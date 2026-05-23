with facility_services as (
    select
        county_name,
        count(*)                                          as total_facilities,
        sum(case when has_maternity  then 1 else 0 end)  as maternity_count,
        sum(case when has_art        then 1 else 0 end)  as art_count,
        sum(case when has_tb         then 1 else 0 end)  as tb_count,
        sum(case when has_emergency  then 1 else 0 end)  as emergency_count,
        sum(case when has_outpatient then 1 else 0 end)  as outpatient_count
    from {{ ref('stg_facilities') }}
    group by county_name
),
population as (
    select
        county_name,
        sum(population) as total_population
    from {{ ref('stg_population') }}
    where sub_county_name = '' or lower(sub_county_name) = lower(county_name)
    group by county_name
),
final as (
    select
        f.county_name,
        f.total_facilities,
        p.total_population,
        f.maternity_count,
        f.art_count,
        f.tb_count,
        f.emergency_count,
        f.outpatient_count,
        round(cast(f.maternity_count as double) / nullif(p.total_population, 0) * 100000, 2) as maternity_per_100k,
        round(cast(f.art_count       as double) / nullif(p.total_population, 0) * 100000, 2) as art_per_100k,
        round(cast(f.tb_count        as double) / nullif(p.total_population, 0) * 100000, 2) as tb_per_100k,
        round(cast(f.emergency_count as double) / nullif(p.total_population, 0) * 100000, 2) as emergency_per_100k,
        case when f.maternity_count < 3 then true else false end as maternity_gap_flag,
        case when f.art_count       < 2 then true else false end as art_gap_flag,
        case when f.tb_count        < 2 then true else false end as tb_gap_flag,
        case when f.emergency_count = 0 then true else false end as no_emergency_flag
    from facility_services f
    left join population p
        on regexp_replace(regexp_replace(lower(f.county_name), '-', ' '), '''', '') =
           regexp_replace(regexp_replace(lower(p.county_name), '-', ' '), '''', '')
)
select * from final
