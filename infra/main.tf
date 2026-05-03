# ============================================================
# Kenya Health Facility Mapping Pipeline
# OpenTofu — main.tf
#
# Provisions:
#   - MinIO raw bucket       (raw ingested JSON/CSV from APIs)
#   - MinIO Iceberg bucket   (Parquet files + Iceberg metadata)
#
# Run AFTER docker compose up (MinIO must be running).
# Run BEFORE triggering any Airflow DAG.
#
# Usage:
#   cd infra
#   tofu init
#   tofu plan
#   tofu apply
# ============================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    minio = {
      source  = "aminueza/minio"
      version = "~> 2.0"
    }
  }
}

# ── Provider ─────────────────────────────────────────────────

provider "minio" {
  minio_server   = var.minio_endpoint
  minio_user     = var.minio_access_key
  minio_password = var.minio_secret_key
  minio_ssl      = var.minio_ssl
}

# ── Raw bucket ───────────────────────────────────────────────
# Stores raw API responses partitioned by dataset and date.
# Layout: raw-facilities/<dataset>/year=YYYY/month=MM/day=DD/

resource "minio_s3_bucket" "raw" {
  bucket        = var.minio_raw_bucket
  acl           = "private"
  force_destroy = false
}

resource "minio_s3_bucket_versioning" "raw" {
  bucket = minio_s3_bucket.raw.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

# ── Iceberg warehouse bucket ─────────────────────────────────
# Stores Parquet data files and Iceberg table metadata.
# Trino reads and writes here via the Iceberg REST catalog.

resource "minio_s3_bucket" "iceberg" {
  bucket        = var.minio_iceberg_bucket
  acl           = "private"
  force_destroy = false
}

resource "minio_s3_bucket_versioning" "iceberg" {
  bucket = minio_s3_bucket.iceberg.bucket

  versioning_configuration {
    status = "Enabled"
  }
}