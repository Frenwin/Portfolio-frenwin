select
    geolocation_zip_code_prefix             as zip_code_prefix,
    geolocation_lat::double precision       as latitude,
    geolocation_lng::double precision       as longitude,
    geolocation_city                        as city,
    upper(geolocation_state)                as state
from {{ source('olist', 'geolocation') }}
