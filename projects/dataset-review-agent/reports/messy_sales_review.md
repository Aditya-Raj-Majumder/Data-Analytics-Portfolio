# Dataset review — `messy_sales.csv`

*Generated 09 August 2026, 21:38. This is a starting point, not a verdict — every finding below should be checked against what you know about where the data came from.*

## At a glance

| | |
|---|---|
| Rows | 922 |
| Columns | 15 |
| Memory | 0.69 MB |
| Empty cells | 2,047 of 13,830 (14.8%) |
| Duplicate rows | 22 (2.39%) |
| Issues found | 9 high · 7 medium · 8 low |

## Where to start

Work through these in order — each one affects the results of the next.

1. Convert placeholder text to real nulls first. Every count you run before this will be wrong in a way that does not announce itself.
2. Fix the dtypes next. Numbers and dates trapped as text cannot be aggregated or filtered correctly.
3. Normalise text categories before any groupby, or your category totals will be split across spelling variants.
4. Establish the true row key before joining anything to this dataset.
5. Decide what to do about the exact duplicate rows — they affect every total in the dataset.
6. Once the above are done, the columns in the best shape to analyse first are: `order_date`, `Revenue`, `Discount`, `Quantity`, `Customer Age`.

## Columns

| # | Column | Stored as | Reads as | Missing | Distinct | Notes |
|---:|---|---|---|---:|---:|---|
| 0 | `Order ID` | str | identifier | 0.0% | 882 | High: 1 issue(s) |
| 1 | `order_date` | str | datetime | 0.0% | 401 | High: 2 issue(s) |
| 2 | `City` | str | categorical | 4.77% | 12 | High: 2 issue(s) |
| 3 | `Revenue` | str | numeric | 2.71% | 873 | High: 2 issue(s) |
| 4 | `Discount` | str | numeric | 0.0% | 327 | High: 1 issue(s) |
| 5 | `Quantity` | float64 | numeric | 0.0% | 13 | High: 4 issue(s) |
| 6 | `Customer Age` | float64 | numeric | 14.53% | 67 | Medium: 3 issue(s) |
| 7 | `Is Member` | str | boolean | 0.0% | 2 | Low: 1 issue(s) |
| 8 | `Channel` | str | categorical | 0.0% | 3 |  |
| 9 | `Sales Channel` | str | categorical | 0.0% | 3 |  |
| 10 | `Currency` | str | constant | 0.0% | 1 | Low: 1 issue(s) |
| 11 | `Sales Rep` | str | categorical | 0.0% | 5 | Medium: 1 issue(s) |
| 12 | `Email` | str | identifier | 0.0% | 900 | High: 1 issue(s) |
| 13 | `Notes` | float64 | empty | 100.0% | 0 | Medium: 1 issue(s) |
| 14 | `Unnamed: 14` | float64 | empty | 100.0% | 0 | Medium: 1 issue(s) |

## Findings

### High (9)

**22 exactly duplicated rows** · _Decide_

22 rows (2.39%) are identical to another row across every column.

*Why it matters:* Every count, sum and average is inflated by these rows. If they reached you through a join, the duplication may be multiplicative rather than additive.

*What to do:* Decide whether these are genuine repeated events (two identical orders in the same second is possible but unusual) or an export artefact. Check whether the source system has a row identifier that would distinguish them before dropping anything.

```python
df[df.duplicated(keep=False)].sort_values(list(df.columns))
```

**`City` uses placeholder text for missing values** · _Fix_

44 values are placeholders rather than real data: `-`, `unknown`. Pandas does not read these as null.

*Why it matters:* These count as a legitimate category in any groupby or value_counts, and they will not be caught by `.isna()`. A 'top city' analysis could return 'unknown' as a real answer.

*What to do:* Convert them to proper nulls before doing anything else.

```python
df['City'] = df['City'].replace(['-', 'unknown'], pd.NA)
```

**`City` has inconsistent capitalisation or spacing** · _Fix_

12 distinct values collapse to 5 once case and whitespace are normalised — 7 are duplicates in different clothing.

