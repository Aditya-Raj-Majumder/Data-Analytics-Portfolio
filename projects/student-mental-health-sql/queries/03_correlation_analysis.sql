-- ============================================================
-- 03. Correlation Analysis
-- ============================================================
-- Purpose: the source study claims social connectedness and
-- acculturative stress are predictive of depression. Grouping by
-- `stay` doesn't test that directly -- this does, using PostgreSQL's
-- built-in CORR() (Pearson correlation coefficient).
--
-- Interpretation guide: CORR() returns a value from -1 to 1.
--   -1  = perfect negative relationship
--    0  = no linear relationship
--   +1  = perfect positive relationship

SELECT
    ROUND(CORR(todep, tosc)::NUMERIC, 3) AS corr_depression_connectedness,
    ROUND(CORR(todep, toas)::NUMERIC, 3) AS corr_depression_stress
FROM students
WHERE inter_dom = 'Inter';

-- Result on this dataset:
--   corr_depression_connectedness ≈ -0.54  (moderate negative)
--   corr_depression_stress        ≈  0.41  (moderate positive)
--
-- Read as: students who feel more socially connected tend to score
-- lower on depression; students under more acculturative stress
-- tend to score higher on depression. Both point in the direction
-- the original study reported, though correlation alone doesn't
-- establish causation.
