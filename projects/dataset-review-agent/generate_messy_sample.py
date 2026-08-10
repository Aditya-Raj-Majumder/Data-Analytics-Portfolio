"""
Builds a deliberately messy dataset so the profiler has something to find.

Every problem planted here is one I have actually seen in a real export:
numbers stored as text with currency symbols, "N/A" typed instead of left
blank, the same city spelled four ways, an "ID" column that is not unique,
sentinel values standing in for missing, and a handful of exact duplicate rows.

Run:  python generate_messy_sample.py
Out:  samples/messy_sales.csv, samples/messy_sales.xlsx (problems planted)
      samples/clean_sales.csv                    (control: nothing wrong)
"""

import os

import numpy as np
import pandas as pd

RNG = np.random.default_rng(11)
N = 900
OUT_DIR = "samples"


def build() -> pd.DataFrame:
    idx = np.arange(N)

    # --- Identifier that is NOT unique (a classic join-breaker) -------------
    order_id = [f"ORD-{1000 + i}" for i in idx]
    for i in RNG.choice(N, 18, replace=False):        # duplicated IDs
        order_id[i] = order_id[max(0, i - 1)]

    # --- Numeric stored as text, with currency symbols and thousands commas -
    revenue_raw = RNG.gamma(4, 260, N)
    revenue = [f"${v:,.2f}" for v in revenue_raw]
    for i in RNG.choice(N, 25, replace=False):         # disguised nulls
        revenue[i] = "N/A"

    # --- Percentage stored as text -----------------------------------------
    discount = [f"{v:.1f}%" for v in RNG.uniform(0, 35, N)]

    # --- Category with case and whitespace variants -------------------------
    cities = ["Mumbai", "mumbai", "MUMBAI", " Mumbai ", "Delhi", "delhi",
              "DELHI", "Bengaluru", "bengaluru", "Chennai", "chennai", "Kolkata"]
    city = RNG.choice(cities, N, p=[.14, .07, .04, .03, .13, .07, .03, .16, .05, .13, .05, .10])
    city = city.astype(object)
    # "unknown" and "-" are missing values that pandas will NOT read as null,
    # so they silently survive into every count and groupby.
    for i in RNG.choice(N, 31, replace=False):
        city[i] = "unknown"
    for i in RNG.choice(N, 12, replace=False):
        city[i] = "-"

    # --- Dates stored as text, with mixed formats and a few in the future ---
    base = pd.Timestamp("2025-03-01")
    dates = base + pd.to_timedelta(RNG.integers(0, 400, N), unit="D")
    order_date = [d.strftime("%Y-%m-%d") for d in dates]
    for i in RNG.choice(N, 40, replace=False):         # different format
        order_date[i] = dates[i].strftime("%d/%m/%Y")
    for i in RNG.choice(N, 6, replace=False):          # impossible future dates
        order_date[i] = "2031-08-14"

    # --- Quantity with negatives and a sentinel value -----------------------
    quantity = RNG.integers(1, 12, N).astype(float)
    quantity[RNG.choice(N, 9, replace=False)] = -1     # returns coded as -1?
    quantity[RNG.choice(N, 14, replace=False)] = 999   # sentinel for unknown

    # --- Customer age with genuine missingness and impossible values --------
    age = RNG.normal(38, 12, N).round()
    age[RNG.choice(N, 130, replace=False)] = np.nan    # 14% missing
    age[RNG.choice(N, 4, replace=False)] = 0
    age[RNG.choice(N, 3, replace=False)] = 217

    # --- Boolean stored as text --------------------------------------------
    is_member = RNG.choice(["Yes", "No"], N, p=[.34, .66])

    # --- A column that is entirely one value --------------------------------
    currency = ["INR"] * N

    # --- A column that is entirely empty ------------------------------------
    notes = [np.nan] * N

    # --- Two columns holding identical data ---------------------------------
    channel = RNG.choice(["Online", "Store", "Partner"], N, p=[.55, .35, .10])

    # --- Free text with trailing whitespace ---------------------------------
    reps = ["A. Sharma", "R. Iyer ", "  M. Khan", "S. Bose", "P. Nair "]
    sales_rep = RNG.choice(reps, N)

    # --- High-cardinality field that is really an identifier ---------------
    email = [f"customer{i}@example.com" for i in idx]

    df = pd.DataFrame(
        {
            "Order ID": order_id,
            "order_date": order_date,
            "City": city,
            "Revenue": revenue,
            "Discount": discount,
            "Quantity": quantity,
            "Customer Age": age,
            "Is Member": is_member,
            "Channel": channel,
            "Sales Channel": channel,          # exact duplicate of Channel
            "Currency": currency,
            "Sales Rep": sales_rep,
            "Email": email,
            "Notes": notes,
            "": [""] * N,                      # unnamed column
        }
    )

    # --- Exact duplicate rows ----------------------------------------------
    dupes = df.iloc[RNG.choice(N, 22, replace=False)]
    df = pd.concat([df, dupes], ignore_index=True)

    return df.sample(frac=1, random_state=5).reset_index(drop=True)


def build_clean() -> pd.DataFrame:
    """A control dataset with nothing wrong with it.

    Just as important as the messy one. A checker that reports problems in
    every file is no more useful than one that reports none, so there has to
    be a case where the correct output is near-silence.
    """
    rng = np.random.default_rng(2)
    n = 500
    return pd.DataFrame(
        {
            "transaction_id": [f"TX{i:05d}" for i in range(n)],
            "date": pd.date_range("2025-01-01", periods=n, freq="h").strftime("%Y-%m-%d"),
            "product": rng.choice(["Widget", "Gadget", "Doohickey"], n),
            "units": rng.integers(1, 20, n),
            "unit_price": rng.uniform(5, 50, n).round(2),
            "in_stock": rng.choice([True, False], n),
        }
    )


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    messy = build()
    messy.to_csv(f"{OUT_DIR}/messy_sales.csv", index=False)
    messy.to_excel(f"{OUT_DIR}/messy_sales.xlsx", index=False)
    print(f"Wrote {len(messy)} rows x {len(messy.columns)} columns to "
          f"{OUT_DIR}/messy_sales.csv and .xlsx")

    clean = build_clean()
    clean.to_csv(f"{OUT_DIR}/clean_sales.csv", index=False)
    print(f"Wrote {len(clean)} rows x {len(clean.columns)} columns to "
          f"{OUT_DIR}/clean_sales.csv (the control case)")


if __name__ == "__main__":
    main()
