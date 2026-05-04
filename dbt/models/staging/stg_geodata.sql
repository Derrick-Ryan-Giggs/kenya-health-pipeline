-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/staging/stg_geodata.sql
--
-- Cleans Kenya county GeoJSON boundary data from HDX.
-- Source: MinIO raw bucket → geodata JSON → Iceberg raw table
-- ============================================================

with source as (
    select * from {{ source('raw', 'geodata') }}
),

cleaned as (
    select
        cast(county_code   as varchar)    as county_code,
        initcap(cast(county_name as varchar)) as county_name,

        -- geometry stored as JSON string — used by Superset choropleth
        cast(geometry      as varchar)    as geometry,

        cast(area_sqkm     as double)     as area_sqkm,
        cast(ingested_at   as timestamp)  as ingested_at

    from source
    where
        county_name is not null
        and geometry    is not null
)

select * from cleaned