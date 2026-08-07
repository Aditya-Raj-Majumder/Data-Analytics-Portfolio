-- ============================================================
-- 01. Data Overview
-- ============================================================
-- Purpose: sanity-check the dataset before analyzing it -- row
-- count, date coverage, and the distinct values in each
-- categorical column. Standard first step before trusting any
-- aggregation downstream.

SELECT
    COUNT(*)                       AS n_orders,
    MIN(date)                      AS first_order_date,
    MAX(date)                      AS last_order_date,
    COUNT(DISTINCT product_line)   AS n_product_lines,
    COUNT(DISTINCT warehouse)      AS n_warehouses,
    COUNT(DISTINCT payment)        AS n_payment_methods
FROM sales;

-- Result:
--   n_orders: 1,000
--   date range: 2021-06-01 to 2021-08-28  (June-August, 3 full months)
--   6 product lines, 3 warehouses, 3 payment methods
--   No missing values in any column (checked separately during load)

-- ------------------------------------------------------------
-- Distinct categorical values, for reference:
--   warehouse:     North, Central, West
--   client_type:   Retail, Wholesale
--   product_line:  Braking system, Suspension & traction, Frame & body,
--                   Electrical system, Engine, Miscellaneous
--   payment:       Cash, Credit card, Transfer
-- ------------------------------------------------------------
