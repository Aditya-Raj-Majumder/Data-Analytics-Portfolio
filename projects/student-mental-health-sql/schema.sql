-- ============================================================
-- Schema: students
-- Source: International Student Mental Health Survey (2018)
--         Japanese international university
-- ============================================================
-- Only the columns used in this analysis are typed strictly below.
-- The full raw dataset has 50 columns; the rest (coping-mechanism
-- flags, demographics, etc.) are omitted here for brevity but are
-- present in data/students.csv and can be added if needed.

DROP TABLE IF EXISTS students;

CREATE TABLE students (
    inter_dom       VARCHAR(10),   -- 'Inter' = international, 'Dom' = domestic
    region          VARCHAR(10),   -- region of origin (international students only)
    gender          VARCHAR(10),
    academic        VARCHAR(10),   -- 'Grad' or 'Under'
    age             INT,
    age_cate        INT,           -- binned age category
    stay            INT,           -- length of stay in Japan, in years
    stay_cate       VARCHAR(10),   -- 'Short' / 'Medium' / 'Long'
    japanese        INT,           -- Japanese proficiency, raw score
    japanese_cate   VARCHAR(10),
    english         INT,           -- English proficiency, raw score
    english_cate    VARCHAR(10),
    todep           INT,           -- PHQ-9 total depression score
    depsev          VARCHAR(10),   -- depression severity bucket
    tosc            INT,           -- SCS total social connectedness score
    toas            INT,           -- ASISS total acculturative stress score
    suicide         VARCHAR(5)     -- self-reported suicidal ideation (Yes/No)
);

-- Load data (adjust for your environment):
-- PostgreSQL:
--   \copy students FROM 'data/students.csv' WITH (FORMAT csv, HEADER true);
