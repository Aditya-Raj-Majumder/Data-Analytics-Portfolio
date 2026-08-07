-- ============================================================
-- 05. Warehouse Performance Comparison
-- ============================================================
-- Purpose: compare the three warehouses on order volume, gross
-- revenue, average order value, and how reliant each one is on
-- wholesale vs. retail business.

SELECT
    warehouse,
    COUNT(*)                                                                          AS n_orders,
    ROUND(SUM(total), 2)                                                              AS gross_revenue,
    ROUND(AVG(total), 2)                                                              AS avg_order_value,
    ROUND(SUM(CASE WHEN client_type = 'Wholesale' THEN total ELSE 0 END), 2)          AS wholesale_revenue,
    ROUND(100.0 * SUM(CASE WHEN client_type = 'Wholesale' THEN total ELSE 0 END)
          / SUM(total), 1)                                                            AS pct_wholesale
FROM sales
GROUP BY warehouse
ORDER BY gross_revenue DESC;

-- Result:
--   Central: 480 orders -> $141,982.88  (55.5% wholesale)
--   North:   340 orders -> $100,203.63  (57.9% wholesale)
--   West:    180 orders ->  $46,926.49  (48.4% wholesale)
--
-- Takeaway: Central is the largest warehouse by both volume and
-- revenue -- roughly 3x West's revenue. North has the highest
-- wholesale mix (57.9%), while West leans more retail (only
-- 48.4% wholesale) and has by far the smallest footprint of the
-- three, both in order count and revenue.
