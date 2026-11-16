# A wrong-results case in PostgreSQL 16.16

While writing Q3, a "top 15 categories" query returned all 74 categories. The cause was not the SQL.

## Minimal reproduction

```sql
WITH c AS (SELECT g AS r FROM generate_series(1, 10) g),
     k AS (SELECT rank() OVER (ORDER BY r DESC) AS rnk,
                  sum(r) OVER (ORDER BY r DESC ROWS UNBOUNDED PRECEDING) AS running_sum
           FROM c)
SELECT count(*) AS rows_returned FROM k WHERE rnk <= 3;
```

| Server | `rows_returned` |
| --- | ---: |
| PostgreSQL 16.16 (`postgres:16` image, Nov 2026) | **10** (wrong) |
| PostgreSQL 17.12 (`postgres:17` image) | 3 (correct) |

## What happens

`EXPLAIN (VERBOSE)` on 16.16 shows a single `WindowAgg` node with **no filter and no run condition**: the `rnk <= 3` predicate is gone from the plan. The trigger is two window functions over the same ordering, where one is `rank()` filtered from outside and the other uses an explicit `ROWS` frame. With only one of them, or with a different frame, the filter is applied correctly.

PostgreSQL 15 introduced "run conditions", which push filters on monotonic window functions such as `rank()` into the window node so it can stop early. The behaviour above is consistent with that pushdown losing the predicate; 17.12 returns the right answer.

## Workaround

Mark the CTE `MATERIALIZED`, which stops the planner pushing outer predicates into it:

```sql
k AS MATERIALIZED (SELECT rank() OVER (...) AS rnk, sum(r) OVER (... ROWS UNBOUNDED PRECEDING) ...)
```

or filter on a column computed in a separate CTE level.

## Lesson

A result that cannot be true ("top 15" returning 74 rows) is a test failing, even without a test suite. Checking row counts against what the question implies caught it before the number went into a report.
