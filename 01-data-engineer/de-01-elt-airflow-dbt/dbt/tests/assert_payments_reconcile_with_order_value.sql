-- Paid amount should match items + freight. Installment interest and vouchers cause
-- known differences, so this warns instead of failing and reports how many orders differ.
{{ config(severity='warn') }}

select order_id, order_value, payment_value, payment_value - order_value as difference
from {{ ref('fct_orders') }}
where order_status = 'delivered'
  and payment_value is not null
  and abs(payment_value - order_value) > 1.00
