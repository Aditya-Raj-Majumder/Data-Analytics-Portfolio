"""
Layer 1 - the profile.

Measures the dataset. No opinions here, only facts: shape, types, missingness,
uniqueness, distributions. Everything in this module should be something you
could verify by hand.

The one piece of interpretation that lives here is `inferred_type` - a guess at
what a column *means* (identifier, category, measurement) as opposed to how
pandas happens to store it. That guess drives which checks run later, so it is
deliberately conservative and always reported alongside the actual dtype.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Strings that mean "missing" but do not read as missing to pandas.
DISGUISED_NULLS = {
    "n/a", "na", "n.a.", "none", "null", "nil", "-", "--", "?", "unknown",
    "not available", "not applicable", "missing", "tbd", "#n/a", "blank",
}

BOOLEAN_SETS = [
    {"yes", "no"}, {"y", "n"}, {"true", "false"}, {"t", "f"},
    {"1", "0"}, {"male", "female"}, {"active", "inactive"},
]

# Column names that imply the values should never be negative.
NON_NEGATIVE_HINTS = (
    "age", "price", "cost", "amount", "revenue", "quantity", "qty", "count",
    "total", "salary", "income", "duration", "distance", "weight", "height",
    "stock", "balance", "score", "rating", "units",
)

IDENTIFIER_HINTS = ("id", "code", "key", "number", "no", "ref", "uuid", "guid")

CURRENCY_RE = re.compile(r"^\s*[-+]?[$£€₹¥]?\s*[\d,]+\.?\d*\s*%?\s*$")


@dataclass
class ColumnProfile:
    name: str
    position: int
    dtype: str            # how pandas read it unaided
    inferred_type: str
    count: int                 # non-null
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    sample_values: list[Any] = field(default_factory=list)
    top_values: list[tuple[Any, int]] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)
    histogram: list[tuple[str, int]] = field(default_factory=list)
    # Raw measurements the diagnostics layer consumes
    disguised_null_count: int = 0
    disguised_null_tokens: list[str] = field(default_factory=list)
    whitespace_count: int = 0
    case_collapsed_unique: int | None = None
    numeric_parseable_pct: float | None = None
    date_parseable_pct: float | None = None
    is_boolean_like: bool = False
    mixed_type_count: int = 0
    # The most-repeated numeric values, with how often each occurs.
    # Sentinel detection needs frequency, and `top_values` above is only
    # populated for text columns, so numerics need their own copy.
    frequent_values: list[tuple[float, int]] = field(default_factory=list)
    # Distance from each frequent value to the nearest OTHER value in the
    # column, and the median distance between neighbouring values overall.
    # Together these say whether a value is stranded on its own.
    frequent_value_gaps: dict[float, float] = field(default_factory=dict)
    typical_value_gap: float = 0.0


@dataclass
class DatasetProfile:
    source: str
    rows: int
    columns: int
    memory_mb: float
    duplicate_rows: int
    duplicate_row_pct: float
    total_cells: int
    missing_cells: int
    missing_pct: float
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    identical_column_pairs: list[tuple[str, str]] = field(default_factory=list)
    unnamed_columns: list[str] = field(default_factory=list)
    duplicate_column_names: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_dataset(path: str, sheet: str | int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the file twice and return (raw_as_text, native).

    Two passes are necessary, and the reason is worth stating because it is a
    real trap. A CSV holds nothing but text, so reading one with `dtype=str`
    makes *every* column look like "numbers stored as text" — which is true and
    completely useless as a finding.

    What actually matters is whether pandas' own type inference *fails* on a
    column. `1234` infers as int64 and is fine. `$1,234` stays object, and that
    is the real problem worth reporting.

    So: `native` is what pandas makes of the file unaided, and is what the
    dtype checks judge against. `raw` preserves the original strings so
    whitespace, casing and placeholder text survive to be measured.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {p}")

    suffix = p.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        sep = "\t" if suffix in {".tsv", ".txt"} else ","
        raw = pd.read_csv(p, sep=sep, dtype=str, keep_default_na=True, low_memory=False)
        native = pd.read_csv(p, sep=sep, low_memory=False)
    elif suffix in {".xlsx", ".xls", ".xlsm"}:
        raw = pd.read_excel(p, sheet_name=sheet, dtype=str)
        native = pd.read_excel(p, sheet_name=sheet)
    else:
        raise ValueError(f"Unsupported file type '{suffix}'. Use .csv, .tsv, .xlsx or .xls.")

    return raw, native


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _try_numeric(series: pd.Series) -> pd.Series:
    """Parse a text series to numbers, tolerating currency symbols and commas."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(r"[$£€₹¥,\s]", "", regex=True)
        .str.replace("%", "", regex=False)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)   # (123) -> -123
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _try_datetime(series: pd.Series) -> pd.Series:
    with pd.option_context("mode.chained_assignment", None):
        parsed = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)
    return parsed


