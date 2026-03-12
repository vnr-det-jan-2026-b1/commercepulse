variable "project_id" {}
variable "region"     {}

locals {
  buckets = {
    "commercepulse-raw-uploads-prod" = {
      location         = var.region
      retention_days   = 90
      uniform_bucket_level_access = true
    }
    "commercepulse-dataflow-staging-prod" = {
      location         = var.region
      retention_days   = 30
      uniform_bucket_level_access = true
    }
    "commercepulse-artifacts-prod" = {
      location         = var.region
      retention_days   = 365
      uniform_bucket_level_access = true
    }
    "commercepulse-terraform-state-prod" = {
      location         = var.region
      retention_days   = null
      uniform_bucket_level_access = true
    }
  }
}

resource "google_storage_bucket" "buckets" {
  for_each = local.buckets

  name                        = each.key
  location                    = each.value.location
  project                     = var.project_id
  uniform_bucket_level_access = each.value.uniform_bucket_level_access
  force_destroy               = false

  dynamic "lifecycle_rule" {
    for_each = each.value.retention_days != null ? [1] : []
    content {
      action { type = "Delete" }
      condition {
        age = each.value.retention_days
      }
    }
  }

  labels = { managed_by = "terraform" }
}

# GCS notification → Pub/Sub for batch upload triggers
resource "google_storage_notification" "batch_trigger" {
  bucket         = google_storage_bucket.buckets["commercepulse-raw-uploads-prod"].name
  payload_format = "JSON_API_V1"
  topic          = "projects/${var.project_id}/topics/commercepulse-batch-triggers"
  event_types    = ["OBJECT_FINALIZE"]

  depends_on = [google_storage_bucket.buckets]
}
