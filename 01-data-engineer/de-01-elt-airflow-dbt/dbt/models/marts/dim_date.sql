-- Calendar covering every purchase, delivery and estimated delivery date in the data.
with bounds as (
    select
        min(purchased_at)::date as first_day,
        greatest(
            max(purchased_at),
            max(estimated_delivery_at),
            max(delivered_to_customer_at)
        )::date as last_day
    from {{ ref('stg_olist__orders') }}
),

days as (
    select generate_series(first_day, last_day, interval '1 day')::date as date_day
    from bounds
)

select
    to_char(date_day, 'YYYYMMDD')::int        as date_key,
    date_day,
    extract(year from date_day)::int          as year,
    extract(quarter from date_day)::int       as quarter,
    extract(month from date_day)::int         as month,
    to_char(date_day, 'Mon')                  as month_name,
    date_trunc('month', date_day)::date       as month_start,
    date_trunc('week', date_day)::date        as week_start,
    extract(isodow from date_day)::int        as day_of_week,
    to_char(date_day, 'Dy')                   as day_name,
    extract(isodow from date_day) in (6, 7)   as is_weekend
from days