def _infer_type(
    name: str,
    non_null: pd.Series,
    unique_count: int,
    rows: int,
    numeric_pct: float,
    date_pct: float,
    is_bool: bool,
) -> str:
    """Guess what the column *means*, not how it is stored."""
    if len(non_null) == 0:
        return "empty"
    if unique_count == 1:
        return "constant"
    if is_bool:
        return "boolean"
    if date_pct >= 0.85:
        return "datetime"
    if numeric_pct >= 0.85:
        return "numeric"

    lowered = name.lower().replace("_", " ")
    name_suggests_id = any(
        h == w or lowered.endswith(f" {h}") or lowered.startswith(f"{h} ")
        for h in IDENTIFIER_HINTS for w in [lowered]
    ) or any(h in lowered.split() for h in IDENTIFIER_HINTS)

    uniqueness = unique_count / max(len(non_null), 1)
    if uniqueness > 0.95 and (name_suggests_id or unique_count > 50):
        return "identifier"
    if unique_count <= 25 or uniqueness < 0.05:
        return "categorical"
    if non_null.astype(str).str.len().mean() > 40:
        return "text"
    return "categorical" if uniqueness < 0.5 else "text"


def _histogram(values: pd.Series, bins: int = 10) -> list[tuple[str, int]]:
    clean = values.dropna()
    if len(clean) < 5 or clean.nunique() < 2:
        return []
    counts, edges = np.histogram(clean, bins=bins)
    return [
        (f"{edges[i]:,.4g} – {edges[i + 1]:,.4g}", int(counts[i]))
        for i in range(len(counts))
    ]


# --------------------------------------------------------------------------
# Column profiling
# --------------------------------------------------------------------------