*Why it matters:* Any groupby, join or value_counts splits these across variants. A city with 300 orders can appear as three cities with 100 each, and nothing in the output tells you it happened.

*What to do:* Normalise before aggregating. Be careful with `.title()` on proper nouns — it breaks names like `McAllen` and `O'Brien`.

```python
df['City'] = df['City'].str.strip().str.lower()
```

**`Discount` holds numbers stored as text** · _Fix_

100.0% of values parse as numbers once currency symbols, commas and percent signs are stripped. Examples: `5.5%`, `17.8%`, `34.0%`.

*Why it matters:* Arithmetic, sorting and aggregation all behave wrongly on text. Sorting puts `$9.00` after `$10.00`, and `.mean()` fails outright.

*What to do:* Strip the symbols and convert to a numeric dtype.

```python
df['Discount'] = pd.to_numeric(
    df['Discount'].astype(str).str.replace(r'[$£€₹,%\s]', '', regex=True),
    errors='coerce')
```

**`Email` looks like an identifier but is not unique** · _Decide_

900 distinct values across 922 rows — 22 rows share an identifier with another row.

*Why it matters:* If you join on this column, matching rows multiply: a value appearing twice on each side produces four rows. This is the single most common cause of silently inflated totals.

*What to do:* Establish what actually makes a row unique before joining. It may be this column combined with a date or a line number.

```python
df['Email'].value_counts().loc[lambda s: s > 1].head(20)
```

**`Order ID` looks like an identifier but is not unique** · _Decide_

882 distinct values across 922 rows — 40 rows share an identifier with another row.

*Why it matters:* If you join on this column, matching rows multiply: a value appearing twice on each side produces four rows. This is the single most common cause of silently inflated totals.

*What to do:* Establish what actually makes a row unique before joining. It may be this column combined with a date or a line number.

```python
df['Order ID'].value_counts().loc[lambda s: s > 1].head(20)
```

**`Quantity` contains negative values** · _Decide_

10 values are below zero, with a minimum of -1.00. The column name suggests it should not be negative.

*Why it matters:* Sums and averages are pulled down by values that may not be real measurements at all.

*What to do:* These are often codes rather than quantities — `-1` standing for 'unknown', or a negative amount marking a return or refund. Find out which before aggregating, and separate them if they are a different kind of event.

```python
df[df['Quantity'] < 0].head(20)
```

**`Revenue` holds numbers stored as text** · _Fix_

100.0% of values parse as numbers once currency symbols, commas and percent signs are stripped. Examples: `$1,836.47`, `$2,406.41`, `$1,119.91`.

*Why it matters:* Arithmetic, sorting and aggregation all behave wrongly on text. Sorting puts `$9.00` after `$10.00`, and `.mean()` fails outright.

*What to do:* Strip the symbols and convert to a numeric dtype.

```python
df['Revenue'] = pd.to_numeric(
    df['Revenue'].astype(str).str.replace(r'[$£€₹,%\s]', '', regex=True),
    errors='coerce')
```

**`order_date` holds dates stored as text** · _Fix_

100.0% of values parse as dates. Examples: `2026-01-28`, `2025-05-26`, `2025-08-05`.

*Why it matters:* You cannot filter by range, resample, or extract month and weekday from text. Mixed formats in the same column are also a real risk here — `03/04/2025` is ambiguous between April 3rd and March 4th.

*What to do:* Convert to datetime, and check the day/month order against a value you can verify independently before trusting it.

```python
df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
```


### Medium (7)

**Columns holding identical data** · _Fix_

These column pairs contain exactly the same values: `Channel` = `Sales Channel`.

*Why it matters:* Redundant columns waste memory and, more importantly, will inflate any correlation matrix or feature-importance ranking you build.

*What to do:* Keep one of each pair and drop the other.

```python
df = df.drop(columns=['Sales Channel'])
```

**`Customer Age` may use sentinel values for missing data** · _Decide_

`0` (5 times), `217` (3 times) — each sits outside the normal range (30.00 to 47.00 covers the middle half of the data) yet repeats often. Genuine extreme measurements usually appear once or twice, not dozens of times.

