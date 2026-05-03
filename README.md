# Kenya Health Facility Mapping Pipeline

A fully open-source lakehouse that maps health facility distribution
across Kenya's 47 counties, exposing inequality at the sub-county level.

## Stack
| Layer        | Tool                          |
|--------------|-------------------------------|
| IaC          | OpenTofu                      |
| Orchestration| Apache Airflow 2.9.2          |
| Storage      | MinIO (S3-compatible)         |
| Table format | Apache Iceberg (REST catalog) |
| Query engine | Trino 480                     |
| Transform    | dbt Core (dbt-trino)          |
| BI           | Apache Superset 5.0.0         |

## Quick start

```bash
cp .env.example .env        # fill in your values
make pull                   # download Docker images (~2.3 GB)
make build                  # build custom Airflow + Superset images
make up                     # start all services
make tofu-apply             # provision MinIO buckets + Trino catalog
make superset-init          # bootstrap Superset admin user
make pipeline-run           # trigger the first ingestion
```

## Data sources
- MOH KMHFL  — Kenya Master Health Facility List API
- KNBS       — Population estimates CSV
- HDX        — Kenya county + sub-county GeoJSON

## Dashboards
- County facility density scorecard (all 47 counties)
- Nairobi sub-county drill-down (Kibera, Mathare, Westlands...)
- Kenya choropleth map (facility density by county)
- Service gap report (maternity, ART, TB, emergency per county)
