-- ============================================================
-- 07. Best-Performing Warehouse per Product Line per Month (Wholesale)
-- ============================================================
-- Purpose: turn the 48-row breakdown from query 04 into a direct
-- answer to "which warehouse should we highlight for each product
-- line, each month?" Uses a CTE + RANK() window function to pick
-- the top warehouse within each (product_line, month) group,
-- instead of eyeballing the full result set.

WITH monthly_wholesale AS (
    SELECT
        product_line,
        CASE EXTRACT(MONTH FROM date)
            WHEN 6 THEN 'June'
            WHEN 7 THEN 'July'
            WHEN 8 THEN 'August'
        END                                     AS month,
        EXTRACT(MONTH FROM date)                AS month_num,
        warehouse,
        SUM(total * (1 - payment_fee))          AS net_revenue
    FROM sales
    WHERE client_type = 'Wholesale'
    GROUP BY product_line, warehouse, month, month_num
),
ranked AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY product_line, month
            ORDER BY net_revenue DESC
        ) AS warehouse_rank
    FROM monthly_wholesale
)
SELECT product_line, month, warehouse, ROUND(net_revenue, 2) AS net_revenue
FROM ranked
WHERE warehouse_rank = 1
ORDER BY product_line, month_num;

-- Result (18 rows -- one winning warehouse per product line per month):
--   Braking System:  Central wins all 3 months (June $3,648.14 / July $3,740.94 / Aug $3,009.10)
--   Engine:          Central wins all 3 months, including a standout August ($9,433.48)
--   Frame & Body:    Central (June, Aug), North (July, $6,093.11)
--   Suspension & Traction: North (June, $7,985.17), Central (July, Aug)
--   Electrical System: Central (June, July), North (August, $4,673.99)
--   Miscellaneous:   West (June), Central (July), North (August)
--
-- Takeaway: Central is the dominant wholesale warehouse, topping
-- 13 of 18 product-line/month combinations -- consistent with its
-- overall size (see query 05). North is the strongest challenger,
-- winning 4 combinations, notably outperforming Central on
-- Suspension & Traction in June and Frame & Body in July. West
-- only tops one combination (Miscellaneous, June), reinforcing
-- that it's the smallest and least wholesale-driven of the three.
