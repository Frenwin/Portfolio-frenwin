-- SCD Type 2: one row per customer address version.
-- valid_from = first purchase made at that address; valid_to = start of the next version (null = current).
with versions as (
    select
        customer_sk,
        customer_unique_id,
        version_number,
        min(zip_code_prefix) as zip_code_prefix,
        min(city)            as city,
        min(state)           as state,
        min(purchased_at)    as valid_from,
        count(*)             as orders_in_version
    from {{ ref('int_customer_versions') }}
    group by customer_sk, customer_unique_id, version_number
)

select
    v.customer_sk,
    v.customer_unique_id,
    v.version_number,
    v.zip_code_prefix,
    v.city,
    v.state,
    loc.latitude,
    loc.longitude,
    v.orders_in_version,
    v.valid_from,
    lead(v.valid_from) over (partition by v.customer_unique_id order by v.version_number) as valid_to,
    lead(v.valid_from) over (partition by v.customer_unique_id order by v.version_number) is null as is_current
from versions as v
left join {{ ref('int_zip_code_locations') }} as loc
    on loc.zip_code_prefix = v.zip_code_prefix
