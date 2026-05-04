-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/staging/stg_facilities.sql
--
-- Cleans and normalizes raw MOH KMHFL facility data.
-- Source: MinIO raw bucket → facilities JSON → Iceberg raw table
-- Filters to operational facilities only.
-- ============================================================

with source as (
    select * from {{ source('raw', 'facilities') }}
),

cleaned as (
    select
        -- identifiers
        cast(facility_code     as varchar)   as facility_code,
        cast(facility_name     as varchar)   as facility_name,

        -- normalize facility type into 4 standard categories
        case
            when lower(cast(facility_type as varchar)) like '%hospital%'       then 'Hospital'
            when lower(cast(facility_type as varchar)) like '%health centre%'  then 'Health Centre'
            when lower(cast(facility_type as varchar)) like '%dispensary%'     then 'Dispensary'
            when lower(cast(facility_type as varchar)) like '%clinic%'         then 'Clinic'
            else 'Other'
        end                                  as facility_type,

        -- location
        cast(county_name       as varchar)   as county_name,
        cast(sub_county_name   as varchar)   as sub_county_name,
        cast(ward_name         as varchar)   as ward_name,
        cast(latitude          as double)    as latitude,
        cast(longitude         as double)    as longitude,
        cast(operation_status  as varchar)   as operation_status,

        -- service availability flags
        cast(has_maternity     as boolean)   as has_maternity,
        cast(has_art           as boolean)   as has_art,
        cast(has_tb            as boolean)   as has_tb,
        cast(has_emergency     as boolean)   as has_emergency,
        cast(has_outpatient    as boolean)   as has_outpatient,

        cast(ingested_at       as timestamp) as ingested_at

    from source
    where
        -- only operational facilities
        lower(cast(operation_status as varchar)) = 'operational'
        -- drop records with no county
        and facility_code is not null
        and county_name   is not null
)

select * from cleaned