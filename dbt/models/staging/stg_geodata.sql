-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/staging/stg_geodata.sql
-- ============================================================
with source as (
    select * from {{ source('raw', 'geodata') }}
),
cleaned as (
    select
        cast(county_code as varchar)                          as county_code,
        lower(cast(county_name as varchar))                   as county_name,
        cast(geometry    as varchar)                          as geometry,
        cast(area_sqkm   as double)                           as area_sqkm,
        cast(ingested_at as timestamp(6))                     as ingested_at
    from source
    where county_name is not null
    and   geometry    is not null
)
select * from cleaned
