-- ============================================================
-- 03. Monthly Net Revenue Trend (All Orders) + Month-over-Month Growth
-- ============================================================
-- Purpose: establish the overall revenue trend across the three
-- months in scope before slicing by product line and warehouse.
-- Uses a window function (LAG) to compute month-over-month change
-- without a self-join.

WITH monthly AS (
    SELECT
        EXTRACT(MONTH FROM date)                              AS month_num,
        CASE EXTRACT(MONTH FROM date)
            WHEN 6 THEN 'June'
            WHEN 7 THEN 'July'
            WHEN 8 THEN 'August'
        END                                                    AS month,
        SUM(total * (1 - payment_fee))                         AS net_revenue
    FROM sales
    GROUP BY month_num
)
SELECT
    month,
    ROUND(net_revenue, 2)                                                          AS net_revenue,
    ROUND(net_revenue - LAG(net_revenue) OVER (ORDER BY month_num), 2)             AS change_vs_prev_month,
    ROUND(100.0 * (net_revenue - LAG(net_revenue) OVER (ORDER BY month_num))
          / LAG(net_revenue) OVER (ORDER BY month_num), 1)                         AS pct_change
FROM monthly
ORDER BY month_num;

-- Result:
--   June:    $93,659.04   (baseline)
--   July:    $91,895.85   (-$1,763.19, -1.9%)
--   August:  $98,653.53   (+$6,757.68, +7.4%)
--
-- Takeaway: revenue dipped slightly in July before recovering
-- strongly in August, ending the quarter up overall. Worth
-- checking whether the July dip lines up with a specific
-- warehouse or product line (see 07_top_wholesale_combinations.sql).
