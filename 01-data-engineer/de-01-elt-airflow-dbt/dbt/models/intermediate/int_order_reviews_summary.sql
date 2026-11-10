-- Some orders have more than one review; keep the average and the latest score.
select
    order_id,
    count(*)                                                       as review_count,
    round(avg(review_score), 2)                                    as avg_review_score,
    (array_agg(review_score order by created_at desc, review_id))[1] as latest_review_score,
    bool_or(comment_message is not null)                           as has_comment
from {{ ref('stg_olist__order_reviews') }}
group by order_id