def profile_column(
    series: pd.Series, position: int, rows: int, native_dtype: str
) -> ColumnProfile:
    name = str(series.name)
    raw = series
    as_text = raw.astype(str)

    # Disguised nulls have to be found before anything else, because they
    # inflate every other count.
    lowered = as_text.str.strip().str.lower()
    disguised_mask = lowered.isin(DISGUISED_NULLS) | (lowered == "")
    disguised_mask &= raw.notna()
    disguised_tokens = sorted(lowered[disguised_mask].unique().tolist())

    # Treat disguised nulls as missing for every downstream measurement.
    effective = raw.where(~disguised_mask)
    non_null = effective.dropna()

    null_count = int(len(raw) - len(non_null))
    unique_count = int(non_null.nunique())

    numeric = _try_numeric(non_null) if len(non_null) else pd.Series(dtype=float)
    numeric_pct = float(numeric.notna().mean()) if len(non_null) else 0.0

    date_pct = 0.0
    if len(non_null) and numeric_pct < 0.85:
        parsed = _try_datetime(non_null)
        date_pct = float(parsed.notna().mean())

    text_lower = non_null.astype(str).str.strip().str.lower()
    is_bool = bool(len(non_null)) and any(
        set(text_lower.unique()) <= s for s in BOOLEAN_SETS
    ) and unique_count <= 2

    inferred = _infer_type(name, non_null, unique_count, rows, numeric_pct, date_pct, is_bool)

    profile = ColumnProfile(
        name=name,
        position=position,
        dtype=native_dtype,
        inferred_type=inferred,
        count=len(non_null),
        null_count=null_count,
        null_pct=round(100 * null_count / max(rows, 1), 2),
        unique_count=unique_count,
        unique_pct=round(100 * unique_count / max(len(non_null), 1), 2),
        sample_values=non_null.head(5).tolist(),
        disguised_null_count=int(disguised_mask.sum()),
        disguised_null_tokens=disguised_tokens,
        numeric_parseable_pct=round(numeric_pct, 4),
        date_parseable_pct=round(date_pct, 4),
        is_boolean_like=is_bool,
    )

    if len(non_null) == 0:
        return profile

    # Whitespace and case variants only make sense for text-ish columns.
    if inferred in {"categorical", "text", "identifier", "boolean"}:
        text = non_null.astype(str)
        profile.whitespace_count = int((text != text.str.strip()).sum())
        profile.case_collapsed_unique = int(text.str.strip().str.lower().nunique())

        counts = text.value_counts().head(8)
        profile.top_values = [(str(k), int(v)) for k, v in counts.items()]

        # Mixed types: some values parse as numbers, most do not (or vice versa)
        if 0.05 < numeric_pct < 0.95:
            profile.mixed_type_count = int(min(numeric.notna().sum(), numeric.isna().sum()))

    if inferred == "numeric" or numeric_pct >= 0.85:
        vals = numeric.dropna()
        if len(vals):
            profile.stats = {
                "mean": float(vals.mean()),
                "std": float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
                "min": float(vals.min()),
                "q1": float(vals.quantile(0.25)),
                "median": float(vals.median()),
                "q3": float(vals.quantile(0.75)),
                "max": float(vals.max()),
                "zeros": int((vals == 0).sum()),
                "negatives": int((vals < 0).sum()),
                "skew": float(vals.skew()) if len(vals) > 2 else 0.0,
            }
            profile.histogram = _histogram(vals)
            # Which exact values repeat most? A real measurement rarely lands
            # on the identical value dozens of times; a code typed by a human
            # or written by a system does.
            # Which values repeat? Note this is deliberately NOT "the top N
            # by count". A sentinel is *less* common than the real values —
            # 14 rows of 999 against 90 rows each of 1 through 11 — so a
            # ranking by frequency fills up with genuine values and pushes the
            # sentinel off the end. That is exactly backwards.
            #
            # So: every value repeating at least 3 times. The cap exists only
            # to stop a high-cardinality column blowing up the profile, and
            # when it bites we keep the values FURTHEST FROM THE MEDIAN rather
            # than the most common ones — because distance is what makes a
            # value a sentinel candidate in the first place.
            counts = vals.value_counts()
            repeated = counts[counts >= 3]
            if len(repeated) > 60:
                mid = float(vals.median())
                keep = sorted(repeated.index, key=lambda v: abs(v - mid), reverse=True)[:60]
                repeated = repeated.loc[keep]
            profile.frequent_values = [(float(v), int(n)) for v, n in repeated.items()]
            # Isolation must be measured against EVERY distinct value in the
            # column, not just the frequent ones. The 12 most common values of
            # a continuous column are a sparse scatter, and the gaps between
            # them say nothing about the real spacing of the data.
            uniq = np.sort(vals.unique())
            if len(uniq) >= 3:
                steps = np.diff(uniq)
                profile.typical_value_gap = float(np.median(steps))
                profile.frequent_value_gaps = {
                    float(v): float(np.min(np.abs(uniq[uniq != v] - v)))
                    for v, _ in profile.frequent_values
                    if (uniq != v).any()
                }

    if inferred == "datetime":
        parsed = _try_datetime(non_null).dropna()
        if len(parsed):
            profile.stats = {
                "min_date": parsed.min(),
                "max_date": parsed.max(),
                "span_days": int((parsed.max() - parsed.min()).days),
                "future_count": int((parsed > pd.Timestamp.now()).sum()),
            }

    return profile


# --------------------------------------------------------------------------
# Dataset profiling
# --------------------------------------------------------------------------

def profile_dataset(df: pd.DataFrame, native: pd.DataFrame, source: str) -> DatasetProfile:
    rows, cols = df.shape

    dupes = int(df.duplicated().sum())
    columns = [
        profile_column(
            df[c], i, rows,
            str(native[c].dtype) if c in native.columns else str(df[c].dtype),
        )
        for i, c in enumerate(df.columns)
    ]

    missing = sum(c.null_count for c in columns)
    total_cells = rows * cols

    # Columns holding identical values - a common artefact of joins and exports.
    identical: list[tuple[str, str]] = []
    names = list(df.columns)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = df[names[i]], df[names[j]]
            if a.isna().all() and b.isna().all():
                continue
            if a.equals(b):
                identical.append((str(names[i]), str(names[j])))

    unnamed = [
        str(c) for c in df.columns
        if str(c).strip() == "" or str(c).lower().startswith("unnamed:")
    ]
    dup_names = [str(c) for c in pd.Index(df.columns).duplicated(keep=False).nonzero()[0]]

    return DatasetProfile(
        source=source,
        rows=rows,
        columns=cols,
        memory_mb=round(df.memory_usage(deep=True).sum() / 1024**2, 2),
        duplicate_rows=dupes,
        duplicate_row_pct=round(100 * dupes / max(rows, 1), 2),
        total_cells=total_cells,
        missing_cells=missing,
        missing_pct=round(100 * missing / max(total_cells, 1), 2),
        column_profiles=columns,
        identical_column_pairs=identical,
        unnamed_columns=unnamed,
        duplicate_column_names=dup_names,
    )
