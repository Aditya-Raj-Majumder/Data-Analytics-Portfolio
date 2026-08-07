-- ============================================================
-- 10. Does Wholesale Get a Bulk Discount? (Unit Price Comparison)
-- ============================================================
-- Purpose: wholesale orders are ~4x larger by quantity than retail
-- (see query 02). The natural assumption is that bulk buyers get a
-- lower per-unit price. This checks whether that's actually true
-- in the pricing data, product line by product line.

SELECT
    product_line,
    client_type,
    ROUND(AVG(unit_price), 2)  AS avg_unit_price,
    ROUND(AVG(quantity), 1)    AS avg_quantity_per_order,
    COUNT(*)                   AS n_orders
FROM sales
GROUP BY product_line, client_type
ORDER BY product_line, client_type;

-- Result (avg_unit_price, Retail vs Wholesale):
--   Braking system:          $17.60 vs $18.19   (wholesale +3.4%)
--   Electrical system:       $25.50 vs $25.93   (wholesale +1.7%)
--   Engine:                  $59.87 vs $60.92   (wholesale +1.8%)
--   Frame & body:            $42.81 vs $42.91   (wholesale +0.2%)
--   Miscellaneous:           $22.54 vs $23.65   (wholesale +4.9%)
--   Suspension & traction:   $33.98 vs $33.94   (wholesale -0.1%, negligible)
--
--   Meanwhile avg_quantity_per_order is consistently ~4x higher
--   for wholesale across every product line (~22-27 units vs ~5-6).
--
-- Takeaway: there is NO bulk discount anywhere in this dataset --
-- if anything, wholesale pays a slightly HIGHER average unit price
-- than retail in 5 of 6 product lines (the 6th is a rounding-level
-- wash). Wholesale's revenue advantage comes entirely from buying
-- roughly 4x the quantity per order, not from a better per-unit
-- rate. Whether that's an intentional pricing decision or a gap
-- worth revisiting (bulk buyers are often given a discount to lock
-- in loyalty) is a question for the pricing team, not something
-- the data resolves on its own -- but it's a finding worth raising.
