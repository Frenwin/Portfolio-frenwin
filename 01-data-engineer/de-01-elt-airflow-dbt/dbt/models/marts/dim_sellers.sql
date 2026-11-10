select
    s.seller_id,
    s.zip_code_prefix,
    s.city,
    s.state,
    loc.latitude,
    loc.longitude
from {{ ref('stg_olist__sellers') }} as s
left join {{ ref('int_zip_code_locations') }} as loc
    on loc.zip_code_prefix = s.zip_code_prefix
