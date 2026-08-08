# 🏍️ Motorcycle Parts Wholesale — SQL Revenue Analysis

![Illustration of a motorcycle V-twin engine beside gears and analytics charts](assets/motorcycle-parts-banner.png)

A SQL portfolio project analyzing three months of order data from a motorcycle
parts retailer, digging into where revenue actually comes from — by client
type, product line, warehouse, and month — and where a few dollars are
quietly being lost to payment processing fees.

## 📘 Background

The company operates three warehouses (**North**, **Central**, **West**) and
sells to two kinds of customers: **Retail** and **Wholesale**. Customers pay
by credit card, bank transfer, or cash, and each method carries a different
processing fee. Over June–August 2021, the business generated 1,000 orders
worth just over **$289,000** in gross revenue.

The board of directors asked a specific question: *how does wholesale
revenue break down by product line, month, and warehouse?* That request is
the anchor for this project — but rather than stopping at a single query, I
used it as a starting point to explore the dataset more broadly, the way an
analyst actually would once they're already inside the data: is wholesale
even the right thing to focus on? Which warehouse is carrying the business?
Are fees costing more than they should?

## 🎯 Objective

1. Answer the board's original question: **net wholesale revenue by product
   line, month, and warehouse.**
2. Go further and independently verify *why* wholesale deserves attention —
   don't just assume the premise, and be willing to revisit an earlier
   finding (query 08 → 09) once new evidence complicates it.
3. Surface secondary findings (warehouse performance, product line mix,
   payment fee cost) that a stakeholder would want next, even though they
   weren't explicitly requested.
4. Demonstrate a range of SQL techniques: filtering, `CASE` logic,
   aggregation, CTEs, and window functions (`RANK()`, `LAG()`) — not just a
   single `GROUP BY`.

## 🗂️ Dataset

**Source:** [`data/motorcycle_parts_sales.csv`](data/motorcycle_parts_sales.csv)
— 1,000 orders, June 1 – August 28, 2021, no missing values.

| Column | Type | Description |
|---|---|---|
| `order_number` | `VARCHAR` | Unique order identifier |
| `date` | `DATE` | Order date |
| `warehouse` | `VARCHAR` | `North`, `Central`, or `West` |
| `client_type` | `VARCHAR` | `Retail` or `Wholesale` |
| `product_line` | `VARCHAR` | One of 6 part categories (Braking System, Engine, etc.) |
| `quantity` | `INT` | Units ordered |
| `unit_price` | `FLOAT` | Price per unit ($) |
| `total` | `FLOAT` | Gross order value ($) |
| `payment` | `VARCHAR` | `Credit card`, `Transfer`, or `Cash` |
| `payment_fee` | `FLOAT` | Fee **rate** charged on this payment method (e.g. `0.03` = 3%) |

Full schema with constraints: [`schema/schema.sql`](schema/schema.sql).

**Important nuance:** `payment_fee` is a *rate*, not a dollar amount. The
dollar cost of a fee on any order is `total * payment_fee`. This has to be
computed **per row before aggregating** — summing raw fee rates across
orders (`SUM(payment_fee)`) produces a meaningless number, since it adds up
percentages that apply to different base amounts. Every net-revenue query
in this project applies the fee row-by-row first.

## ⚙️ Tools

- **SQL** (PostgreSQL-flavored — `EXTRACT()`, `CASE`, window functions,
  `::numeric` casting)
- Developed and validated in a DataCamp Workspace / SQLite environment

## 📂 Project Structure

```
motorcycle-parts-wholesale-sql-analysis/
├── README.md
├── schema/
│   └── schema.sql                  -- table definition + column notes
├── data/
│   └── motorcycle_parts_sales.csv  -- source dataset (1,000 rows)
├── queries/
│   ├── 01_data_overview.sql
│   ├── 02_retail_vs_wholesale_split.sql
│   ├── 03_monthly_revenue_trend.sql
│   ├── 04_wholesale_revenue_by_product_month_warehouse.sql   -- ★ board deliverable
│   ├── 05_warehouse_performance.sql
│   ├── 06_product_line_performance.sql
│   ├── 07_top_wholesale_combinations.sql
│   ├── 08_payment_method_fee_analysis.sql
│   ├── 09_payment_method_by_client_type.sql   -- ★ corrects 08
│   ├── 10_bulk_pricing_check.sql
│   ├── 11_revenue_concentration.sql
│   └── 12_july_dip_investigation.sql          -- ★ closes the loop on 03
└── results/
    └── *.csv                        -- full output of each query
```

