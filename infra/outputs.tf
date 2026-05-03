# ============================================================
# Kenya Health Facility Mapping Pipeline
# OpenTofu — outputs.tf
# Printed to terminal after tofu apply completes.
# ============================================================

output "raw_bucket_name" {
  description = "MinIO raw data lake bucket"
  value       = minio_s3_bucket.raw.bucket
}

output "iceberg_bucket_name" {
  description = "MinIO Iceberg warehouse bucket"
  value       = minio_s3_bucket.iceberg.bucket
}

output "minio_endpoint" {
  description = "MinIO endpoint your services connect to"
  value       = var.minio_endpoint
}

output "next_steps" {
  description = "What to do after tofu apply"
  value       = <<-EOT
    Buckets provisioned. Next:
      1. make superset-init
      2. make pipeline-run
  EOT
}