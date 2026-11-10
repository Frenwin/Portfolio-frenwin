-- Every customer must have exactly one current SCD2 row.
select customer_unique_id, count(*) filter (where is_current) as current_rows
from {{ ref('dim_customers') }}
group by customer_unique_id
having count(*) filter (where is_current) <> 1