## 📊 Analysis Walkthrough

### 01 · Data Overview
Sanity-checked row count, date coverage, and distinct categorical values
before trusting anything downstream. **1,000 orders**, June 1–Aug 28 2021,
6 product lines, 3 warehouses, 3 payment methods, no nulls.

### 02 · Retail vs. Wholesale Split
Before narrowing in on wholesale, I checked whether it actually deserved
the board's attention.

| client_type | n_orders | % of orders | gross_revenue | % of revenue | avg_order_value |
|---|---|---|---|---|---|
| Wholesale | 225 | 22.5% | $159,642.33 | **55.2%** | $709.52 |
| Retail | 775 | 77.5% | $129,470.67 | 44.8% | $167.06 |

**Wholesale is under a quarter of all orders but drives more than half of
gross revenue** — orders average roughly 4.2x larger than retail. This
confirms the board's focus is well-placed.

### 03 · Monthly Revenue Trend
Overall net revenue by month, with month-over-month change via `LAG()`:

| month | net_revenue | change_vs_prev_month | pct_change |
|---|---|---|---|
| June | $93,659.04 | — | — |
| July | $91,895.85 | -$1,763.19 | -1.9% |
| August | $98,653.53 | +$6,757.68 | **+7.4%** |

Revenue dipped slightly in July before a strong August recovery — see
query 12 for what actually drove the dip.

### 04 · ★ Wholesale Net Revenue by Product Line, Month, Warehouse
The board's original request. Filters to `Wholesale` orders, converts the
month to a name, and computes net revenue as
`SUM(total * (1 - payment_fee))` — applying the fee rate per row before
summing. Returns 48 rows (not every product line has orders in every
warehouse/month combination). Full output:
[`results/04_wholesale_revenue_by_product_month_warehouse.csv`](results/04_wholesale_revenue_by_product_month_warehouse.csv).

### 05 · Warehouse Performance
| warehouse | n_orders | gross_revenue | avg_order_value | % wholesale |
|---|---|---|---|---|
| Central | 480 | $141,982.88 | $295.80 | 55.5% |
| North | 340 | $100,203.63 | $294.72 | 57.9% |
| West | 180 | $46,926.49 | $260.70 | 48.4% |

Central is the largest warehouse by a wide margin — roughly **3x West's
revenue**. North has the highest wholesale mix; West leans more retail and
is the smallest of the three by every measure.

### 06 · Product Line Performance
| product_line | n_orders | gross_revenue | avg_order_value | units_sold |
|---|---|---|---|---|
| Suspension & traction | 228 | $73,014.21 | $320.24 | 2,145 |
| Frame & body | 166 | $69,024.73 | $415.81 | 1,619 |
| Electrical system | 193 | $43,612.71 | $225.97 | 1,698 |
| Braking system | 230 | $38,350.15 | $166.74 | 2,130 |
| Engine | 61 | $37,945.38 | **$622.06** | 627 |
| Miscellaneous | 122 | $27,165.82 | $222.67 | 1,176 |

**Engine** has the fewest orders of any line but by far the highest average
order value — a low-volume, high-ticket category. **Braking System** is the
opposite: most-ordered line in the dataset, but lowest AOV, landing it only
4th in total revenue.

### 07 · Best-Performing Warehouse per Product Line per Month
A CTE + `RANK()` window function picks the top warehouse for every
product-line/month combination, turning the 48-row breakdown from query 04
into a direct answer.

**Central wins 13 of 18 combinations** — consistent with it being the
largest warehouse overall. **North** is the strongest challenger, winning 4,
including beating Central on Suspension & Traction in June and Frame & Body
in July. **West** only tops one combination (Miscellaneous, June).

