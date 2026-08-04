# 🧠 International Students & Mental Health — SQL Analysis

![Illustration of silhouetted heads facing a glowing pathway](assets/mentalhealth.jpg)

A SQL portfolio project analyzing survey data on international student mental
health, exploring whether length of stay abroad relates to depression,
social connectedness, and acculturative stress — and stress-testing the
claims of the original published study against the raw data.

## 📘 Background

In 2018, a Japanese international university surveyed its student body on
mental health and published the results the following year (approved by
several ethical/regulatory boards). The study's headline findings:

1. International students face **higher mental health risk** than the
   general population.
2. **Social connectedness** (feeling part of a social group) and
   **acculturative stress** (stress from adapting to a new culture) are
   **predictive of depression**.

This project uses SQL to independently explore the underlying survey data
and check whether these conclusions hold up — with a particular focus on
whether **length of stay** in the host country is a contributing factor.

## 🎯 Objective

Answer, using SQL alone:

- Does average depression / connectedness / stress shift with how long an
  international student has been in the country?
- Do connectedness and stress actually correlate with depression in this
  data, the way the study claims?
- Do international students really score worse than domestic students?
- How concentrated is depression risk — is it a uniform mild elevation, or
  a subgroup with serious risk?

## 🗂️ Dataset

`data/students.csv` — one row per survey respondent (268 total: 201
international, 67 domestic; 18 stray/blank rows from the raw export
were removed). Key columns used in this analysis:

| Column | Description |
|---|---|
| `inter_dom` | Student type: `Inter` (international) or `Dom` (domestic) |
| `stay` | Length of stay in the host country, in years |
| `todep` | PHQ-9 total depression score (0–27, higher = more symptoms) |
| `tosc` | SCS total social connectedness score (8–48, higher = more connected) |
| `toas` | ASISS total acculturative stress score (36–180, higher = more stress) |
| `depsev` | Depression severity band derived from `todep` (Min/Mild/Mod/ModSev/Sev) |

Full column list and data types are in [`schema.sql`](schema.sql).

**Data source & privacy note:** this is de-identified, publicly available
survey data from the published 2018 study referenced above — no names or
other directly identifying information are included. It's shared here
strictly for portfolio/analysis purposes; if you plan to reuse it, please
check the original study for its licensing and citation terms.

## ⚙️ Tools

PostgreSQL. Every query in `queries/` is standard ANSI SQL plus one
Postgres-specific function (`CORR()`) noted where it's used.

## 📂 Project structure

```
student-mental-health-sql/
├── README.md
├── schema.sql                              -- table definition
├── data/
│   └── students.csv                        -- raw survey data
├── queries/
│   ├── 01_data_exploration.sql             -- sanity checks, nulls, ranges
│   ├── 02_scores_by_length_of_stay.sql     -- core analysis (required deliverable)
│   ├── 03_correlation_analysis.sql         -- tests the study's core claim
│   ├── 04_international_vs_domestic.sql    -- tests the "higher risk" claim
│   └── 05_depression_severity_breakdown.sql -- risk concentration, not just averages
└── results/
    └── scores_by_length_of_stay.csv        -- output of query 02
```

## 📊 Analysis walkthrough

### Step 1 — Explore and validate the data
Before trusting any aggregate, [`01_data_exploration.sql`](queries/01_data_exploration.sql)
checks group sizes, confirms no rows have a null `inter_dom` (18 such stray
rows were present in the original raw export and have been removed from
`data/students.csv`), and confirms the three score columns fall inside
their valid test ranges. It also shows the sample size at each length of
stay — important context, since some `stay` values have only 1–3 students.

### Step 2 — Core analysis: scores by length of stay
[`02_scores_by_length_of_stay.sql`](queries/02_scores_by_length_of_stay.sql)
filters to international students, groups by `stay`, and averages the three
scores at each length of stay.

| stay | count_int | average_phq | average_scs | average_as |
|---|---|---|---|---|
| 10 | 1 | 13.00 | 32.00 | 50.00 |
| 8 | 1 | 10.00 | 44.00 | 65.00 |
| 7 | 1 | 4.00 | 48.00 | 45.00 |
| 6 | 3 | 6.00 | 38.00 | 58.67 |
| 5 | 1 | 0.00 | 34.00 | 91.00 |
| 4 | 14 | 8.57 | 33.93 | 87.71 |
| 3 | 46 | 9.09 | 37.13 | 78.00 |
| 2 | 39 | 8.28 | 37.08 | 77.67 |
| 1 | 95 | 7.48 | 38.11 | 72.80 |

