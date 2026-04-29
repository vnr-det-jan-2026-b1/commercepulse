"""
CommercePulse++ Streaming Event Pipeline
Pub/Sub → Dataflow (Apache Beam) → BigQuery raw.user_events

Always-on streaming pipeline that:
1. Reads events from Pub/Sub topic
2. Validates and normalises event payloads
3. Stitches events into sessions (30-minute inactivity window)
4. Writes valid events to BigQuery via streaming inserts
5. Routes bad records to dead-letter topic

Usage:
    python event_pipeline.py \
        --project=commercepulse-project \
        --region=asia-south1 \
        --runner=DataflowRunner \
        --streaming \
        --temp_location=gs://commercepulse-dataflow-staging-prod/temp
"""
import json
import hashlib
import logging
import argparse
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
from apache_beam.transforms.window import Sessions
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from apache_beam.io import ReadFromPubSub, WriteToPubSub

logger = logging.getLogger(__name__)

PUBSUB_SUBSCRIPTION = "projects/{project}/subscriptions/commercepulse-events-sub"
DEAD_LETTER_TOPIC   = "projects/{project}/topics/commercepulse-events-dead-letter"
BQ_TABLE            = "{project}:cp_raw.user_events"

VALID_EVENT_TYPES = {
    "page_view", "product_view", "add_to_cart",
    "checkout_start", "checkout_complete", "purchase",
}