### 08 · Payment Method Fee Analysis
| payment | n_orders | % of orders | avg_fee_pct | total_fees_paid |
|---|---|---|---|---|
| Credit card | 659 | 65.9% | 3.0% | $3,308.15 |
| Transfer | 225 | 22.5% | 1.0% | $1,596.42 |
| Cash | 116 | 11.6% | 0.0% | $0.00 |

Combined fee cost across all orders: **$4,904.57**, about **1.7% of gross
revenue**. Fees are concentrated almost entirely in credit card
transactions, which also make up nearly two-thirds of all orders — a
possible cost-reduction lever worth checking further (see query 09).

### 09 · ★ Payment Method by Client Type — Is Payment Choice Random?
Before recommending anything from query 08, I checked whether payment
method is actually a free choice per order.

| client_type | payment | % within client_type | fees_paid |
|---|---|---|---|
| Wholesale | Transfer | **100.0%** | $1,596.42 |
| Retail | Credit card | 85.0% | $3,308.15 |
| Retail | Cash | 15.0% | $0.00 |

**This corrects query 08's implication.** Payment method isn't a free
choice — it's fully determined by `client_type`. Every wholesale order pays
by Transfer; every retail order pays by Credit Card or Cash; there is zero
overlap in either direction. Wholesale is *already* on the cheaper of the
two non-zero fee rates. The entire $3,308.15 in credit card fees sits
inside retail — so any fee-reduction push should target retail's
credit-card share, not wholesale as I'd initially framed it.

### 10 · Does Wholesale Get a Bulk Discount?
Wholesale orders average ~4x the quantity of retail orders (query 02). The
natural assumption is a lower per-unit price for buying in bulk — I checked
it directly:

| product_line | Retail avg unit price | Wholesale avg unit price | Difference |
|---|---|---|---|
| Braking system | $17.60 | $18.19 | +3.4% |
| Miscellaneous | $22.54 | $23.65 | +4.9% |
| Electrical system | $25.50 | $25.93 | +1.7% |
| Engine | $59.87 | $60.92 | +1.8% |
| Frame & body | $42.81 | $42.91 | +0.2% |
| Suspension & traction | $33.98 | $33.94 | -0.1% |

**There is no bulk discount anywhere in this dataset.** If anything,
wholesale pays a slightly *higher* average unit price in 5 of 6 product
lines. Wholesale's revenue advantage comes entirely from ordering ~4x the
quantity per order, not from a better rate — worth flagging to the pricing
team as either an intentional policy or a gap worth revisiting.

### 11 · Revenue Concentration — Do a Few Large Orders Drive the Business?
A Pareto-style check tying queries 02 and 06 together:

- The **top 200 orders** (20% of all 1,000, by dollar value) generate
  **$166,127.52 — 57.5% of total revenue**.
- Of those 200 largest orders, **154 (77.0%) are Wholesale** — despite
  wholesale being only 22.5% of all orders overall.

This closes the loop on the analysis: wholesale isn't just outperforming on
average order size — it's heavily over-represented among the single
largest, most valuable orders in the business (mostly Engine parts out of
Central and North; see [`results/11_top_orders.csv`](results/11_top_orders.csv)
for the 20 largest individual orders). Revenue is concentrated in a
relatively small number of large wholesale orders, not spread evenly across
the wholesale segment.

### 12 · ★ What Caused the July Dip? (Follow-up to Query 03)
Query 03 flagged a company-wide -1.9% July dip without explaining it. Same
`LAG()` technique, but partitioned by warehouse instead of computed once
over the whole company:

| warehouse | June | July | % change | August | % change |
|---|---|---|---|---|---|
| Central | $43,327.68 | $47,393.40 | **+9.4%** | $48,797.13 | +3.0% |
| North | $32,752.96 | $28,636.86 | **-12.6%** | $37,194.84 | +29.9% |
| West | $17,578.41 | $15,865.59 | -9.7% | $12,661.56 | **-20.2%** |

Turns out there isn't one clean cause — there are two overlapping stories:

1. **North had a genuine one-month dip** (-12.6% in July), fully reversed
   in August (+29.9%). Central actually *grew* through July, so it isn't
   part of the story at all.
