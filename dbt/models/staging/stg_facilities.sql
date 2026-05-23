with source as (
    select * from {{ source("raw", "facilities") }}
),
cleaned as (
    select
        cast(facility_id       as varchar)   as facility_id,
        cast(facility_code     as varchar)   as facility_code,
        cast(facility_name     as varchar)   as facility_name,
        case
            when lower(cast(facility_type as varchar)) like '%hospital%'       then 'Hospital'
            when lower(cast(facility_type as varchar)) like '%health centre%'  then 'Health Centre'
            when lower(cast(facility_type as varchar)) like '%dispensary%'     then 'Dispensary'
            when lower(cast(facility_type as varchar)) like '%clinic%'         then 'Clinic'
            else 'Other'
        end                                  as facility_type,
        cast(county_name       as varchar)   as county_name,
        cast(sub_county_name   as varchar)   as sub_county_name,
        cast(ward_name         as varchar)   as ward_name,
        cast(latitude          as double)    as latitude,
        cast(longitude         as double)    as longitude,
        cast(operation_status  as varchar)   as operation_status,
        cast(has_maternity     as boolean)   as has_maternity,
        cast(has_art           as boolean)   as has_art,
        cast(has_tb            as boolean)   as has_tb,
        cast(has_emergency     as boolean)   as has_emergency,
        cast(has_outpatient    as boolean)   as has_outpatient,
        cast(ingested_at       as timestamp(6)) as ingested_at,
        row_number() over (
            partition by cast(facility_id as varchar)
            order by cast(ingested_at as timestamp(6)) desc
        ) as rn
    from source
    where lower(cast(operation_status as varchar)) = 'operational'
    and   facility_code is not null
    and   county_name   is not null
)
select
    facility_id, facility_code, facility_name, facility_type,
    county_name, sub_county_name, ward_name,
    latitude, longitude, operation_status,
    has_maternity, has_art, has_tb, has_emergency, has_outpatient,
    ingested_at
from cleaned
where rn = 1