*Why it matters:* If these are codes rather than measurements, every average, sum and total computed from this column is wrong. A handful of 999s in a column that otherwise tops out at 12 will dominate the mean without any warning.

*What to do:* Check what these values mean in the source system. Common conventions are -1 or 999 for 'unknown', 0 for 'not recorded', and negative amounts marking returns. If they are codes, convert them to nulls before aggregating; if they mark a different kind of event, separate those rows out.

```python
df['Customer Age'].value_counts().head(15)
# then, once confirmed:
df['Customer Age'] = df['Customer Age'].replace([0.0, 217.0], pd.NA)
```

**`Notes` is completely empty** · _Fix_

Every value in this column is missing.

*Why it matters:* It carries no information and cannot be used for anything.

*What to do:* Drop it, after checking the source system was supposed to populate it.

```python
df = df.drop(columns=['Notes'])
```

**`Quantity` may use sentinel values for missing data** · _Decide_

`999` (14 times), `-1` (10 times) — each sits outside the normal range (3.00 to 9.00 covers the middle half of the data) yet repeats often. Genuine extreme measurements usually appear once or twice, not dozens of times.

*Why it matters:* If these are codes rather than measurements, every average, sum and total computed from this column is wrong. A handful of 999s in a column that otherwise tops out at 12 will dominate the mean without any warning.

*What to do:* Check what these values mean in the source system. Common conventions are -1 or 999 for 'unknown', 0 for 'not recorded', and negative amounts marking returns. If they are codes, convert them to nulls before aggregating; if they mark a different kind of event, separate those rows out.

```python
df['Quantity'].value_counts().head(15)
# then, once confirmed:
df['Quantity'] = df['Quantity'].replace([999.0, -1.0], pd.NA)
```

**`Sales Rep` has leading or trailing whitespace** · _Fix_

574 values have spaces at the start or end.

*Why it matters:* Joins and equality filters fail silently on these — `'Delhi ' != 'Delhi'`.

*What to do:* Strip whitespace.

```python
df['Sales Rep'] = df['Sales Rep'].str.strip()
```

**`Unnamed: 14` is completely empty** · _Fix_

Every value in this column is missing.

*Why it matters:* It carries no information and cannot be used for anything.

*What to do:* Drop it, after checking the source system was supposed to populate it.

```python
df = df.drop(columns=['Unnamed: 14'])
```

**`order_date` contains dates in the future** · _Decide_

6 values are later than today.

*Why it matters:* Future dates in a historical dataset usually mean a typo in the year, a placeholder, or a genuinely scheduled record mixed with completed ones.

*What to do:* Inspect them; decide whether they belong in this analysis at all.

```python
df[df['order_date'] > pd.Timestamp.now()]
```


### Low (8)

**Unnamed columns** · _Fix_

1 column(s) have no header: `Unnamed: 14`.

*Why it matters:* Usually a trailing comma or a stray column in the source export. Harmless, but they clutter every subsequent operation.

*What to do:* Drop them after confirming they hold nothing you need.

```python
df = df.loc[:, ~df.columns.str.match(r'^(Unnamed|\s*$)')]
```

**`Currency` holds a single value** · _Fix_

Every one of the 922 non-null rows is `INR`.

*Why it matters:* It has zero variance, so it cannot explain anything or serve as a grouping key. It may still be worth keeping as documentation of scope.

*What to do:* Note the value as a property of the dataset, then drop the column.

```python
df = df.drop(columns=['Currency'])
```

**`Customer Age` is 14.53% missing** · _Decide_

134 of 922 rows have no value.

*Why it matters:* Dropping these rows shrinks your sample; filling them invents data. Which is worse depends entirely on *why* they are missing.

*What to do:* Ask whether the missingness is random. If the people who skipped this field differ systematically from those who did not — high earners declining to state income, say — then both dropping and mean-filling will bias your results, in opposite directions. Check whether the nulls cluster by date, source, or another column.

```python
df[df['Customer Age'].isna()].describe(include='all')
```

**`Customer Age` has values outside the usual range** · _Decide_

The middle 50% sits between 30.00 and 47.00, but the full range runs 0.00 to 217.00.

