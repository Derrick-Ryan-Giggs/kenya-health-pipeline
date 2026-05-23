select
    facility_id,
    count(*) as n
from {{ ref('stg_facilities') }}
group by facility_id
having count(*) > 1
