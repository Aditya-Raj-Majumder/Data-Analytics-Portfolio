-- ============================================================
-- 02. Retail vs. Wholesale -- Order Volume vs. Revenue Contribution
-- ============================================================
-- Purpose: before narrowing in on wholesale, confirm that it's
-- actually worth the board's attention. This compares order COUNT
-- against revenue CONTRIBUTION for each client type -- a classic
-- check for whether a smaller segment is punching above its weight.

SELECT
    client_type,
    COUNT(*)                                                       AS n_orders,
    ROUND(SUM(total), 2)                                           AS gross_revenue,
    ROUND(AVG(total), 2)                                           AS avg_order_value,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sales), 1)      AS pct_of_orders,
    ROUND(100.0 * SUM(total) / (SELECT SUM(total) FROM sales), 1)  AS pct_of_revenue
FROM sales
GROUP BY client_type
ORDER BY gross_revenue DESC;

-- Result:
--   Wholesale:  225 orders (22.5% of orders) -> $159,642.33 (55.2% of revenue)
--   Retail:     775 orders (77.5% of orders) -> $129,470.67 (44.8% of revenue)
--
--   Wholesale avg order value: $709.52
--   Retail avg order value:    $167.06  (wholesale orders are ~4.2x larger)
--
-- Takeaway: wholesale is under a quarter of all orders but drives
-- more than half of gross revenue. This justifies the board's
-- specific interest in wholesale performance -- it's the higher-
-- leverage segment per order, even though retail has more orders.
