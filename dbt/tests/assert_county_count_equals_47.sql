-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- tests/assert_county_count_equals_47.sql
--
-- Fails if the county density mart does not cover all 47 counties.
-- Returns rows on failure, empty result = test passes.
-- ============================================================

select count(*) as county_count
from {{ ref('mart_county_density') }}
having count(*) != 47