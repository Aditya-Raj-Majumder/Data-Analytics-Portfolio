-- ============================================================
-- 08. Payment Method Mix and Processing Fee Cost
-- ============================================================
-- Purpose: quantify how much revenue is lost to payment processing
-- fees, broken down by payment method. Useful for a cost-reduction
-- angle the board didn't explicitly ask for, but that falls out
-- naturally from the same data.

SELECT
    payment,
    COUNT(*)                                                          AS n_orders,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sales), 1)         AS pct_of_orders,
    ROUND(AVG(payment_fee) * 100, 2)                                  AS avg_fee_pct,
    ROUND(SUM(total * payment_fee), 2)                                AS total_fees_paid
FROM sales
GROUP BY payment
ORDER BY total_fees_paid DESC;

-- Result:
--   Credit card: 659 orders (65.9%) -- flat 3.0% fee -> $3,308.15 total fees
--   Transfer:    225 orders (22.5%) -- flat 1.0% fee -> $1,596.42 total fees
--   Cash:        116 orders (11.6%) -- 0% fee        -> $0.00 total fees
--
--   Combined fee cost across all 1,000 orders: $4,904.57
--   (roughly 1.7% of total gross revenue of $289,113.00)
--
-- Takeaway: fees are a modest but real drag on revenue (~1.7%), but
-- they're concentrated almost entirely in credit card transactions,
-- which also make up nearly two-thirds of all orders.
--
-- NOTE: see query 09 before assuming payment method is a lever you
-- can just switch. It turns out payment method is fully determined
-- by client_type in this dataset (100% of wholesale pays by
-- Transfer, 100% of retail pays by Credit Card or Cash) -- so the
-- "shift orders to a cheaper method" idea only makes sense for
-- retail's credit-card share, not wholesale.