**Reading this carefully:** 95 of 201 international students have only
stayed 1 year, so the well-populated rows are `stay` = 1 through 4.
Within that range, acculturative stress climbs steadily (72.8 → 87.7)
while depression and connectedness stay comparatively flat. The rows for
`stay` ≥ 5 have 1–3 students each and shouldn't be read as trends — one
person can swing those averages by 10+ points.

### Step 3 — Test the study's actual claim: does stress/connectedness predict depression?
Grouping by `stay` doesn't test the study's real claim. [`03_correlation_analysis.sql`](queries/03_correlation_analysis.sql)
computes Pearson correlation directly between depression and the other two
scores:

| Relationship | Correlation |
|---|---|
| Depression ↔ Social connectedness | **−0.54** (moderate negative) |
| Depression ↔ Acculturative stress | **+0.41** (moderate positive) |

This supports the study's claim directionally: less-connected and
more-stressed students do tend to score higher on depression in this
sample. (Note: correlation, not causation — and PHQ-9/SCS/ASISS share some
survey-method overlap that could inflate the relationship somewhat.)

### Step 4 — Check the "higher risk than general population" claim
[`04_international_vs_domestic.sql`](queries/04_international_vs_domestic.sql)
compares international and domestic students directly:

| Group | n | avg PHQ-9 | avg SCS | avg ASISS |
|---|---|---|---|---|
| Domestic | 67 | 8.61 | 37.64 | 62.84 |
| International | 201 | 8.04 | 37.42 | 75.56 |

International students score meaningfully higher on acculturative stress
(expected — domestic students aren't adjusting to a new culture), but their
average depression score is not higher than domestic students' — it's
slightly *lower* in this sample. That complicates a literal reading of the
study's headline claim, at least on this cut of the data.

### Step 5 — Look past the average: how concentrated is the risk?
An average can hide a high-risk subgroup. [`05_depression_severity_breakdown.sql`](queries/05_depression_severity_breakdown.sql)
buckets international students into PHQ-9 severity bands:

| Severity | n | % of international students |
|---|---|---|
| Minimal | 51 | 25.4% |
| Mild | 81 | 40.3% |
| Moderate | 53 | 26.4% |
| Moderately severe | 11 | 5.5% |
| Severe | 5 | 2.5% |

About **1 in 3 international students** falls into moderate-or-worse
depression territory — a more concrete, decision-useful number for a
university counseling office than a single average score.

## 🔑 Key takeaways

- **Length of stay and stress**: acculturative stress rises with years in
  the country over the well-populated 1–4 year range; depression doesn't
  show the same clear trend, and the `stay` ≥ 5 rows are too thin to trust.
- **The connectedness/stress → depression link holds up**: moderate
  correlations in the expected directions, consistent with the original
  study.
- **The "international students are worse off" claim is more nuanced than
  the headline**: they carry more acculturative stress, but not more
  depression, than domestic students in this dataset.
- **Risk is concentrated, not diffuse**: roughly a third of international
  students land in moderate-to-severe depression territory, which matters
  more for intervention planning than the average score alone.

## ▶️ How to reproduce

```bash
# 1. Create the table
psql -d your_database -f schema.sql

# 2. Load the data
psql -d your_database -c "\copy students FROM 'data/students.csv' WITH (FORMAT csv, HEADER true)"

# 3. Run any analysis query
psql -d your_database -f queries/02_scores_by_length_of_stay.sql
```

## ⚠️ Caveats

- Several `stay` values have very small sample sizes (n=1–3); those rows
  are directional at best, not statistically reliable.
- Correlation ≠ causation — Step 3's results describe association, not a
  causal mechanism.
- All scores are self-reported survey instruments (PHQ-9, SCS, ASISS),
  which carry the usual self-report biases.

---

**Author:** Aditya Raj Majumder  
🎓 Junior Data Analyst  
🔗 [LinkedIn](https://www.linkedin.com/in/aditya-raj-majumder-600533250/) | [GitHub](https://github.com/Aditya-Raj-Majumder)

