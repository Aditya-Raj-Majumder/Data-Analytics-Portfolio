-- ============================================================
-- 04. Wholesale Net Revenue by Product Line, Month, and Warehouse
-- ============================================================
-- Purpose: THE core deliverable requested by the board -- net
-- wholesale revenue for every product line / month / warehouse
-- combination. Net revenue = gross total minus the dollar cost
-- of payment processing fees (payment_fee is a RATE, so it must
-- be applied per-row before aggregating -- see README for why).

SELECT
    product_line,
    CASE EXTRACT(MONTH FROM date)
        WHEN 6 THEN 'June'
        WHEN 7 THEN 'July'
        WHEN 8 THEN 'August'
    END                                             AS month,
    warehouse,
    ROUND(SUM(total * (1 - payment_fee))::numeric, 2) AS net_revenue
FROM sales
WHERE client_type = 'Wholesale'
GROUP BY product_line, warehouse, month
ORDER BY product_line, month, net_revenue DESC;

-- Sample of results (18 rows total: 6 product lines x 3 months,
-- up to 3 warehouse rows each):
--
--   product_line     | month  | warehouse | net_revenue
--   Braking system    | June   | Central   | 3,648.14
--   Braking system    | June   | North     | 1,472.93
--   Braking system    | June   | West      | 1,200.64
--   Braking system    | July   | Central   | 3,740.94
--   Braking system    | July   | West      | 3,030.39
--   Braking system    | July   | North     | 2,568.55
--   ...
--
-- Full output: see results/04_wholesale_revenue_by_product_month_warehouse.csv
