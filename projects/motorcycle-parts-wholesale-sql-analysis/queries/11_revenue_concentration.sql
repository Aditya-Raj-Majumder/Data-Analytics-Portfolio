-- ============================================================
-- 11. Revenue Concentration -- Do a Few Large Orders Drive the Business?
-- ============================================================
-- Purpose: a classic Pareto check -- what share of revenue comes
-- from the largest orders, and what proportion of those orders
-- are wholesale? Ties queries 02 and 06 together into a single
-- concentration story.

WITH ranked AS (
    SELECT
        order_number,
        total,
        client_type,
        ROW_NUMBER() OVER (ORDER BY total DESC) AS rn,
        COUNT(*) OVER ()                        AS n_total
    FROM sales
),
top_20_pct AS (
    SELECT * FROM ranked WHERE rn <= n_total * 0.2
)
SELECT
    COUNT(*)                                                                AS n_orders_in_top20pct,
    ROUND(SUM(total), 2)                                                    AS revenue_from_top20pct,
    ROUND(100.0 * SUM(total) / (SELECT SUM(total) FROM sales), 1)          AS pct_of_total_revenue,
    SUM(CASE WHEN client_type = 'Wholesale' THEN 1 ELSE 0 END)             AS n_wholesale_in_top20,
    ROUND(100.0 * SUM(CASE WHEN client_type = 'Wholesale' THEN 1 ELSE 0 END)
          / COUNT(*), 1)                                                    AS pct_wholesale_in_top20
FROM top_20_pct;

-- Result:
--   The top 200 orders (20% of all 1,000 orders, by dollar value)
--   generate $166,127.52 -- 57.5% of total revenue.
--
--   Of those 200 largest orders, 154 (77.0%) are Wholesale --
--   even though wholesale is only 22.5% of ALL orders (query 02).
--
-- Takeaway: this closes the loop on the whole analysis. Wholesale
-- isn't just outperforming on average order size (query 02) or
-- winning most warehouse matchups (query 07) -- it's also heavily
-- over-represented among the single largest, most valuable orders
-- in the business. The revenue concentration isn't just "wholesale
-- vs retail" in the aggregate; it's concentrated in a relatively
-- small number of large wholesale orders, most of them Engine
-- parts out of Central and North (see the largest individual
-- orders in results/11_top_orders.csv). A handful of accounts or
-- order patterns like these are worth protecting and understanding
-- specifically, not just managing at the segment-average level.
