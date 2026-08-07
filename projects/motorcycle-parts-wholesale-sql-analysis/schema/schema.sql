-- ============================================================
-- Schema: sales
-- Source: data/motorcycle_parts_sales.csv
-- Description: One row per order placed with a motorcycle parts
--              retailer operating three warehouses, June-Aug 2021.
-- ============================================================

CREATE TABLE sales (
    order_number   VARCHAR PRIMARY KEY,   -- Unique order identifier (e.g. 'N1', 'C42')
    date           DATE NOT NULL,         -- Order date (2021-06-01 to 2021-08-28)
    warehouse      VARCHAR NOT NULL,      -- 'North', 'Central', or 'West'
    client_type    VARCHAR NOT NULL,      -- 'Retail' or 'Wholesale'
    product_line   VARCHAR NOT NULL,      -- One of 6 part categories
    quantity       INT NOT NULL,          -- Units ordered
    unit_price     FLOAT NOT NULL,        -- Price per unit ($)
    total          FLOAT NOT NULL,        -- Gross order value ($)
    payment        VARCHAR NOT NULL,      -- 'Credit card', 'Transfer', or 'Cash'
    payment_fee    FLOAT NOT NULL         -- Fee rate charged on this payment method (e.g. 0.03 = 3%)
);

-- Notes:
-- * payment_fee is a RATE, not a dollar amount. Dollar fee on an order
--   = total * payment_fee. This matters for every net-revenue query below.
-- * 1,000 orders total; no missing values in any column.
