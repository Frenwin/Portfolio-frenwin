-- review_id alone is not unique: the same review can be attached to several orders,
-- so the grain is (review_id, order_id).
select
    review_id || '-' || order_id                    as review_key,
    review_id,
    order_id,
    review_score::int                               as review_score,
    nullif(trim(review_comment_title), '')          as comment_title,
    nullif(trim(review_comment_message), '')        as comment_message,
    review_creation_date::timestamp                 as created_at,
    review_answer_timestamp::timestamp              as answered_at
from {{ source('olist', 'order_reviews') }}
