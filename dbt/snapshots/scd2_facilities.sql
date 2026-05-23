-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- snapshots/scd2_facilities.sql
--
-- SCD Type 2 snapshot tracking every change to every facility.
-- Answers:
--   Has Nairobi's facility count improved over time?
--   Which county added the most new facilities?
--   When was a specific facility first registered?
--   Which facilities were upgraded from dispensary to health centre?
--
-- dbt adds these columns automatically:
--   dbt_scd_id       — unique row identifier
--   dbt_updated_at   — when this version was created
--   dbt_valid_from   — when this record became active
--   dbt_valid_to     — when this record was superseded (null = current)
--   dbt_is_deleted   — true if facility no longer appears in source
-- ============================================================

{% snapshot scd2_facilities %}

{{
    config(
        target_schema='snapshots',
        unique_key='facility_id',
        strategy='check',
        check_cols=[
            'facility_name',
            'facility_type',
            'operation_status',
            'county_name',
            'sub_county_name',
            'has_maternity',
            'has_art',
            'has_tb',
            'has_emergency',
            'has_outpatient',
            'latitude',
            'longitude'
        ],
        invalidate_hard_deletes=True
    )
}}

select
    facility_id,
    facility_code,
    facility_name,
    facility_type,
    county_name,
    sub_county_name,
    ward_name,
    latitude,
    longitude,
    operation_status,
    has_maternity,
    has_art,
    has_tb,
    has_emergency,
    has_outpatient,
    ingested_at
from {{ ref('stg_facilities') }}

{% endsnapshot %}
