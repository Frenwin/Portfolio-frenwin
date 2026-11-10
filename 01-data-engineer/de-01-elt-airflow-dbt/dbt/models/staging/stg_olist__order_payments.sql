select
    order_id || '-' || payment_sequential  as payment_key,
    order_id,
    payment_sequential::int                as payment_sequence,
    payment_type,
    payment_installments::int              as installments,
    payment_value::numeric(12, 2)          as payment_value
from {{ source('olist', 'order_payments') }}
