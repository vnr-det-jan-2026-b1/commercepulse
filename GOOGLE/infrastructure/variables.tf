variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "commercepulse-project"
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Deployment environment (prod / staging / dev)"
  type        = string
  default     = "prod"
}
