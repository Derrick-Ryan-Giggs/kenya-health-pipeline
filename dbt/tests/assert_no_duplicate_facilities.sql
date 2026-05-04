-- ============================================================
-- Kenya Health Facility Mapping Pipeline
-- tests/assert_no_duplicate_facilities.sql
--
-- Fails if any facility_code appears more than once.
-- Returns rows on failure, empty result = test passes.
-- ============================================================

select
    facility_code,
    count(*) as n
from {{ ref('stg_facilities') }}
group by facility_code
having count(*) > 1