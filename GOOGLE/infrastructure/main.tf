terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket  = "commercepulse-terraform-state-sahith"
    prefix  = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required APIs ────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "dataflow.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "composer.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "cloudtasks.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "firebase.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com"
  ])

  service            = each.key
  disable_on_destroy = false
}

# ── Modules ─────────────────────────────────────────────────────

# module "networking" {
#   source = "./modules/networking"
# }

module "iam" {
  source     = "./modules/iam"
  project_id = var.project_id
}

module "pubsub" {
  source     = "./modules/pubsub"
  project_id = var.project_id
}

module "storage" {
  source     = "./modules/storage"
  project_id = var.project_id
  region     = var.region
  depends_on = [module.pubsub]
}

module "bigquery" {
  source     = "./modules/bigquery"
  project_id = var.project_id
  region     = var.region
}

# module "cloud_run" {
#   source = "./modules/cloud_run"
# }