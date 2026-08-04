-- ============================================================
-- 02. Mental Health Scores by Length of Stay
-- ============================================================
-- Purpose: for international students only, compute the average
-- depression (PHQ-9), social connectedness (SCS), and
-- acculturative stress (ASISS) score at each length of stay,
-- to see whether time in Japan tracks with these scores.
--
-- Output: 9 rows (one per distinct `stay` value, 1-10 years),
-- 5 columns: stay, count_int, average_phq, average_scs, average_as

SELECT
    stay,
    COUNT(*)              AS count_int,
    ROUND(AVG(todep), 2)  AS average_phq,
    ROUND(AVG(tosc), 2)   AS average_scs,
    ROUND(AVG(toas), 2)   AS average_as
FROM students
WHERE inter_dom = 'Inter'
GROUP BY stay
ORDER BY stay DESC;
