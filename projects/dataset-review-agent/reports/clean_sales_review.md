# Dataset review — `clean_sales.csv`

*Generated 09 August 2026, 21:38. This is a starting point, not a verdict — every finding below should be checked against what you know about where the data came from.*

## At a glance

| | |
|---|---|
| Rows | 500 |
| Columns | 6 |
| Memory | 0.16 MB |
| Empty cells | 0 of 3,000 (0.0%) |
| Duplicate rows | 0 (0.0%) |
| Issues found | 1 high · 0 medium · 0 low |

## Where to start

Work through these in order — each one affects the results of the next.

1. Fix the dtypes next. Numbers and dates trapped as text cannot be aggregated or filtered correctly.
2. Once the above are done, the columns in the best shape to analyse first are: `date`, `units`, `unit_price`.

## Columns

| # | Column | Stored as | Reads as | Missing | Distinct | Notes |
|---:|---|---|---|---:|---:|---|
| 0 | `transaction_id` | str | identifier | 0.0% | 500 |  |
| 1 | `date` | str | datetime | 0.0% | 21 | High: 1 issue(s) |
| 2 | `product` | str | categorical | 0.0% | 3 |  |
| 3 | `units` | int64 | numeric | 0.0% | 19 |  |
| 4 | `unit_price` | float64 | numeric | 0.0% | 476 |  |
| 5 | `in_stock` | bool | boolean | 0.0% | 2 |  |

## Findings

### High (1)

**`date` holds dates stored as text** · _Fix_

100.0% of values parse as dates. Examples: `2025-01-01`, `2025-01-01`, `2025-01-01`.

*Why it matters:* You cannot filter by range, resample, or extract month and weekday from text. Mixed formats in the same column are also a real risk here — `03/04/2025` is ambiguous between April 3rd and March 4th.

*What to do:* Convert to datetime, and check the day/month order against a value you can verify independently before trusting it.

```python
df['date'] = pd.to_datetime(df['date'], errors='coerce')
```


## Numeric summary

| Column | Mean | Median | Std | Min | Q1 | Q3 | Max | Zeros | Negatives |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `units` | 10.00 | 10.00 | 5.40 | 1.00 | 5.00 | 15.00 | 19.00 | 0 | 0 |
| `unit_price` | 27.95 | 27.80 | 12.79 | 5.08 | 16.25 | 39.20 | 49.84 | 0 | 0 |

## Category breakdown

- **product** — `Doohickey` (169), `Widget` (167), `Gadget` (164)

---

*What this report does not know: what the data is for, how it was collected, or which of these columns matters to your question. It flags patterns that are usually problems — confirming whether they are problems here is your job.*