BQ_SCHEMA = {
    "fields": [
        {"name": "event_id",        "type": "STRING",    "mode": "REQUIRED"},
        {"name": "seller_id",       "type": "STRING",    "mode": "REQUIRED"},
        {"name": "session_id",      "type": "STRING",    "mode": "NULLABLE"},
        {"name": "user_id_hash",    "type": "STRING",    "mode": "NULLABLE"},
        {"name": "event_type",      "type": "STRING",    "mode": "REQUIRED"},
        {"name": "product_sku",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "marketplace",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "event_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "event_date",      "type": "DATE",      "mode": "REQUIRED"},
        {"name": "page_url",        "type": "STRING",    "mode": "NULLABLE"},
        {"name": "referrer",        "type": "STRING",    "mode": "NULLABLE"},
        {"name": "utm_source",      "type": "STRING",    "mode": "NULLABLE"},
        {"name": "utm_medium",      "type": "STRING",    "mode": "NULLABLE"},
        {"name": "utm_campaign",    "type": "STRING",    "mode": "NULLABLE"},
        {"name": "device_type",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "country_code",    "type": "STRING",    "mode": "NULLABLE"},
        {"name": "ingest_timestamp","type": "TIMESTAMP", "mode": "NULLABLE"},
    ]
}


class ValidateEventDoFn(beam.DoFn):
    """Validate required fields and normalise event payload."""
    DEAD_LETTER = "dead_letter"

    def process(self, message: bytes):
        try:
            event = json.loads(message.decode("utf-8"))
        except Exception as e:
            yield beam.pvalue.TaggedOutput(self.DEAD_LETTER,
                json.dumps({"error": f"JSON parse error: {e}", "raw": message[:500].decode("utf-8", errors="replace")}).encode())
            return

        seller_id  = event.get("seller_id", "").strip()
        event_type = event.get("event_type", "").strip().lower()

        if not seller_id:
            yield beam.pvalue.TaggedOutput(self.DEAD_LETTER,
                json.dumps({"error": "Missing seller_id", "event": event}).encode())
            return

        if event_type not in VALID_EVENT_TYPES:
            yield beam.pvalue.TaggedOutput(self.DEAD_LETTER,
                json.dumps({"error": f"Invalid event_type: {event_type}", "event": event}).encode())
            return

        # Normalise user_id to hash for privacy
        raw_uid = str(event.get("user_id", event.get("anonymous_id", "")))
        uid_hash = hashlib.sha256(f"{seller_id}:{raw_uid}".encode()).hexdigest()[:16] if raw_uid else None

        # Parse timestamp
        ts_raw = event.get("timestamp", event.get("event_timestamp"))
        try:
            if isinstance(ts_raw, (int, float)):
                ts = datetime.utcfromtimestamp(ts_raw / 1000 if ts_raw > 1e10 else ts_raw)
            else:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except Exception:
            ts = datetime.utcnow()

        # Normalise device type
        device_raw = str(event.get("device_type", "")).lower()
        if "mobile" in device_raw or "android" in device_raw or "ios" in device_raw:
            device_type = "mobile"
        elif "tablet" in device_raw or "ipad" in device_raw:
            device_type = "tablet"
        else:
            device_type = "desktop"

        normalised = {
            "event_id":        event.get("event_id") or f"{seller_id}-{uid_hash}-{int(ts.timestamp())}",
            "seller_id":       seller_id,
            "user_id_hash":    uid_hash,
            "event_type":      event_type,
            "product_sku":     str(event.get("product_sku", event.get("sku", ""))).strip() or None,
            "marketplace":     str(event.get("marketplace", "")).strip() or None,
            "event_timestamp": ts.isoformat(),
            "event_date":      ts.date().isoformat(),
            "page_url":        str(event.get("page_url", ""))[:512] or None,
            "referrer":        str(event.get("referrer", ""))[:512] or None,
            "utm_source":      str(event.get("utm_source", ""))[:128] or None,
            "utm_medium":      str(event.get("utm_medium", ""))[:128] or None,
            "utm_campaign":    str(event.get("utm_campaign", ""))[:256] or None,
            "device_type":     device_type,
            "country_code":    str(event.get("country_code", ""))[:2].upper() or None,
            "ingest_timestamp": datetime.utcnow().isoformat(),
        }

        yield normalised


class AssignSessionDoFn(beam.DoFn):
    """
    Assigns a session_id to each event based on (seller_id, user_id_hash).
    Session ID = hash of seller + user + window start timestamp.
    """
    def process(self, element, window=beam.DoFn.WindowParam):
        window_start = window.start.to_utc_datetime().isoformat()
        session_key  = f"{element['seller_id']}:{element.get('user_id_hash', 'anon')}:{window_start}"
        element["session_id"] = hashlib.sha256(session_key.encode()).hexdigest()[:16]
        yield element


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(GoogleCloudOptions).project = known_args.project

    subscription  = PUBSUB_SUBSCRIPTION.format(project=known_args.project)
    dead_topic    = DEAD_LETTER_TOPIC.format(project=known_args.project)
    bq_table      = BQ_TABLE.format(project=known_args.project)

    with beam.Pipeline(options=options) as p:
        raw_messages = (
            p
            | "ReadFromPubSub" >> ReadFromPubSub(subscription=subscription)
        )

        parsed = (
            raw_messages
            | "ValidateEvents" >> beam.ParDo(ValidateEventDoFn())
                .with_outputs(ValidateEventDoFn.DEAD_LETTER, main="valid")
        )

        # Session windowing: 30-minute inactivity gap
        sessionised = (
            parsed.valid
            | "KeyBySeller_User" >> beam.Map(
                lambda e: (f"{e['seller_id']}:{e.get('user_id_hash', 'anon')}", e)
            )
            | "SessionWindows" >> beam.WindowInto(
                Sessions(gap_size=1800),  # 30 minutes
                trigger=AfterWatermark(late=AfterProcessingTime(60)),
                accumulation_mode=AccumulationMode.DISCARDING,
                allowed_lateness=300,
            )
            | "AssignSessionId" >> beam.ParDo(AssignSessionDoFn())
                .with_input_types(tuple)
            | "ExtractValue" >> beam.Map(lambda kv: kv[1])
        )

        # Write valid events to BigQuery (streaming insert)
        (
            sessionised
            | "WriteToBigQuery" >> WriteToBigQuery(
                table=bq_table,
                schema=BQ_SCHEMA,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
                method=WriteToBigQuery.Method.STREAMING_INSERTS,
            )
        )

        # Route dead-letter messages back to Pub/Sub dead-letter topic
        (
            parsed[ValidateEventDoFn.DEAD_LETTER]
            | "WriteDeadLetter" >> WriteToPubSub(topic=dead_topic)
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
