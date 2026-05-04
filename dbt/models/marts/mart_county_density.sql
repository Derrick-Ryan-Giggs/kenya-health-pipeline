-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/marts/mart_county_density.sql
--
-- County facility density scorecard for all 47 Kenya counties.
-- Answers:
--   Which county has the worst facility-to-population ratio?
--   How does Nairobi compare to other urban counties?
--   What is the breakdown of facility types per county?
-- ============================================================

with facilities as (
    select
        county_name,
        facility_type,
        count(*)                                          as facility_count,
        sum(case when has_maternity  then 1 else 0 end)  as maternity_count,
        sum(case when has_art        then 1 else 0 end)  as art_count,
        sum(case when has_tb         then 1 else 0 end)  as tb_count,
        sum(case when has_emergency  then 1 else 0 end)  as emergency_count
    from {{ ref('stg_facilities') }}
    group by county_name, facility_type
),

-- weighted score per county:
-- hospital = 4 pts, health centre = 2 pts, dispensary/clinic = 1 pt
weighted as (
    select
        county_name,
        sum(facility_count)   as total_facilities,
        sum(maternity_count)  as maternity_facilities,
        sum(art_count)        as art_facilities,
        sum(tb_count)         as tb_facilities,
        sum(emergency_count)  as emergency_facilities,

        -- type breakdown
        sum(case when facility_type = 'Hospital'      then facility_count else 0 end) as hospital_count,
        sum(case when facility_type = 'Health Centre' then facility_count else 0 end) as health_centre_count,
        sum(case when facility_type = 'Dispensary'    then facility_count else 0 end) as dispensary_count,
        sum(case when facility_type = 'Clinic'        then facility_count else 0 end) as clinic_count,

        sum(
            facility_count * case facility_type
                when 'Hospital'      then 4
                when 'Health Centre' then 2
                else 1
            end
        ) as weighted_score
    from facilities
    group by county_name
),

population as (
    select
        county_name,
        sum(population) as total_population
    from {{ ref('stg_population') }}
    -- county-level rows only (sub_county_name matches county or is blank)
    where
        sub_county_name = ''
        or lower(sub_county_name) = lower(county_name)
    group by county_name
),

final as (
    select
        w.county_name,
        w.total_facilities,
        w.hospital_count,
        w.health_centre_count,
        w.dispensary_count,
        w.clinic_count,
        w.maternity_facilities,
        w.art_facilities,
        w.tb_facilities,
        w.emergency_facilities,
        w.weighted_score,
        p.total_population,

        -- facilities per 10,000 people
        round(
            cast(w.total_facilities as double)
            / nullif(p.total_population, 0) * 10000,
            2
        ) as facilities_per_10k,

        -- weighted density per 10,000 people
        round(
            cast(w.weighted_score as double)
            / nullif(p.total_population, 0) * 10000,
            2
        ) as weighted_density_per_10k,

        -- rank: 1 = most underserved
        rank() over (
            order by
                cast(w.total_facilities as double)
                / nullif(p.total_population, 0) asc
        ) as density_rank

    from weighted w
    left join population p using (county_name)
)

select * from final