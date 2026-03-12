variable "project_id" {}

data "google_storage_project_service_account" "gcs_sa" {
  project = var.project_id
}

# ── Streaming events topic ─────────────────────────────────────

resource "google_pubsub_topic" "events" {
  name = "commercepulse-events"

  message_retention_duration = "86400s"  # 24 hours

  labels = { managed_by = "terraform" }
}

resource "google_pubsub_subscription" "events_dataflow" {
  name  = "commercepulse-events-sub"
  topic = google_pubsub_topic.events.name

  ack_deadline_seconds       = 60
  message_retention_duration = "3600s"   # 1 hour

  expiration_policy {
    ttl = ""  # never expires
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_topic" "events_dead_letter" {
  name = "commercepulse-events-dead-letter"
  labels = { managed_by = "terraform" }
}

resource "google_pubsub_subscription" "events_dead_letter" {
  name  = "commercepulse-events-dead-letter-sub"
  topic = google_pubsub_topic.events_dead_letter.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"  # 7 days

  expiration_policy {
    ttl = ""
  }
}

# ── Batch upload trigger topic ─────────────────────────────────

resource "google_pubsub_topic" "batch_triggers" {
  name = "commercepulse-batch-triggers"
  labels = { managed_by = "terraform" }
}

resource "google_pubsub_topic_iam_member" "gcs_publisher" {
  topic  = google_pubsub_topic.batch_triggers.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs_sa.email_address}"
}

resource "google_pubsub_subscription" "batch_triggers_composer" {
  name  = "commercepulse-batch-triggers-sub"
  topic = google_pubsub_topic.batch_triggers.name

  ack_deadline_seconds       = 300
  message_retention_duration = "3600s"

  expiration_policy {
    ttl = ""
  }
}
