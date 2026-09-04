"""
Build the Power BI star schema from the raw Olist CSVs.

Reads the nine Kaggle files from data/raw/ and writes four modelling tables to
data/processed/. Every analytical decision is made here rather than inside the
.pbix, so it can be reviewed, diffed, and rerun without Power BI.

Source: "Brazilian E-Commerce Public Dataset by Olist" (Kaggle), covering
Sept 2016 - Oct 2018.

Usage:
    python build_model.py                      # uses ./data/raw and ./data/processed
    python build_model.py --raw PATH --out PATH
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SECONDS_PER_DAY = 86400

# An order counts as late when order_delivered_customer_date falls after
# order_estimated_delivery_date -- the date the customer was shown at checkout.
# That single definition, applied in add_delivery_measures(), drives every
# headline number in the report.

# Only completed deliveries answer the question "how do customers react to a
# broken delivery promise" -- an order that never arrived has no delivery date
# to compare against. This drops ~3,000 of ~99,400 orders.
INCLUDED_STATUS = "delivered"


def days_between(later, earlier):
    """Signed duration in days between two datetime columns."""
    return (later - earlier).dt.total_seconds() / SECONDS_PER_DAY


def load_raw(raw_dir):
    """Read the source CSVs, parsing the five order timestamps as datetimes."""
    order_dates = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    def read(name, **kwargs):
        return pd.read_csv(raw_dir / f"{name}.csv", **kwargs)

    return {
        "orders": read("olist_orders_dataset", parse_dates=order_dates),
        "customers": read("olist_customers_dataset"),
        "items": read("olist_order_items_dataset"),
        "reviews": read("olist_order_reviews_dataset"),
        "products": read("olist_products_dataset"),
        "sellers": read("olist_sellers_dataset"),
        "categories": read("product_category_name_translation"),
    }


def select_delivered_orders(orders):
    """Restrict to delivered orders that carry all four timestamps.

    A handful of orders are marked delivered but have a missing timestamp, which
    would make their phase durations null. They are dropped rather than imputed:
    guessing a delivery date would invent the very quantity being measured.
    """
    required = [
        "order_delivered_customer_date",
        "order_approved_at",
        "order_delivered_carrier_date",
    ]
    delivered = orders[orders.order_status == INCLUDED_STATUS]
    return delivered.dropna(subset=required).copy()


def add_delivery_measures(df):
    """Derive durations, the lateness flag, and the three delivery phases.

    Phases split the customer's wait into the parts different teams own:
        approval -> payment processing
        handoff  -> the seller getting the parcel to the carrier
        transit  -> the carrier getting it to the door
    """
    df["delivery_days"] = days_between(
        df.order_delivered_customer_date, df.order_purchase_timestamp
    )
    df["promised_days"] = days_between(
        df.order_estimated_delivery_date, df.order_purchase_timestamp
    )
    # Positive slack = delivered early. Negative = the promise was missed.
    df["slack_days"] = days_between(
        df.order_estimated_delivery_date, df.order_delivered_customer_date
    )

    df["approval_days"] = days_between(df.order_approved_at, df.order_purchase_timestamp)
    df["handoff_days"] = days_between(
        df.order_delivered_carrier_date, df.order_approved_at
    )
    df["transit_days"] = days_between(
        df.order_delivered_customer_date, df.order_delivered_carrier_date
    )

    df["is_late"] = (df.slack_days < 0).astype(int)
    df["days_late"] = np.where(df.slack_days < 0, -df.slack_days, 0)

    # ~1,400 orders record carrier pickup before payment approval, which cannot
    # happen. They are flagged rather than deleted: the order still delivered and
    # its lateness is trustworthy, only its phase split is not. Phase measures in
    # the report filter on this flag; everything else keeps the full population.
    impossible = (df.handoff_days < 0) | (df.transit_days < 0)
    df["data_quality_flag"] = np.where(impossible, "negative_phase", "ok")
    return df


def add_review_score(df, reviews):
    """Attach one review per order.

    The review table has more rows than orders because some orders were reviewed
    twice. Keeping the latest answer treats the customer's final word as their
    verdict; keeping the first would instead capture their initial reaction.
    Either is defensible -- the choice is recorded here so it can be changed.
    """
    latest = reviews.sort_values("review_answer_timestamp").drop_duplicates(
        "order_id", keep="last"
    )
    df = df.merge(latest[["order_id", "review_score"]], on="order_id", how="left")

    # 1-star share is the outcome variable, not mean score: 59% of reviews are
    # 5-star, so the mean barely moves while the 1-star rate moves a lot.
    df["is_one_star"] = (df.review_score == 1).astype("Int64")
    return df


def add_order_contents(df, items, products, categories):
    """Roll item rows up to order level and attach a category and seller.

    order_items is one row per item, so it must be aggregated before joining to
    an order-grain fact table or orders would be double counted. Multi-item
    orders are represented by their highest-priced item, which is an
    approximation: a two-item order gets one category, not two.
    """
    products = products.merge(categories, on="product_category_name", how="left")
    items = items.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left",
    )

    totals = (
        items.groupby("order_id")
        .agg(
            item_count=("order_item_id", "max"),
            order_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
        )
        .reset_index()
    )
    dominant = items.sort_values("price", ascending=False).drop_duplicates("order_id")[
        ["order_id", "seller_id", "product_category_name_english"]
    ]

    df = df.merge(totals, on="order_id", how="left")
    df = df.merge(dominant, on="order_id", how="left")
    return df.rename(columns={"product_category_name_english": "category"})


def build_fact(raw):
    """Assemble the order-grain fact table."""
    df = select_delivered_orders(raw["orders"])
    df = add_delivery_measures(df)
    df = add_review_score(df, raw["reviews"])
    df = add_order_contents(df, raw["items"], raw["products"], raw["categories"])

    columns = [
        "order_id", "customer_id", "seller_id", "category",
        "order_purchase_timestamp", "order_estimated_delivery_date",
        "order_delivered_customer_date",
        "delivery_days", "promised_days", "slack_days",
        "approval_days", "handoff_days", "transit_days",
        "is_late", "days_late",
        "review_score", "is_one_star",
        "item_count", "order_value", "freight_value",
        "data_quality_flag",
    ]
    return df[columns].rename(columns={"order_purchase_timestamp": "purchase_date"})


def build_dim_date(fact):
    """Continuous date table -- no source file provides one.

    Power BI needs an unbroken date range to make time intelligence work; a
    relationship straight to purchase_date would silently skip days with no
    orders.
    """
    start = fact.purchase_date.min().normalize()
    end = fact.order_delivered_customer_date.max().normalize()
    dates = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    dates["year"] = dates.date.dt.year
    dates["month"] = dates.date.dt.month
    dates["month_name"] = dates.date.dt.strftime("%b")
    dates["year_month"] = dates.date.dt.strftime("%Y-%m")
    dates["quarter"] = "Q" + dates.date.dt.quarter.astype(str)
    dates["day_of_week"] = dates.date.dt.day_name()
    return dates


def report(fact, orders):
    """Print what was kept, dropped, and flagged, so the run is auditable."""
    delivered = (orders.order_status == INCLUDED_STATUS).sum()
    print(f"source orders           {len(orders):>7,}")
    print(f"  delivered             {delivered:>7,}")
    print(f"  in fact table         {len(fact):>7,}")
    print(f"  dropped (not delivered or missing timestamp) "
          f"{len(orders) - len(fact):>7,}")
    print()
    print(f"late orders             {fact.is_late.sum():>7,} "
          f"({fact.is_late.mean():.1%})")
    print(f"flagged negative phase  "
          f"{(fact.data_quality_flag != 'ok').sum():>7,}")
    print(f"missing a review        {fact.review_score.isna().sum():>7,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="data/raw", type=Path)
    parser.add_argument("--out", default="data/processed", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    raw = load_raw(args.raw)
    fact = build_fact(raw)

    fact.to_csv(args.out / "fact_orders.csv", index=False)
    build_dim_date(fact).to_csv(args.out / "dim_date.csv", index=False)
    raw["customers"][
        ["customer_id", "customer_unique_id", "customer_city", "customer_state"]
    ].to_csv(args.out / "dim_customer.csv", index=False)
    raw["sellers"].to_csv(args.out / "dim_seller.csv", index=False)

    report(fact, raw["orders"])
    print(f"\nwrote 4 tables to {args.out}/")


if __name__ == "__main__":
    main()
