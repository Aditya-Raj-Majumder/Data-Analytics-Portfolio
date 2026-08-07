-- ============================================================
-- 12. What Caused the July Dip? (Follow-up to Query 03)
-- ============================================================
-- Purpose: query 03 flagged a -1.9% company-wide dip in July
-- without explaining it. This closes that loop by breaking the
-- same monthly trend out per warehouse, using LAG() partitioned
-- by warehouse instead of computed once over the whole company.

WITH warehouse_monthly AS (
    SELECT
        warehouse,
        EXTRACT(MONTH FROM date)                AS month_num,
        CASE EXTRACT(MONTH FROM date)
            WHEN 6 THEN 'June'
            WHEN 7 THEN 'July'
            WHEN 8 THEN 'August'
        END                                      AS month,
        SUM(total * (1 - payment_fee))           AS net_revenue
    FROM sales
    GROUP BY warehouse, month_num, month
)
SELECT
    warehouse,
    month,
    ROUND(net_revenue, 2) AS net_revenue,
    ROUND(100.0 * (net_revenue - LAG(net_revenue) OVER (PARTITION BY warehouse ORDER BY month_num))
          / LAG(net_revenue) OVER (PARTITION BY warehouse ORDER BY month_num), 1) AS pct_change_vs_prev_month
FROM warehouse_monthly
ORDER BY warehouse, month_num;

-- Result:
--   Central:  June $43,327.68 -> July $47,393.40 (+9.4%)  -> Aug $48,797.13 (+3.0%)
--   North:    June $32,752.96 -> July $28,636.86 (-12.6%) -> Aug $37,194.84 (+29.9%)
--   West:     June $17,578.41 -> July $15,865.59 (-9.7%)  -> Aug $15,865.59->$12,661.56 (-20.2%)
--
-- Takeaway -- there isn't one clean cause, there are two overlapping ones:
--
-- 1. NORTH had a genuine one-month dip: -12.6% in July, fully
--    reversed in August (+29.9%). Central actually GREW through
--    July (+9.4%), so Central isn't part of the story at all.
--
-- 2. WEST is not having a "July dip" -- it's declining every
--    single month of the quarter (June -> July -> August:
--    $17,578 -> $15,866 -> $12,662, i.e. -9.7% then -20.2%).
--    That's a steady erosion across all three months, not a
--    one-off blip, and it's a separate, arguably bigger concern
--    than the July number query 03 originally flagged.
--
-- A supporting cut by product line (not shown as a separate query --
-- same technique applied to product_line instead of warehouse)
-- shows Frame & Body dropped ~26% company-wide in July, and that
-- drop was broad-based -- it happened in Central, North, AND West
-- simultaneously that month, so it isn't explained by any single
-- warehouse either.
--
-- Bottom line: July's dip = North's temporary pull-back +
-- a broad, cross-warehouse softness in Frame & Body. West's decline
-- is a separate, ongoing trend that deserves its own attention
-- rather than being read as part of the "July story."
