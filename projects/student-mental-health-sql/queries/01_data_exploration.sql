-- ============================================================
-- 01. Data Exploration & Quality Checks
-- ============================================================
-- Purpose: understand the shape of the data and catch issues
-- (nulls, unexpected categories, outliers) before trusting any
-- aggregate result built on top of it.

-- 1a. Row count and student-type breakdown
SELECT
    inter_dom,
    COUNT(*) AS n_students
FROM students
GROUP BY inter_dom
ORDER BY n_students DESC;

-- 1b. Check for NULL / unlabeled inter_dom rows
-- (these should be excluded from any inter_dom-based analysis;
-- the raw source file originally had 18 stray/blank rows appended
-- after the real respondents, which have been removed from
-- data/students.csv -- this check should now return 0)
SELECT COUNT(*) AS n_unlabeled
FROM students
WHERE inter_dom IS NULL;

-- 1c. Range check on the three score columns
-- PHQ-9 (todep) should run 0-27, SCS (tosc) 8-48, ASISS (toas) 36-180
SELECT
    MIN(todep) AS min_phq, MAX(todep) AS max_phq,
    MIN(tosc)  AS min_scs, MAX(tosc)  AS max_scs,
    MIN(toas)  AS min_as,  MAX(toas)  AS max_as
FROM students
WHERE inter_dom = 'Inter';

-- 1d. Distribution of length of stay among international students
-- (flags how thin the sample gets at longer stays)
SELECT
    stay,
    COUNT(*) AS n_students
FROM students
WHERE inter_dom = 'Inter'
GROUP BY stay
ORDER BY stay;
