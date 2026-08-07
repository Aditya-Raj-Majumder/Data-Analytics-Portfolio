-- ============================================================
-- 06. Product Line Performance (All Orders)
-- ============================================================
-- Purpose: rank product lines by revenue contribution and see
-- which ones move the most units vs. which command higher prices
-- per order. Order count alone can mislead -- a product line
-- with fewer, pricier orders can outearn a high-volume one.

SELECT
    product_line,
    COUNT(*)                 AS n_orders,
    ROUND(SUM(total), 2)     AS gross_revenue,
    ROUND(AVG(total), 2)     AS avg_order_value,
    SUM(quantity)             AS units_sold
FROM sales
GROUP BY product_line
ORDER BY gross_revenue DESC;

-- Result:
--   Suspension & traction: 228 orders -> $73,014.21  (AOV $320.24, 2,145 units)
--   Frame & body:          166 orders -> $69,024.73  (AOV $415.81, 1,619 units)
--   Electrical system:     193 orders -> $43,612.71  (AOV $225.97, 1,698 units)
--   Braking system:        230 orders -> $38,350.15  (AOV $166.74, 2,130 units)
--   Engine:                 61 orders -> $37,945.38  (AOV $622.06,   627 units)
--   Miscellaneous:         122 orders -> $27,165.82  (AOV $222.67, 1,176 units)
--
-- Takeaway: Engine has the fewest orders of any product line (61)
-- but the highest average order value by a wide margin ($622.06)
-- -- it's a low-volume, high-ticket category. Braking System is
-- the opposite: highest order count, but the lowest AOV, so it
-- ranks only 4th in total revenue despite being the most-ordered
-- product line in the dataset.
