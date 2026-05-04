-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- models/marts/mart_underserved_counties.sql
--
-- Ranked underserved counties scorecard with severity scores.
-- Answers:
--   Which 10 counties are most urgently underserved?
--   What specific services are missing in bottom-ranked counties?
--   How much investment would bring each county to baseline?
-- ============================================================

with density as (
    select * from {{ ref('mart_county_density') }}
),

gaps as (
    select * from {{ ref('mart_service_gaps') }}
),

scored as (
    select
        d.county_name,
        d.total_facilities,
        d.total_population,
        d.facilities_per_10k,
        d.weighted_density_per_10k,
        d.density_rank,
        d.hospital_count,
        d.health_centre_count,
        d.dispensary_count,
        d.clinic_count,
        g.maternity_count,
        g.art_count,
        g.tb_count,
        g.emergency_count,
        g.maternity_per_100k,
        g.art_per_100k,
        g.tb_per_100k,
        g.emergency_per_100k,
        g.maternity_gap_flag,
        g.art_gap_flag,
        g.tb_gap_flag,
        g.no_emergency_flag,

        -- severity score — higher = more underserved
        (
            -- density score
            case
                when d.facilities_per_10k < 1  then 4
                when d.facilities_per_10k < 2  then 3
                when d.facilities_per_10k < 5  then 2
                else 1
            end
            -- service gap penalties
            + case when g.maternity_gap_flag then 2 else 0 end
            + case when g.art_gap_flag       then 2 else 0 end
            + case when g.tb_gap_flag        then 1 else 0 end
            + case when g.no_emergency_flag  then 3 else 0 end
        ) as severity_score,

        -- estimated new facilities needed to reach 2 per 10k baseline
        greatest(
            0,
            cast(
                ceil(2.0 * d.total_population / 10000) - d.total_facilities
            as integer)
        ) as facilities_needed_to_baseline

    from density d
    left join gaps g using (county_name)
)

select
    *,
    rank() over (order by severity_score desc) as underserved_rank
from scored