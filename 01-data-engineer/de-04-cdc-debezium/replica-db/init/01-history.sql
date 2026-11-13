-- Mirror tables (customers, products, orders, order_items, cdc_probe) are created by the
-- JDBC sink connector. This table is written by cdc/history.py and keeps what a mirror loses:
-- every status an order passed through, and when.

CREATE TABLE order_status_events (
    order_id     bigint      NOT NULL,
    lsn          bigint      NOT NULL,   -- position in the source WAL: unique per change
    op           char(1)     NOT NULL,   -- r = snapshot, c = insert, u = update, d = delete
    status       text,                   -- null for deletes
    changed_at   timestamptz NOT NULL,
    recorded_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (order_id, lsn)
);

-- SCD Type 2 view: one row per status with the interval it was valid.
-- Ordered by WAL position (lsn), the true order of changes; timestamps come from two clocks
-- (application updated_at vs commit time) and can disagree.
CREATE VIEW order_status_history AS
SELECT order_id, status, valid_from, valid_to, valid_to IS NULL AS is_current
FROM (
    SELECT order_id,
           op,
           status,
           changed_at AS valid_from,
           lead(changed_at) OVER (PARTITION BY order_id ORDER BY lsn, changed_at) AS valid_to
    FROM order_status_events
) e
WHERE op <> 'd';