2. **West isn't having a "July dip"** — it's declining every single month
   of the quarter (-9.7% in July, then -20.2% in August). That's a steady
   erosion across the whole quarter, not a one-off blip, and arguably a
   bigger concern than the July number that started this thread.

A supporting cut by product line (same technique, applied to
`product_line` instead of `warehouse`) shows Frame & Body dropped ~26%
company-wide in July, and that drop hit Central, North, *and* West
simultaneously — so it isn't explained by any single warehouse either.

**Bottom line:** July's dip = North's temporary pull-back + broad,
cross-warehouse softness in Frame & Body. West's ongoing decline is a
separate trend that deserves its own attention, not just a footnote on
the July number.

## 🔑 Key Takeaways

- **Wholesale earns its spotlight**: 22.5% of orders, 55.2% of revenue.
- **Central warehouse is the clear leader**, driving the most revenue
  overall and winning the majority of wholesale product/month matchups.
- **North is the strongest #2**, with the highest wholesale mix of the
  three warehouses and several head-to-head wins over Central.
- **Engine parts are a high-ticket, low-volume category** — worth a
  different sales approach than high-volume, low-margin lines like Braking
  System.
- **Payment fees are a modest (~1.7%) but real drag on revenue**, and are
  concentrated entirely in retail credit-card transactions — payment
  method is structurally tied to client type, not a per-order choice, so
  wholesale is already on the cheaper rate.
- **No bulk discount exists for wholesale** — wholesale's revenue edge
  comes purely from larger order quantities (~4x retail), not a better
  per-unit price, which in most product lines is actually slightly higher.
- **Revenue is concentrated in a small number of large wholesale orders**:
  the top 20% of all orders by value generate 57.5% of revenue, and 77% of
  those top orders are wholesale — well above wholesale's 22.5% share of
  order volume.
- **West warehouse is in steady decline, not a one-month dip**: revenue
  fell every month of the quarter (-9.7% in July, -20.2% in August). This
  is a separate, ongoing trend distinct from North's temporary July
  pull-back, and arguably deserves more attention than either.

## ▶️ How to Reproduce

1. Create the `sales` table using [`schema/schema.sql`](schema/schema.sql).
2. Load [`data/motorcycle_parts_sales.csv`](data/motorcycle_parts_sales.csv)
   into the table.
3. Run any file in [`queries/`](queries/) in order (numbered 01–12) against
   a PostgreSQL database — each file is self-contained and commented with
   its own results.
4. Compare your output against the corresponding CSV in
   [`results/`](results/) to confirm a match.

> Queries use PostgreSQL syntax (`EXTRACT()`, `::numeric`). If running on
> SQLite, swap `EXTRACT(MONTH FROM date)` for `CAST(strftime('%m', date) AS INTEGER)`
> and drop the `::numeric` cast — both were used to validate this project's
> results locally.

## ⚠️ Caveats

- Fee treatment note: query 04 (the board's original request) computes net
  revenue by applying `payment_fee` as a rate per row
  (`total * (1 - payment_fee)`). This is the technically correct treatment
  given the column is documented as a fee rate. If your grading rubric or
  downstream tooling instead expects `SUM(total) - SUM(payment_fee)` (fee
  treated as an absolute figure), the two will diverge — check which
  convention your use case expects before comparing numbers.
- Three months of data (June–August 2021) is a short window — the "August
  recovery" in query 03 is a single data point and shouldn't be read as a
  seasonal pattern without more history.
- `West` warehouse has noticeably fewer orders than the other two (180 vs.
  480/340), so its per-product-line/month figures in query 04 are based on
  smaller samples and are more sensitive to a single large order.
- West's month-over-month decline (query 12) is only two data points
  (July, August vs. June) — real, but too short a window to confirm it's
  a genuine trend rather than normal variance. Worth re-checking once a
  fourth month of data is available before treating it as a confirmed
  problem.

---

*Dataset: motorcycle parts sales, June–August 2021 (1,000 orders, provided
as a practice dataset).*

---

**Author:** Aditya Raj Majumder  
🎓 Junior Data Analyst  
🔗 [LinkedIn](https://www.linkedin.com/in/aditya-raj-majumder-600533250/) | [GitHub](https://github.com/Aditya-Raj-Majumder)
