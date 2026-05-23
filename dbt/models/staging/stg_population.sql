-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/staging/stg_population.sql
-- ============================================================
with source as (
    select * from {{ source('raw', 'population') }}
),
cleaned as (
    select
        cast(county_code as varchar)              as county_code,
        lower(cast(county_name as varchar))       as county_name,
        lower(cast(sub_county  as varchar))       as sub_county_name,
        cast(population  as bigint)               as population,
        cast(census_year as integer)              as census_year,
        cast(ingested_at as timestamp(6))         as ingested_at
    from source
    where population  is not null
    and   population  > 0
    and   county_name is not null
)
select * from cleaned