*Why it matters:* These may be genuine extremes, data entry errors, or a different kind of record mixed into the same column.

*What to do:* Look at them individually before deciding. Outliers are often the most interesting rows in the dataset, not the least — removing them by rule is rarely the right first move.

```python
q1, q3 = df['Customer Age'].quantile([.25, .75])
iqr = q3 - q1
df[(df['Customer Age'] < q1 - 1.5*iqr) | (df['Customer Age'] > q3 + 1.5*iqr)]
```

**`Is Member` is a yes/no field stored as text** · _Fix_

Only two distinct values: `No`, `Yes`.

*Why it matters:* Boolean dtype is smaller and works directly with `.sum()` and filters.

*What to do:* Map to True/False.

```python
df['Is Member'] = df['Is Member'].str.strip().str.lower().map({'yes': True, 'no': False, 'y': True, 'n': False, 'true': True, 'false': False})
```

**`Quantity` is heavily right-skewed** · _Decide_

Skew is 7.9, and the mean (20.98) sits above the median (6.00) by 14.98 — around 250% of the interquartile spread.

*Why it matters:* A long tail is pulling the mean away from the typical row, so the average describes the tail more than the bulk of the data. Any method assuming normality will also be poorly calibrated.

*What to do:* Report the median alongside the mean, and consider a log scale for charts. Check first whether the tail is genuine or the result of a few bad values.

**`Quantity` has values outside the usual range** · _Decide_

The middle 50% sits between 3.00 and 9.00, but the full range runs -1.00 to 999.00.

*Why it matters:* These may be genuine extremes, data entry errors, or a different kind of record mixed into the same column.

*What to do:* Look at them individually before deciding. Outliers are often the most interesting rows in the dataset, not the least — removing them by rule is rarely the right first move.

```python
q1, q3 = df['Quantity'].quantile([.25, .75])
iqr = q3 - q1
df[(df['Quantity'] < q1 - 1.5*iqr) | (df['Quantity'] > q3 + 1.5*iqr)]
```

**`Revenue` has values outside the usual range** · _Decide_

The middle 50% sits between 646.57 and 1,332.51, but the full range runs 90.92 to 2,905.26.

*Why it matters:* These may be genuine extremes, data entry errors, or a different kind of record mixed into the same column.

*What to do:* Look at them individually before deciding. Outliers are often the most interesting rows in the dataset, not the least — removing them by rule is rarely the right first move.

```python
q1, q3 = df['Revenue'].quantile([.25, .75])
iqr = q3 - q1
df[(df['Revenue'] < q1 - 1.5*iqr) | (df['Revenue'] > q3 + 1.5*iqr)]
```


## Numeric summary

| Column | Mean | Median | Std | Min | Q1 | Q3 | Max | Zeros | Negatives |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `Revenue` | 1e+03 | 990.24 | 518.67 | 90.92 | 646.57 | 1.3e+03 | 2.9e+03 | 0 | 0 |
| `Discount` | 17.25 | 17.20 | 10.02 | 0.10 | 8.50 | 25.90 | 35.00 | 0 | 0 |
| `Quantity` | 20.98 | 6.00 | 121.55 | -1.00 | 3.00 | 9.00 | 999.00 | 0 | 10 |
| `Customer Age` | 39.07 | 39.00 | 16.78 | 0.00 | 30.00 | 47.00 | 217.00 | 5 | 0 |

## Category breakdown

- **City** — `Bengaluru` (148), `Mumbai` (121), `Delhi` (120), `Chennai` (112), `Kolkata` (84), `mumbai` (65) … and 6 more
- **Channel** — `Online` (530), `Store` (309), `Partner` (83)
- **Sales Channel** — `Online` (530), `Store` (309), `Partner` (83)
- **Sales Rep** — `R. Iyer ` (207), `P. Nair ` (201), `A. Sharma` (192), `  M. Khan` (166), `S. Bose` (156)

---

*What this report does not know: what the data is for, how it was collected, or which of these columns matters to your question. It flags patterns that are usually problems — confirming whether they are problems here is your job.*