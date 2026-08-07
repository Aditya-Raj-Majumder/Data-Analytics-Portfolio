-- ============================================================
-- 09. Payment Method by Client Type -- Is Payment Choice Random?
-- ============================================================
-- Purpose: query 08 flagged credit card fees as a possible cost
-- lever. Before recommending anything, check whether payment
-- method is actually a free choice per order, or whether it's
-- structurally tied to something else -- like client type.

SELECT
    client_type,
    payment,
    COUNT(*)                                                                      AS n_orders,
    ROUND(100.0 * COUNT(*)
          / SUM(COUNT(*)) OVER (PARTITION BY client_type), 1)                     AS pct_within_client_type,
    ROUND(SUM(total * payment_fee), 2)                                            AS fees_paid
FROM sales
GROUP BY client_type, payment
ORDER BY client_type, fees_paid DESC;

-- Result:
--   Wholesale -> Transfer:     225 orders (100.0% of wholesale)  -> $1,596.42 fees
--   Retail    -> Credit card:  659 orders ( 85.0% of retail)     -> $3,308.15 fees
--   Retail    -> Cash:         116 orders ( 15.0% of retail)     -> $0.00 fees
--
-- Takeaway -- THIS CORRECTS QUERY 08's IMPLICATION:
-- Payment method isn't a free per-order choice in this dataset --
-- it's fully determined by client_type. Every single wholesale
-- order pays by Transfer (1% fee); every single retail order pays
-- by either Credit Card or Cash, and NEVER by Transfer. There is
-- no overlap in either direction.
--
-- This means the "shift wholesale orders to a cheaper payment
-- method" idea floated in query 08 isn't a real opportunity --
-- wholesale is already on the cheaper of the two non-zero fee
-- rates. The entire $3,308.15 in credit card fees sits inside
-- retail, where 85% of orders already default to card. Any fee-
-- reduction push should target retail's credit-card share, not
-- wholesale.
