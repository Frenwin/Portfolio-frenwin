-- Operational database of an online shop. Debezium reads its write-ahead log, never its tables.

CREATE TABLE customers (
    id          bigserial PRIMARY KEY,
    name        text        NOT NULL,
    email       text        NOT NULL UNIQUE,
    city        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id          bigserial PRIMARY KEY,
    name        text          NOT NULL,
    category    text          NOT NULL,
    price_idr   numeric(12, 2) NOT NULL CHECK (price_idr > 0),
    stock       integer       NOT NULL CHECK (stock >= 0),
    updated_at  timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id           bigserial PRIMARY KEY,
    customer_id  bigint        NOT NULL REFERENCES customers (id),
    status       text          NOT NULL CHECK (status IN ('pending', 'paid', 'packed', 'shipped', 'delivered', 'cancelled')),
    total_idr    numeric(14, 2) NOT NULL,
    created_at   timestamptz   NOT NULL DEFAULT now(),
    updated_at   timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    order_id        bigint        NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    line_no         integer       NOT NULL,
    product_id      bigint        NOT NULL REFERENCES products (id),
    quantity        integer       NOT NULL CHECK (quantity > 0),
    unit_price_idr  numeric(12, 2) NOT NULL,
    PRIMARY KEY (order_id, line_no)
);

-- Rows written only to measure replication lag.
CREATE TABLE cdc_probe (
    id          bigserial PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- Updates on orders carry the full previous row, so consumers can see the old status.
ALTER TABLE orders REPLICA IDENTITY FULL;

-- Least privilege: Debezium may replicate and read, nothing else.
CREATE ROLE debezium WITH LOGIN REPLICATION PASSWORD 'debezium';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

-- Created up front so the connector does not need table ownership to create it.
CREATE PUBLICATION dbz_publication FOR TABLE customers, products, orders, order_items, cdc_probe;
