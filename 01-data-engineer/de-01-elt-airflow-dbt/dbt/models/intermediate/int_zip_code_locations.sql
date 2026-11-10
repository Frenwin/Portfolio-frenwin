-- One row per zip code prefix. Points outside Brazil's bounding box are dropped
-- before averaging, so a few bad coordinates cannot drag a location into the ocean.
with points as (
    select *
    from {{ ref('stg_olist__geolocation') }}
    where latitude  between -34.0 and 5.5
      and longitude between -74.0 and -34.0
)

select
    zip_code_prefix,
    avg(latitude)                              as latitude,
    avg(longitude)                             as longitude,
    mode() within group (order by city)        as city,
    mode() within group (order by state)       as state,
    count(*)                                   as source_points
from points
group by zip_code_prefix
