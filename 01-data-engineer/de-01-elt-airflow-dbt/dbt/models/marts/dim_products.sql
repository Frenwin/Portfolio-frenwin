select
    p.product_id,
    coalesce(p.category_name_pt, 'unknown')                       as category_name_pt,
    -- two categories have no translation in the source; fall back to the Portuguese name
    coalesce(t.category_name_en, p.category_name_pt, 'unknown')   as category_name,
    p.name_length,
    p.description_length,
    p.photos_qty,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm,
    p.length_cm * p.height_cm * p.width_cm                        as volume_cm3
from {{ ref('stg_olist__products') }} as p
left join {{ ref('stg_olist__product_category_translation') }} as t
    on t.category_name_pt = p.category_name_pt
