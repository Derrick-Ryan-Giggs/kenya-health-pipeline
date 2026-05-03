# ============================================================
# Kenya Health Facility Mapping Pipeline
# OpenTofu — variables.tf
# All values injected via terraform.tfvars (from .env)
# ============================================================

# ── MinIO ────────────────────────────────────────────────────

variable "minio_endpoint" {
  description = "MinIO S3-compatible endpoint (host:port, no scheme)"
  type        = string
}

variable "minio_access_key" {
  description = "MinIO root user"
  type        = string
  sensitive   = true
}

variable "minio_secret_key" {
  description = "MinIO root password"
  type        = string
  sensitive   = true
}

variable "minio_raw_bucket" {
  description = "Bucket for raw ingested data (JSON/CSV from APIs)"
  type        = string
}

variable "minio_iceberg_bucket" {
  description = "Bucket for Iceberg warehouse (Parquet + metadata)"
  type        = string
}

variable "minio_ssl" {
  description = "Whether MinIO endpoint uses TLS"
  type        = bool
  default     = false
}

# ── Trino ────────────────────────────────────────────────────

variable "trino_host" {
  description = "Trino coordinator host"
  type        = string
}

variable "trino_port" {
  description = "Trino coordinator HTTP port"
  type        = number
  default     = 8080
}

variable "trino_catalog" {
  description = "Iceberg catalog name in Trino"
  type        = string
  default     = "iceberg"
}

variable "trino_schema" {
  description = "Default schema inside the Iceberg catalog"
  type        = string
  default     = "kenya_health"
}