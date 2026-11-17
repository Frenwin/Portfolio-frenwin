-- Q6. Do new users come back? Weekly cohort retention.
-- Techniques: cohort defined by the first_visit event, DATE_DIFF in weeks, retention as share of cohort size.
WITH activity AS (
    SELECT DISTINCT
        user_pseudo_id,
        DATE_TRUNC(PARSE_DATE('%Y%m%d', event_date), WEEK(MONDAY)) AS week,
        event_name = 'first_visit'                                  AS is_first_visit
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201102' AND '20210131'
),
cohorts AS (
    -- only users whose first visit falls inside the data, so every cohort is genuinely new
    SELECT user_pseudo_id, MIN(week) AS cohort_week
    FROM activity
    WHERE is_first_visit
    GROUP BY user_pseudo_id
),
cohort_activity AS (
    SELECT c.cohort_week, DATE_DIFF(a.week, c.cohort_week, WEEK) AS week_number, a.user_pseudo_id
    FROM cohorts c
    JOIN (SELECT DISTINCT user_pseudo_id, week FROM activity) a USING (user_pseudo_id)
    WHERE a.week >= c.cohort_week
),
sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_pseudo_id) AS cohort_size FROM cohorts GROUP BY cohort_week
)
SELECT
    ca.cohort_week,
    s.cohort_size,
    ca.week_number,
    COUNT(DISTINCT ca.user_pseudo_id)                                  AS active_users,
    ROUND(100 * COUNT(DISTINCT ca.user_pseudo_id) / s.cohort_size, 2)  AS retention_pct
FROM cohort_activity ca
JOIN sizes s USING (cohort_week)
GROUP BY ca.cohort_week, s.cohort_size, ca.week_number
ORDER BY ca.cohort_week, ca.week_number;
