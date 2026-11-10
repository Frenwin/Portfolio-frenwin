-- SCD2 validity ranges of one customer must be ordered and must not overlap.
select a.customer_unique_id, a.version_number, b.version_number as next_version
from {{ ref('dim_customers') }} as a
inner join {{ ref('dim_customers') }} as b
    on b.customer_unique_id = a.customer_unique_id
   and b.version_number = a.version_number + 1
where a.valid_to is distinct from b.valid_from
   or a.valid_from > b.valid_from
