-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/staging/stg_population.sql
--
-- Cleans KNBS population estimates.
-- Source: MinIO raw bucket → population JSON → Iceberg raw table
-- ============================================================

with source as (
    select * from {{ source('raw', 'population') }}
),

cleaned as (
    select
        cast(county_code   as varchar)    as county_code,

        -- standardize county name casing
        initcap(cast(county_name as varchar))   as county_name,
        initcap(cast(sub_county  as varchar))   as sub_county_name,

        cast(population    as bigint)     as population,
        cast(census_year   as integer)    as census_year,
        cast(ingested_at   as timestamp)  as ingested_at

    from source
    where
        population  is not null
        and population > 0
        and county_name is not null
)

select * from cleaned