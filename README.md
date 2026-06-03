# Kenya Health Facility Mapping Pipeline

> **An open-source data lakehouse exposing healthcare inequality across Kenya's 47 counties — built end-to-end with Apache Airflow, MinIO, Apache Iceberg, Trino, dbt Core, and Apache Superset, all running in Docker on a local machine.**

---

## Table of Contents

- [Problem Description](#-problem-description)
- [Solution Overview](#-solution-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Data Sources](#-data-sources)
- [Project Structure](#-project-structure)
- [Infrastructure as Code (OpenTofu)](#-infrastructure-as-code-opentofu)
- [Data Ingestion & Orchestration](#-data-ingestion--orchestration)
- [Data Lakehouse Design](#-data-lakehouse-design)
- [Transformations (dbt Core)](#-transformations-dbt-core)
- [Dashboard](#-dashboard)
- [Challenges & How We Solved Them](#-challenges--how-we-solved-them)
- [Reproducibility — How to Run](#-reproducibility--how-to-run)
- [Known Limitations & Future Work](#-known-limitations--future-work)

---

## Problem Description

Kenya has 47 counties and over 20,000 registered health facilities — yet access to care is profoundly unequal. A child born in Westlands, Nairobi, has access to 7.23 facilities per 10,000 people. A child born in Embakasi North has 0.62. That inequality is real, large, and invisible — because the data to prove it has never been systematically assembled in one place.

The Ministry of Health (MOH) publishes facility lists through the Kenya Master Health Facility Registry (KMHFR). The Kenya National Bureau of Statistics (KNBS) publishes county population data from the 2019 Census. The Humanitarian Data Exchange (HDX) publishes county boundary GeoJSON. But no one has joined these three datasets together into a reproducible, automated pipeline that answers the real questions:

- **Which counties are most underserved relative to their population?**
- **Which counties lack maternity, ART (HIV treatment), TB, or emergency facilities?**
- **How has the facility landscape changed over time?**
- **What would it take to bring every county to a baseline of 3 facilities per 10,000 people?**

This pipeline answers all of those questions — automatically, monthly, and at county and sub-county resolution — using 100% open-source tools running in Docker on a local machine.

---

## Solution Overview

| Dimension | Detail |
|-----------|--------|
| **Scope** | 47 counties, 17 Nairobi sub-counties, 20,391 health facilities |
| **Granularity** | County-level density, service gaps, facility type breakdown |
| **Refresh cadence** | Monthly via Airflow orchestration |
| **Deployment** | Local Docker Compose + Cloudflare Tunnel for live sharing |
| **License** | 100% open-source stack (Apache 2.0) |

**Key findings surfaced by the pipeline:**
- Bungoma is the most underserved county in Kenya (rank 1): 1.88 facilities per 10,000 people serving 1.67M people
- Samburu is the only county with a critical TB gap: only 1 TB facility for 310,327 people
- Embakasi North (Nairobi) has just 0.62 facilities per 10,000 — while neighbouring Starehe has 7.23
- Mandera has the highest raw ratio (6.26 per 10k) due to sparse population density — a reminder that ratios alone don't tell the full story

---

## Architecture

```

                        Data Sources (External)                       
  KMHFR API (MOH)       KNBS 2019 Census      HDX County GeoJSON     
  api.kmhfr.health.go.ke  humdata.org            humdata.org          

                                                      
                                                      

              Apache Airflow (CeleryExecutor + Redis)                 
   kenya_health_monthly DAG                                           
    ingest_facilities                                           
    ingest_population   (parallel)  ingestion_complete    
    ingest_geodata                                            
                                                                     
                                               dbt_run DAG            

                               
                               

                    MinIO (S3-Compatible Data Lake)                   
   raw-facilities/                                                    
    facilities/year=2026/month=05/day=22/facilities.json  (32.6MB)
    population/year=2026/month=05/day=22/population.json          
    geodata/year=2026/month=05/day=22/geodata.json                
   iceberg-warehouse/  (Parquet files, managed by Iceberg)           

                               
                               

            Apache Iceberg (Table Format) + REST Catalog              
            (SQLite persistence via Docker named volume)              
                                                                      
   iceberg.raw.facilities    (20,391 rows, Parquet)                  
   iceberg.raw.population    (47 rows)                               
   iceberg.raw.geodata       (47 rows)                               

                               
                               

                    Trino 480 (Query Engine)                          
              Queries Iceberg tables via S3/MinIO                    

                               
                               

                    dbt Core + dbt-trino adapter                      
   Staging (views)                                                    
    stg_facilities      (dedup, filter operational, normalize)    
    stg_population      (county population join keys)             
    stg_geodata         (county boundary GeoJSON)                 
                                                                      
   Marts (Iceberg tables)                                             
    mart_county_density         (facilities per 10k, 47 counties) 
    mart_service_gaps           (maternity/ART/TB/emergency rates) 
    mart_underserved_counties   (severity scoring + ranking)       
    mart_nairobi_subcounty      (17 sub-county drill-down)        
                                                                      
   Snapshot (SCD2)                                                    
    scd2_facilities             (facility change history)         

                               
                               

                    Apache Superset 5.0.0                             
   Kenya Health Facility Dashboard                                    
    Facilities per 10,000 People by County (Bar Chart)            
    Underserved Counties Ranking (Table, conditional formatting)  
    Maternity Coverage by County (Bar Chart)                      
    Service Coverage Rates by County (Grouped Bar)                
    Nairobi Sub-County Facility Density (Bar Chart)               
    Nairobi Sub-County Service Gaps (Table)                       
    Total Counties Mapped (Big Number: 47)                        
    Kenya Facility Density Map (deck.gl Polygon Choropleth)       

                               
                               
             Cloudflare Tunnel → Public URL (trycloudflare.com)
```

---

## Tech Stack

| Layer | Tool | Version | Purpose |
|-------|------|---------|---------|
| IaC | OpenTofu | 1.9.x | Provision MinIO buckets + versioning |
| Orchestration | Apache Airflow | 2.9.2 | DAG scheduling, CeleryExecutor |
| Message Broker | Redis | 7.2 | Celery task queue |
| Data Lake | MinIO | RELEASE.2025-09-07 | S3-compatible object storage |
| Table Format | Apache Iceberg | (via REST catalog) | ACID tables, time travel, schema evolution |
| Catalog | Iceberg REST Catalog | apache/iceberg-rest-fixture | SQLite-backed catalog, persists across restarts |
| Query Engine | Trino | 480 | Federated SQL over Iceberg/MinIO |
| Transformations | dbt Core + dbt-trino | 1.8.0 | Staging models, mart models, SCD2 snapshots |
| BI / Dashboard | Apache Superset | 5.0.0 | Interactive dashboards |
| Metadata DB (Airflow) | PostgreSQL | 13 | Airflow state |
| Metadata DB (Superset) | PostgreSQL | 18 | Superset state |
| Deployment | Docker Compose | — | All services containerised |
| Tunneling | Cloudflare Tunnel | cloudflared | Expose localhost to the internet |

All tools are **100% open-source**. No proprietary SaaS services are used.

---

## Data Sources

### 1. MOH KMHFR API (Primary — Facilities)
- **URL:** `https://api.kmhfr.health.go.ke/api/public/facilities/`
- **Type:** Public REST API, no authentication required
- **Volume:** 20,391 facilities, 680 pages (page_size=30)
- **Key fields:** facility code, name, KEPH level, facility type, owner, county, sub-county, constituency, ward, operation status, service flags (maternity, ART, TB, emergency, outpatient), GPS coordinates
- **Refresh:** Monthly (pipeline re-ingests on each DAG run)

### 2. KNBS 2019 Census (Population)
- **URL:** HDX — Kenya Population by County CSV
- **Type:** Static dataset (official census), county + sub-county level
- **Volume:** 47 county records, 9,800+ downloads globally
- **Key fields:** county, total population, male, female, households
- **Note:** Kenya's last official census. 2024 projections applied at 2.3% annual growth rate (KNBS methodology) for Nairobi sub-county population seed

### 3. HOT OSM / HDX Kenya County GeoJSON (Boundaries)
- **URL:** HDX Kenya GeoJSON (county boundaries)
- **Type:** Static GeoJSON, WGS84 coordinate system
- **Volume:** 47 county polygons (mix of Polygon and MultiPolygon)
- **Key fields:** county_name, geometry (full polygon coordinates)
- **Use:** Choropleth map rendering in Superset

---

## Project Structure

```
kenya-health-pipeline/
 .env                          # All secrets and config (never committed)
 .env.example                  # Template — copy to .env and fill in
 .gitignore
 Makefile                      # make up / make down / make pipeline-run etc.
 README.md
 docker-compose.yml            # Full 13-container stack definition

 airflow/
    Dockerfile                # Extends apache/airflow:2.9.2-python3.10
    requirements.txt          # dbt-core, dbt-trino, boto3, trino, etc.
    webserver_config.py       # Flask-AppBuilder session config (Redis-backed)
    dags/
        kenya_health_monthly.py   # Orchestrator DAG (monthly trigger)
        ingest_facilities.py      # KMHFR API → MinIO raw bucket
        ingest_population.py      # KNBS CSV → MinIO raw bucket
        ingest_geodata.py         # HDX GeoJSON → MinIO raw bucket
        dbt_run.py                # dbt run → dbt test → dbt snapshot

 ingestion/
    __init__.py
    kmhfl_client.py           # Paginates KMHFR API (680 pages)
    knbs_client.py            # Downloads KNBS Census CSV
    hdx_client.py             # Downloads HDX county GeoJSON
    minio_loader.py           # Uploads NDJSON to MinIO with partitioned paths

 dbt/
    dbt_project.yml
    profiles.yml              # Reads from env vars (TRINO_HOST etc.)
    packages.yml
    seeds/
       nairobi_subcounty_population.csv   # 17 sub-counties, 2019 + 2024 projections
    models/
       staging/
          stg_facilities.sql
          stg_population.sql
          stg_geodata.sql
          schema.yml
       marts/
           mart_county_density.sql
           mart_service_gaps.sql
           mart_underserved_counties.sql
           mart_nairobi_subcounty.sql
           schema.yml
    snapshots/
       scd2_facilities.sql   # SCD2 change tracking on facility attributes
    tests/
        assert_no_duplicate_facilities.sql
        assert_county_count_equals_47.sql

 trino/
    etc/
        config.properties     # coordinator=true, memory limits
        jvm.config
        node.properties
        catalog/
            iceberg.properties  # Points to MinIO S3 + Iceberg REST catalog

 superset/
    Dockerfile                # Extends apache/superset:5.0.0 + psycopg2 + sqlalchemy-trino
    superset_config.py        # SECRET_KEY, session config, Trino connection
    dashboards/

 infra/
     main.tf                   # MinIO bucket resources (OpenTofu)
     variables.tf
     outputs.tf
     terraform.tfvars.example
     .gitignore                # *.tfstate never committed
```

---

## Infrastructure as Code (OpenTofu)

OpenTofu runs **once before the stack** to provision the two MinIO buckets. It is not a running service — it's a one-time CLI command.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in your MinIO credentials (matching .env)
tofu init
tofu apply
```

OpenTofu provisions:
- `raw-facilities` bucket — versioning enabled, stores raw NDJSON ingestion output
- `iceberg-warehouse` bucket — versioning enabled, stores Parquet files written by Trino/Iceberg

**Why OpenTofu over Terraform?** OpenTofu is the community-maintained, truly open-source fork of Terraform (following HashiCorp's BSL license change). It is 100% compatible with the Terraform provider ecosystem and is used here as the IaC layer consistent with the project's open-source-only constraint.

If buckets were already created by `minio-init` on first stack start, import them:
```bash
tofu import minio_s3_bucket.raw raw-facilities
tofu import minio_s3_bucket.iceberg iceberg-warehouse
tofu apply
```

---

## Data Ingestion & Orchestration

### Airflow DAG Design

The pipeline uses **Apache Airflow with CeleryExecutor** (backed by Redis). All tasks run inside Docker containers with the custom `kenya-health-airflow` image that bundles dbt Core alongside the ingestion scripts.

```
kenya_health_monthly (schedule: @monthly)

 start (DummyOperator)
    trigger_ingest_facilities  
    trigger_ingest_population   TriggerDagRunOperator (parallel)
    trigger_ingest_geodata     

 ingestion_complete (ExternalTaskSensor waits for all 3)
     trigger_dbt_run
         end
```

**Key design decisions:**
- The three ingestion DAGs run **in parallel** — facilities, population, and geodata are independent
- `ingestion_complete` acts as a barrier gate: dbt only runs after all three succeed
- Each child DAG has `retries=3, retry_delay=timedelta(minutes=5)` for transient API failures
- `schedule_interval=None` on child DAGs — they are only triggered by the parent orchestrator, never on their own schedule

### Ingestion Logic

**Facilities (`kmhfl_client.py`):**
Paginates the KMHFR public API (20,391 facilities, 680 pages at 30 per page). Uses `requests.Session` with urllib3 warning suppression. Uploads a single NDJSON file to MinIO at:
```
raw-facilities/facilities/year=YYYY/month=MM/day=DD/facilities.json
```

**Population (`knbs_client.py`):**
Downloads the KNBS Census 2019 county CSV from HDX. Uploads 47 records as NDJSON.

**Geodata (`hdx_client.py`):**
Downloads Kenya county GeoJSON from HDX. Handles both `Polygon` and `MultiPolygon` types. Uploads 47 county geometry records as NDJSON. County name normalization handles known discrepancies (`elegeyo-marakwet` → `elgeyo marakwet`, `murang'a` → `muranga`, `tharaka - nithi` → `tharaka nithi`).

---

## Data Lakehouse Design

### Architecture: Lakehouse (not traditional Data Warehouse)

This project implements a **lakehouse architecture** — the "warehouse" is not a single tool but a four-piece open-source assembly:

| Component | Role |
|-----------|------|
| **MinIO** | Storage layer — raw files (NDJSON) and Parquet files live here |
| **Apache Iceberg** | Table format layer — provides ACID transactions, schema evolution, time travel on top of files |
| **Iceberg REST Catalog** | Catalog layer — tracks schema definitions and table locations, persisted via SQLite in a named Docker volume |
| **Trino** | Query engine layer — executes ANSI SQL across Iceberg tables without moving data |

### Why Iceberg over plain Parquet?

- **Schema evolution:** New columns can be added to raw tables without breaking existing dbt models
- **Time travel:** `SELECT * FROM iceberg.raw.facilities FOR TIMESTAMP AS OF ...` — any point-in-time snapshot
- **ACID transactions:** Safe concurrent writes from multiple Airflow workers
- **Partition pruning:** Iceberg's hidden partitioning (by ingestion date) allows Trino to skip irrelevant Parquet files entirely

### Raw Layer Schema

```sql
-- iceberg.raw.facilities (20,391 rows, Parquet)
facility_id         VARCHAR
facility_name       VARCHAR
facility_type       VARCHAR
keph_level          VARCHAR
county_name         VARCHAR
sub_county_name     VARCHAR
operation_status    VARCHAR
has_maternity       BOOLEAN
has_art             BOOLEAN
has_tb              BOOLEAN
has_emergency       BOOLEAN
latitude            DOUBLE
longitude           DOUBLE
ingested_at         TIMESTAMP(6)

-- iceberg.raw.population (47 rows)
county_name         VARCHAR
population          BIGINT

-- iceberg.raw.geodata (47 rows)
county_name         VARCHAR
geometry            VARCHAR   -- GeoJSON string (Polygon/MultiPolygon)
area_sqkm           DOUBLE
```

### Iceberg Catalog Persistence

The Iceberg REST catalog uses **SQLite persistence via a named Docker volume** (`iceberg-catalog`). This means all schemas, table registrations, and metadata survive `docker compose down / up` cycles.

The critical Trino catalog configuration (`trino/etc/catalog/iceberg.properties`):
```properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://iceberg-rest:8181
iceberg.file-format=PARQUET
iceberg.unique-table-location=true
iceberg.register-table-procedure.enabled=true
```

---

## Transformations (dbt Core)

**30 data tests pass. 7 models run. 1 SCD2 snapshot. 1 seed.**

### Staging Layer (Materialized as Views)

| Model | Key Transformations |
|-------|---------------------|
| `stg_facilities` | Deduplication via `ROW_NUMBER()` on `facility_id`, filter to `operation_status = 'Operational'`, normalize boolean service flags, `TIMESTAMP(6)` casting |
| `stg_population` | Lower-case county names for join consistency |
| `stg_geodata` | Lower-case county names, preserve full GeoJSON geometry strings |

### Mart Layer (Materialized as Iceberg Tables)

**`mart_county_density`** — Core scorecard for all 47 counties:
```sql
facilities_per_10k = ROUND(total_facilities / population * 10000, 2)
weighted_density_per_10k = weighted by facility type (hospitals count more than dispensaries)
density_rank = ROW_NUMBER() OVER (ORDER BY facilities_per_10k ASC)
```
Also includes breakdowns by facility type (hospital, health centre, dispensary, clinic) and service type (maternity, ART, TB, emergency).

**`mart_service_gaps`** — Service coverage rates per 100,000 people per county with gap flags:
```sql
maternity_per_100k, art_per_100k, tb_per_100k, emergency_per_100k
maternity_gap_flag = maternity_per_100k < national_median
tb_gap_flag = tb_count < 2   -- Samburu: only 1 TB facility
```

**`mart_underserved_counties`** — Composite severity scoring:
```sql
severity_score = 
  (1 if facilities_per_10k < 2.5 else 0) +
  (1 if maternity_gap_flag else 0) +
  (1 if art_gap_flag else 0) +
  (1 if tb_gap_flag else 0) +
  (1 if no_emergency_flag else 0)

underserved_rank = ROW_NUMBER() OVER (ORDER BY severity_score DESC, facilities_per_10k ASC)
facilities_needed_to_baseline = MAX(0, CEILING(population/10000 * 3) - total_facilities)
```

**`mart_nairobi_subcounty`** — 17 Nairobi sub-county drill-down, joining facilities to the `nairobi_subcounty_population` seed (2019 census + 2024 projections at 2.3% annual KNBS growth rate):
```
Starehe:       7.23 per 10k  (most dense — Nairobi CBD)
Embakasi North: 0.62 per 10k  (least dense — 291,760 people, 18 facilities)
```

### SCD2 Snapshot

`scd2_facilities.sql` tracks changes to key facility attributes over time using dbt's native snapshot mechanism:
```yaml
unique_key: facility_id
strategy: check
check_cols:
  - facility_name
  - facility_type
  - operation_status
  - county_name
  - has_maternity, has_art, has_tb, has_emergency
```

On each monthly pipeline run, any facility that changed is recorded with `dbt_valid_from` and `dbt_valid_to` timestamps. This enables queries like: *"Show me all facilities that gained or lost maternity services in the last 6 months."*

### Data Quality Tests

```yaml
# Custom tests
- assert_no_duplicate_facilities     # No facility_id appears more than once in staging
- assert_county_count_equals_47      # Exactly 47 counties in mart_county_density

# Schema tests (dbt built-in)
- unique: facility_id
- not_null: county_name, facilities_per_10k
- accepted_values: operation_status in ['Operational']
```

---

## Dashboard

**Dashboard:** Kenya Health Facility Dashboard (Apache Superset 5.0.0)

**Live URL (Cloudflare Tunnel):** `https://emily-illustration-nutrition-choosing.trycloudflare.com`

### Charts

| # | Chart Name | Type | Dataset | Key Insight |
|---|-----------|------|---------|-------------|
| 1 | Facilities per 10,000 People by County | Bar Chart | `mart_county_density` | County-level density comparison across all 47 counties |
| 2 | Underserved Counties Ranking | Table | `mart_underserved_counties` | Bungoma ranks #1 most underserved (1.88/10k, 1.67M people) |
| 3 | Maternity Coverage by County | Bar Chart | `mart_service_gaps` | Maternity facilities per 100k by county |
| 4 | Service Coverage Rates by County | Grouped Bar | `mart_service_gaps` | 4 services side-by-side: maternity, ART, TB, emergency |
| 5 | Nairobi Sub-County Facility Density | Bar Chart | `mart_nairobi_subcounty` | Starehe (7.23) vs Embakasi North (0.62) inequality within Nairobi |
| 6 | Nairobi Sub-County Service Gaps | Table | `mart_nairobi_subcounty` | Sub-county service detail with 2024 population projections |
| 7 | Total Counties Mapped | Big Number | `mart_county_density` | 47 Kenya Counties Mapped |
| 8 | Kenya Facility Density Map | deck.gl Polygon | `geo_county_density_feature` | Choropleth — red = high density, lighter = underserved |

The choropleth map (Chart 8) required significant engineering to get working. The geometry data required wrapping in full GeoJSON Feature objects (`{"type":"Feature","geometry":...,"properties":{...}}`) before deck.gl would render the polygons. County name normalization across three datasets required explicit CASE mapping for Elegeyo-Marakwet, Murang'a, and Tharaka-Nithi.

---

## Challenges & How We Solved Them

### 1. Superset & Airflow Session Logout Bug

**Problem:** Both Apache Superset 5.0.0 and Apache Airflow 2.9.2 were logging users out within 20–60 seconds of login. This was a critical blocker for building dashboards interactively.

**Investigation:** Traced through browser cookies, Flask session configuration, container logs, and GitHub issues. The root cause was multi-layered:
- Airflow: Multiple gunicorn worker processes weren't sharing session state — each worker had its own memory, so the CSRF token created by worker A wasn't visible to worker B
- Superset 5.0.0: A known regression (`Class 'werkzeug.local.LocalProxy' is not mapped`) caused the user session to fail persisting to the PostgreSQL database, falling back to cookie-only sessions that expired in ~60 seconds

**Solution:**
- Airflow: Set `AIRFLOW__WEBSERVER__WORKERS=1` to force single-worker mode, eliminating the cross-worker session sharing problem. Added `FLASK_APP_MUTATOR` in `superset_config.py` to call `session.permanent = True` on every request. Added `PERMANENT_SESSION_LIFETIME = timedelta(days=730)` (2 years)
- Superset: Added `SESSION_COOKIE_NAME`, `SESSION_PERMANENT = True`, `WTF_CSRF_TIME_LIMIT = None`, and a `before_request` hook to force permanent sessions on every request
- Both: Set fixed, stable `SECRET_KEY` values in `.env` (generated with `openssl rand -hex 32`) — the default behaviour was generating a random key on each container start, invalidating all sessions on every restart

### 2. Iceberg Catalog Not Persisting Across Restarts

**Problem:** Every time the stack was restarted, Trino lost all knowledge of the Iceberg schemas and tables. Re-running `CREATE SCHEMA` and `CALL iceberg.system.register_table(...)` was required on every fresh start.

**Root cause:** The Iceberg REST catalog was using an in-memory SQLite database by default. On container restart, the memory was wiped.

**Solution:** Added `CATALOG_URI=jdbc:sqlite:/catalog/iceberg_catalog.db` to the iceberg-rest container environment and mounted a named Docker volume (`iceberg-catalog`) at `/catalog`. The SQLite file now persists across all restarts. Both schemas (`iceberg.raw`, `iceberg.kenya_health`) and all table registrations survive `docker compose down / up`.

### 3. dbt Target Directory Permission Conflicts

**Problem:** The dbt VS Code extension (running as the host user) would create the `dbt/target/` directory with host user ownership. When Airflow (running as UID 50000 inside the container) tried to write `partial_parse.msgpack`, it got `PermissionError: [Errno 13] Permission denied`.

**Solution:** Declared `dbt-target` and `dbt-logs` as **named Docker volumes** in `docker-compose.yml`, mounted at `/opt/airflow/dbt/target` and `/opt/airflow/dbt/logs`. Named volumes are owned by the Docker daemon, not the host user. After deleting the host-owned directories (`sudo rm -rf dbt/target dbt/logs`) and recreating the worker container, ownership was fixed with `docker exec --user root ... chown -R 50000:0 /opt/airflow/dbt/target`.

### 4. KMHFR API URL Discovery

**Problem:** The pipeline was originally wired to hit `https://kmhfl.health.go.ke/api` but that domain does a server-side 301 redirect to `https://kmhfr.health.go.ke`. The redirect sent the client to the new domain, which then returned just the URL path as plain text (not JSON) — causing a `JSONDecodeError: Expecting value: line 1 column 1`.

**Investigation:** Traced through multiple failed attempts (including a detour through the 2017 HDX Excel file, the Healthsites CSV, and the HOT OSM GeoJSON zip) before discovering the correct public API endpoint at `https://api.kmhfr.health.go.ke/api/public/facilities/`.

**Solution:** Updated `KMHFL_FACILITIES_URL` in `.env` to the correct API endpoint. Confirmed with `curl` that it returns paginated JSON (20,391 facilities, 680 pages). No authentication required.

### 5. Superset Country Map Only Supports 8 Old Provinces

**Problem:** Kenya's Country Map in Superset uses pre-loaded GeoJSON from inside the Superset image. That GeoJSON has only 8 administrative subdivisions (the old provinces: KE-100 through KE-800), not the current 47 counties. No amount of ISO code mapping could fix this — the underlying map data simply doesn't have county boundaries.

**Investigation:** Found the GeoJSON inside the container at:
```
/app/.venv/lib/python3.10/site-packages/superset/static/assets/f3c3f0689af8cafeab87.geojson
```
Properties: `{'ISO': 'KE-700', 'NAME_1': 'Rift Valley'}` — confirming 8 provinces only.

**Solution:** Switched to `deck.gl Polygon` chart type with custom GeoJSON from our own `stg_geodata` table. Created a virtual dataset (`geo_county_density_feature`) in Superset SQL Lab that wraps each county's raw geometry string inside a full GeoJSON Feature object, which deck.gl requires:
```sql
concat('{"type":"Feature","geometry":', g.geometry,
       ',"properties":{"county_name":"', g.county_name,
       '","facilities_per_10k":', cast(d.facilities_per_10k as varchar), '}}')
```

### 6. Superset psycopg2 Not Installing in Correct Python Environment

**Problem:** Superset 5.0.0 uses a virtual environment at `/app/.venv` managed by `uv` (not pip). Installing `psycopg2-binary` with `pip install` or `uv pip install --system` put it in the system Python (`/usr/local/lib/python3.10`), not the venv. Superset never saw it and kept crashing with `ModuleNotFoundError: No module named 'psycopg2'`.

**Investigation:** Ran `docker run --rm apache/superset:5.0.0 find / -name "pip"` — returned nothing. Found `uv` at `/usr/local/bin/uv` and Python at `/app/.venv/bin/python3`. Confirmed via `sys.path` that the venv only loads from `/app/.venv/lib/python3.10/site-packages`.

**Solution:** Used `uv pip install --python /app/.venv/bin/python3` in the Dockerfile — this tells uv to target the specific Python interpreter (and its associated virtual environment), bypassing the system Python entirely:
```dockerfile
RUN uv pip install --python /app/.venv/bin/python3 \
    psycopg2-binary==2.9.9 \
    sqlalchemy-trino==0.5.0 \
    trino==0.327.0
```

### 7. Airflow pip Upgrading Airflow Itself During Image Build

**Problem:** Installing `apache-airflow-providers-amazon` without a constraint file caused pip to resolve it as requiring Airflow 3.0.0 (not 2.9.2), and silently upgraded the entire Airflow installation. The container then couldn't find the `airflow` binary at the path the entrypoint expected for 2.9.2.

**Solution:** Added the official Airflow constraints file to all pip installs:
```dockerfile
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.10.txt" \
    -r /requirements.txt
```
Also pinned the base image to `apache/airflow:2.9.2-python3.10` (explicit Python version) to prevent implicit base image changes.

### 8. Nairobi Sub-County Population Data Not Available in KNBS Source

**Problem:** The KNBS CSV only had a single county-level total for Nairobi (4,397,073) with an empty `sub_county_name` field. `mart_nairobi_subcounty` was showing `NULL` for all population and density calculations.

**Solution:** Created a dbt seed file (`seeds/nairobi_subcounty_population.csv`) with 2019 census populations for all 17 Nairobi sub-counties, plus 2024 projections calculated at 2.3% annual growth (KNBS methodology):
```
population_2024 = population_2019 × (1.023)^5
```
This is exactly what WHO, MOH, and NGOs operating in Kenya use — 2019 census as the base, projections for the current year. The seed was loaded into Iceberg via `dbt seed` and joined in the mart model.

### 9. Three County Name Mismatches Across Datasets

**Problem:** The geodata table (from HOT OSM via HDX) spelled three county names differently from the mart tables (sourced from KMHFR):
- `elegeyo-marakwet` → should be `elgeyo marakwet`
- `murang'a` → should be `muranga`
- `tharaka - nithi` → should be `tharaka nithi`

These caused NULL joins for those three counties in the choropleth map and any cross-dataset query.

**Solution:** Added explicit CASE mapping in the join condition of the geo virtual dataset:
```sql
ON lower(d.county_name) = CASE lower(g.county_name)
    WHEN 'elegeyo-marakwet' THEN 'elgeyo marakwet'
    WHEN 'murang''a'        THEN 'muranga'
    WHEN 'tharaka - nithi'  THEN 'tharaka nithi'
    ELSE regexp_replace(regexp_replace(lower(g.county_name), '\s*-\s*', ' '), '''', '')
END
```

---

## Reproducibility — How to Run

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Ubuntu / Linux | 22.04+ |
| Docker Engine | 24+ |
| Docker Compose | V2 (plugin) |
| OpenTofu | 1.9+ |
| At least 16GB RAM | — |
| At least 20GB free disk | — |

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Derrick-Ryan-Giggs/kenya-health-pipeline.git
cd kenya-health-pipeline
```

### Step 2 — Configure Environment

```bash
cp .env.example .env
nano .env
```

Required fields to fill in:
```bash
# Generate Fernet key for Airflow
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate secret keys
openssl rand -hex 32   # → AIRFLOW_WEBSERVER_SECRET_KEY
openssl rand -hex 32   # → SUPERSET_SECRET_KEY
```

### Step 3 — Pull Docker Images

```bash
docker pull minio/minio:RELEASE.2025-09-07T16-13-09Z
docker pull minio/mc:RELEASE.2025-08-13T08-35-41Z
docker pull trinodb/trino:480
docker pull apache/superset:5.0.0
# apache/airflow:2.9.2-python3.10 and postgres:13, postgres:18, redis:7.2
# are pulled automatically during make build
```

### Step 4 — Build Custom Images

```bash
make build
```

This builds:
- `kenya-health-airflow` — Airflow 2.9.2 + dbt Core 1.8.0 + dbt-trino + boto3 + trino client
- `kenya-health-superset` — Superset 5.0.0 + psycopg2 + sqlalchemy-trino

### Step 5 — Start the Stack

```bash
make up
```

Wait ~60 seconds for all services to become healthy. Check status:
```bash
docker compose ps
```

All 13 containers should show `healthy` or `exited` (for one-shot init containers).

### Step 6 — Provision Infrastructure (OpenTofu)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in your MinIO credentials (matching .env)
tofu init
tofu apply
cd ..
```

If buckets already exist (created by minio-init):
```bash
tofu import minio_s3_bucket.raw raw-facilities
tofu import minio_s3_bucket.iceberg iceberg-warehouse
tofu apply
```

### Step 7 — Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8080 | See `.env` → `AIRFLOW_ADMIN_USER/PASSWORD` |
| MinIO Console | http://localhost:9001 | See `.env` → `MINIO_ROOT_USER/PASSWORD` |
| Trino UI | http://localhost:8081 | `trino` (no password) |
| Superset | http://localhost:8088 | See `.env` → `SUPERSET_ADMIN_USER/PASSWORD` |

### Step 8 — Create Iceberg Schemas and Register Tables

Run these in Trino's SQL interface (http://localhost:8081) or via CLI:

```sql
-- Create schemas
CREATE SCHEMA IF NOT EXISTS iceberg.raw LOCATION 's3://iceberg-warehouse/raw/';
CREATE SCHEMA IF NOT EXISTS iceberg.kenya_health LOCATION 's3://iceberg-warehouse/kenya_health/';
```

After the first pipeline run (Step 10), register the raw tables pointing at the MinIO files.

### Step 9 — Connect Superset to Trino

In Superset → Settings → Database Connections → + Database:
- **Database type:** Trino
- **SQLAlchemy URI:** `trino://trino@trino:8080/iceberg`
- **Display name:** `Kenya Health Trino`

### Step 10 — Run the Pipeline

```bash
make pipeline-run
```

This triggers `kenya_health_monthly` in Airflow. Monitor at http://localhost:8080.

The full run takes approximately:
- Facilities ingestion: ~25 minutes (680 API pages × 20,391 records)
- Population + Geodata: ~2 minutes each
- dbt run: ~3 minutes (7 models + snapshot)
- Total: ~30 minutes end-to-end

### Step 11 — Share Publicly (Optional)

```bash
nohup cloudflared tunnel --url http://localhost:8088 &
cat nohup.out | grep trycloudflare
```

### Makefile Commands Reference

```bash
make build          # Build custom Airflow and Superset images
make up             # Start all 13 services
make down           # Stop all services (volumes preserved)
make restart        # Stop and start
make pipeline-run   # Trigger kenya_health_monthly DAG
make ps             # Show container status
make logs           # Stream all container logs
make clean          # WARNING: removes all volumes (data loss)
```

---

## Known Limitations & Future Work

### Known Limitations

| Limitation | Detail |
|-----------|--------|
| **Facilities data is from 2017 XLSX + live API** | The MOH KMHFR public API (`api.kmhfr.health.go.ke/api/public/facilities/`) provides current data but lacks some enrichment fields present in the 2017 HDX Excel (KEPH level granularity, ward-level breakdown). Production upgrade: use the authenticated KMHFR API for full field coverage. |
| **No sub-county population for most counties** | The KNBS 2019 Census CSV provides only county totals. Nairobi sub-county populations are handled via a dbt seed. Other county sub-county breakdowns would require the full KNBS Sub-County report. |
| **Choropleth map deck.gl limitation** | Superset 5.0 has confirmed bugs with deck.gl GeoJSON rendering (GitHub issues #32127, #33618). The map renders correctly with careful GeoJSON Feature wrapping but has viewport and 3D tilt edge cases. |
| **Superset Country Map only has 8 old provinces** | The built-in Kenya GeoJSON in Superset uses pre-2013 provincial boundaries (KE-100 to KE-800), not the current 47 counties. The choropleth uses a custom virtual dataset instead. |
| **Single-node Airflow worker** | `AIRFLOW__WEBSERVER__WORKERS=1` is set to fix session issues. For production, a proper distributed session store (Redis with Flask-Session) should be configured. |

### Future Work

- [ ] Integrate DHIS2 (KHIS) service utilisation data — actual monthly deliveries, ART patient volumes, TB case counts per facility — via MOH credential request to `servicedesk@health.go.ke`
- [ ] Add WorldPop high-resolution population rasters for sub-county disaggregation without manual seed files
- [ ] Deploy to a cloud VPS (Hetzner CX22, ~€4/month) for 24/7 availability
- [ ] Add Grafana for operational pipeline monitoring (DAG success rates, ingestion volumes, data freshness)
- [ ] Build a GitHub Actions CI/CD pipeline to run `dbt test` on PR to main
- [ ] Add Slowly Changing Dimension Type 2 analytics — "which counties gained or lost facilities in the last 12 months"
- [ ] Share dataset with MOH Kenya, UNICEF Kenya, Amref Health Africa, Code for Kenya, and HDX for public reuse

---

## References

- [Kenya Master Health Facility Registry (KMHFR)](https://kmhfr.health.go.ke)
- [KMHFR Public API](https://api.kmhfr.health.go.ke/api/public/facilities/)
- [KNBS 2019 Kenya Population and Housing Census](https://www.knbs.or.ke/2019-kenya-population-and-housing-census/)
- [HDX Kenya County Boundaries](https://data.humdata.org)
- [Apache Iceberg Documentation](https://iceberg.apache.org/docs/latest/)
- [Trino Documentation](https://trino.io/docs/current/)
- [dbt Core Documentation](https://docs.getdbt.com/)
- [Apache Superset Documentation](https://superset.apache.org/docs/intro)
- [OpenTofu Documentation](https://opentofu.org/docs/)

---

## Author

**Derrick Ryan Giggs**
- GitHub: [github.com/Derrick-Ryan-Giggs](https://github.com/Derrick-Ryan-Giggs)
- Medium: [medium.com/@derrickryangiggs](https://medium.com/@derrickryangiggs)


---

