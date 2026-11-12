-- Every accepted ride, once. event_id is the idempotency key for the whole sink.
CREATE TABLE rides (
    event_id        text PRIMARY KEY,
    run_id          text        NOT NULL,
    event_ts        timestamptz NOT NULL,   -- when the ride happened (event time)
    produced_at     timestamptz NOT NULL,   -- when the producer sent it
    ingested_at     timestamptz NOT NULL DEFAULT clock_timestamp(),  -- when it landed here
    batch_id        bigint      NOT NULL,
    user_id         text        NOT NULL,
    driver_id       text        NOT NULL,
    zone            text        NOT NULL,
    payment_method  text        NOT NULL,
    distance_km     numeric(6, 2) NOT NULL,
    fare_idr        integer     NOT NULL
);
CREATE INDEX rides_ingested_at_idx ON rides (ingested_at);
CREATE INDEX rides_run_id_idx ON rides (run_id);

-- Real-time demand per zone and minute, updated incrementally from newly inserted rides only.
CREATE TABLE zone_demand_1m (
    window_start  timestamptz NOT NULL,
    zone          text        NOT NULL,
    trips         integer     NOT NULL,
    revenue_idr   bigint      NOT NULL,
    distance_km   numeric(12, 2) NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (window_start, zone)
);

-- Final per-minute demand emitted by Spark once the watermark closes the window.
CREATE TABLE zone_demand_final (
    window_start  timestamptz NOT NULL,
    window_end    timestamptz NOT NULL,
    zone          text        NOT NULL,
    trips         integer     NOT NULL,
    revenue_idr   bigint      NOT NULL,
    finalized_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (window_start, zone)
);

-- Rides per user and minute; flagged_at is set the moment a user crosses the fraud threshold.
CREATE TABLE user_activity_1m (
    window_start  timestamptz NOT NULL,
    user_id       text        NOT NULL,
    rides         integer     NOT NULL,
    fare_idr      bigint      NOT NULL,
    flagged_at    timestamptz,
    PRIMARY KEY (window_start, user_id)
);

CREATE VIEW fraud_alerts AS
SELECT window_start, user_id, rides, fare_idr, flagged_at
FROM user_activity_1m
WHERE flagged_at IS NOT NULL;

-- Events that failed parsing or validation, keyed by their Kafka position (idempotent).
CREATE TABLE rejected_events (
    kafka_partition integer     NOT NULL,
    kafka_offset    bigint      NOT NULL,
    kafka_ts        timestamptz NOT NULL,
    reason          text        NOT NULL,
    raw_value       text,
    rejected_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (kafka_partition, kafka_offset)
);

-- One row per micro-batch per query, for throughput monitoring.
CREATE TABLE stream_batches (
    query          text    NOT NULL,
    batch_id       bigint  NOT NULL,
    rows_in        integer NOT NULL,
    rows_written   integer NOT NULL,
    processed_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (query, batch_id)
);
