-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/marts/mart_nairobi_subcounty.sql
--
-- Nairobi sub-county drill-down — exposes inequality hidden
-- inside Nairobi's aggregate numbers.
-- Answers:
--   How many facilities per 10k in Kibera vs Westlands?
--   Which Nairobi sub-counties have no maternity services?
--   Where are the biggest investment gaps within Nairobi?
-- ============================================================

with nairobi_facilities as (
    select *
    from {{ ref('stg_facilities') }}
    where lower(county_name) = 'nairobi'
),

subcounty_counts as (
    select
        sub_county_name,
        count(*)                                          as total_facilities,
        sum(case when has_maternity  then 1 else 0 end)  as maternity_count,
        sum(case when has_art        then 1 else 0 end)  as art_count,
        sum(case when has_tb         then 1 else 0 end)  as tb_count,
        sum(case when has_emergency  then 1 else 0 end)  as emergency_count,

        -- facility type breakdown
        sum(case when facility_type = 'Hospital'      then 1 else 0 end) as hospital_count,
        sum(case when facility_type = 'Health Centre' then 1 else 0 end) as health_centre_count,
        sum(case when facility_type = 'Dispensary'    then 1 else 0 end) as dispensary_count,
        sum(case when facility_type = 'Clinic'        then 1 else 0 end) as clinic_count
    from nairobi_facilities
    where sub_county_name != ''
    group by sub_county_name
),

nairobi_population as (
    select
        sub_county_name,
        population
    from {{ ref('stg_population') }}
    where
        lower(county_name) = 'nairobi'
        and lower(sub_county_name) != 'nairobi'
        and sub_county_name != ''
),

final as (
    select
        s.sub_county_name,
        s.total_facilities,
        p.population,
        s.maternity_count,
        s.art_count,
        s.tb_count,
        s.emergency_count,
        s.hospital_count,
        s.health_centre_count,
        s.dispensary_count,
        s.clinic_count,

        -- density
        round(
            cast(s.total_facilities as double)
            / nullif(p.population, 0) * 10000,
            2
        ) as facilities_per_10k,

        -- gap flags
        case when s.maternity_count = 0 then true else false end as no_maternity_flag,
        case when s.art_count       = 0 then true else false end as no_art_flag,
        case when s.emergency_count = 0 then true else false end as no_emergency_flag,

        -- rank: 1 = most underserved sub-county in Nairobi
        rank() over (
            order by
                cast(s.total_facilities as double)
                / nullif(p.population, 0) asc
        ) as subcounty_density_rank

    from subcounty_counts s
    left join nairobi_population p using (sub_county_name)
)

select * from final