variable "project_id" {}

locals {
  service_accounts = {
    "sa-dataflow"       = "Dataflow pipeline worker"
    "sa-composer"       = "Cloud Composer orchestration"
    "sa-cloudrun-api"   = "Cloud Run API backend"
    "sa-vertex-pipelines" = "Vertex AI ML pipelines"
    "sa-functions"      = "Cloud Functions (alerts)"
  }
}

resource "google_service_account" "accounts" {
  for_each     = local.service_accounts
  account_id   = each.key
  display_name = each.value
  project      = var.project_id
}

# Dataflow worker permissions
resource "google_project_iam_member" "dataflow_worker" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.accounts["sa-dataflow"].email}"
}
resource "google_project_iam_member" "dataflow_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.accounts["sa-dataflow"].email}"
}
resource "google_project_iam_member" "dataflow_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.accounts["sa-dataflow"].email}"
}
resource "google_project_iam_member" "dataflow_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.accounts["sa-dataflow"].email}"
}
resource "google_project_iam_member" "dataflow_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.accounts["sa-dataflow"].email}"
}

# Cloud Run API permissions
resource "google_project_iam_member" "cloudrun_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.accounts["sa-cloudrun-api"].email}"
}
resource "google_project_iam_member" "cloudrun_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.accounts["sa-cloudrun-api"].email}"
}
resource "google_project_iam_member" "cloudrun_tasks" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.accounts["sa-cloudrun-api"].email}"
}
resource "google_project_iam_member" "cloudrun_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.accounts["sa-cloudrun-api"].email}"
}
resource "google_project_iam_member" "cloudrun_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.accounts["sa-cloudrun-api"].email}"
}

# Cloud Composer permissions
resource "google_project_iam_member" "composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.accounts["sa-composer"].email}"
}
resource "google_project_iam_member" "composer_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.accounts["sa-composer"].email}"
}
resource "google_project_iam_member" "composer_dataflow_admin" {
  project = var.project_id
  role    = "roles/dataflow.admin"
  member  = "serviceAccount:${google_service_account.accounts["sa-composer"].email}"
}
resource "google_project_iam_member" "composer_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.accounts["sa-composer"].email}"
}

# Cloud Functions (alerts) permissions
resource "google_project_iam_member" "functions_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.accounts["sa-functions"].email}"
}
resource "google_project_iam_member" "functions_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.accounts["sa-functions"].email}"
}
resource "google_project_iam_member" "functions_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.accounts["sa-functions"].email}"
}

# Vertex AI pipeline permissions
resource "google_project_iam_member" "vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.admin"
  member  = "serviceAccount:${google_service_account.accounts["sa-vertex-pipelines"].email}"
}
resource "google_project_iam_member" "vertex_bq" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.accounts["sa-vertex-pipelines"].email}"
}
resource "google_project_iam_member" "vertex_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.accounts["sa-vertex-pipelines"].email}"
}
resource "google_project_iam_member" "vertex_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.accounts["sa-vertex-pipelines"].email}"
}
