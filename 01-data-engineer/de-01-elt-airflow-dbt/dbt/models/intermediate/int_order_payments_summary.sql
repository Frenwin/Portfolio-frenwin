select
    order_id,
    count(*)                                                       as payment_count,
    sum(payment_value)                                             as payment_value,
    max(installments)                                              as max_installments,
    (array_agg(payment_type order by payment_value desc, payment_sequence))[1] as primary_payment_type
from {{ ref('stg_olist__order_payments') }}
group by order_id
