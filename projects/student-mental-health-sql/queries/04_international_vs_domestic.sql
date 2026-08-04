-- ============================================================
-- 04. International vs. Domestic Students
-- ============================================================
-- Purpose: the source study claims international students carry
-- higher mental-health risk than the general population. This
-- dataset includes domestic students too, so we can check that
-- claim directly rather than taking it on faith.

SELECT
    inter_dom,
    COUNT(*)              AS n_students,
    ROUND(AVG(todep), 2)  AS average_phq,
    ROUND(AVG(tosc), 2)   AS average_scs,
    ROUND(AVG(toas), 2)   AS average_as
FROM students
WHERE inter_dom IN ('Inter', 'Dom')
GROUP BY inter_dom
ORDER BY inter_dom;

-- Result on this dataset:
--   Dom   (n=67):  avg PHQ 8.61 | avg SCS 37.64 | avg ASISS 62.84
--   Inter (n=201): avg PHQ 8.04 | avg SCS 37.42 | avg ASISS 75.56
--
-- International students score notably higher on acculturative
-- stress (as expected -- domestic students aren't adjusting to a
-- new culture), but their average PHQ-9 depression score is
-- actually *not* higher than domestic students' in this sample --
-- it's marginally lower. This nuances the original study's framing
-- and is worth calling out rather than assuming the headline
-- finding holds exactly in this cut of the data.
