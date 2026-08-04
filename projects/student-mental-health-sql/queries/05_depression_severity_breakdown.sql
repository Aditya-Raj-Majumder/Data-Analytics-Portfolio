-- ============================================================
-- 05. Depression Severity Breakdown
-- ============================================================
-- Purpose: averages can hide risk concentrated in a subgroup.
-- This breaks international students into PHQ-9 severity bands
-- and shows what share falls into moderate-to-severe territory,
-- which is arguably more actionable for a university counseling
-- office than a single average score.

SELECT
    depsev,
    COUNT(*) AS n_students,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_international
FROM students
WHERE inter_dom = 'Inter'
GROUP BY depsev
ORDER BY
    CASE depsev
        WHEN 'Min'    THEN 1
        WHEN 'Mild'   THEN 2
        WHEN 'Mod'    THEN 3
        WHEN 'ModSev' THEN 4
        WHEN 'Sev'    THEN 5
    END;

-- Result on this dataset (n=201 international students):
--   Min (minimal)      : 51 students (25.4%)
--   Mild               : 81 students (40.3%)
--   Mod (moderate)     : 53 students (26.4%)
--   ModSev             : 11 students ( 5.5%)
--   Sev (severe)       :  5 students ( 2.5%)
--
-- About 1 in 3 international students falls into moderate-or-worse
-- depression territory -- a more concrete, actionable number than
-- an average PHQ-9 score alone.
