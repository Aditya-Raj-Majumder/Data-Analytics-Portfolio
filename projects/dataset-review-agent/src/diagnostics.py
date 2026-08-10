"""
Layer 2 and 3 - diagnose, then advise.

This is the part a profiling library does not do. `ydata-profiling` will tell
you a column has 214 unique values; it will not tell you that 125 of them are
the same city typed differently, that this will split your groupby, and that
you should normalise before aggregating.

Two kinds of finding:

  * `fix`      - unambiguous. Whitespace, dtype conversion, exact duplicates.
                 Safe to give a concrete instruction and the pandas to do it.
  * `question` - depends on domain knowledge the profiler does not have.
                 Phrased as a question, never an instruction. A tool that
                 confidently recommends median imputation for data that is
                 missing-not-at-random does more damage than one that stays
                 quiet.

Severity is about *blocking analysis*, not about how odd the number looks:
  HIGH   - will produce wrong results if you do not deal with it
  MEDIUM - will distort some analyses, or hides something you should know
  LOW    - worth knowing before you start; not dangerous
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .profiler import NON_NEGATIVE_HINTS, ColumnProfile, DatasetProfile

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Finding:
    severity: str            # high | medium | low
    kind: str                # fix | question
    column: str | None
    title: str
    detail: str
    impact: str = ""
    action: str = ""
    code: str | None = None
    evidence: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Dataset-level checks
# --------------------------------------------------------------------------

def check_dataset(profile: DatasetProfile) -> list[Finding]:
    out: list[Finding] = []

    if profile.duplicate_rows:
        out.append(Finding(
            severity="high",
            kind="question",
            column=None,
            title=f"{profile.duplicate_rows} exactly duplicated rows",
            detail=(
                f"{profile.duplicate_rows} rows ({profile.duplicate_row_pct}%) are "
                f"identical to another row across every column."
            ),
            impact=(
                "Every count, sum and average is inflated by these rows. If they "
                "reached you through a join, the duplication may be multiplicative "
                "rather than additive."
            ),
            action=(
                "Decide whether these are genuine repeated events (two identical "
                "orders in the same second is possible but unusual) or an export "
                "artefact. Check whether the source system has a row identifier "
                "that would distinguish them before dropping anything."
            ),
            code="df[df.duplicated(keep=False)].sort_values(list(df.columns))",
        ))

    if profile.identical_column_pairs:
        pairs = ", ".join(f"`{a}` = `{b}`" for a, b in profile.identical_column_pairs)
        out.append(Finding(
            severity="medium",
            kind="fix",
            column=None,
            title="Columns holding identical data",
            detail=f"These column pairs contain exactly the same values: {pairs}.",
            impact=(
                "Redundant columns waste memory and, more importantly, will inflate "
                "any correlation matrix or feature-importance ranking you build."
            ),
            action="Keep one of each pair and drop the other.",
            code="df = df.drop(columns=[" + ", ".join(
                f"'{b}'" for _, b in profile.identical_column_pairs) + "])",
        ))

    if profile.unnamed_columns:
        cols = ", ".join(f"`{c}`" for c in profile.unnamed_columns)
        out.append(Finding(
            severity="low",
            kind="fix",
            column=None,
            title="Unnamed columns",
            detail=f"{len(profile.unnamed_columns)} column(s) have no header: {cols}.",
            impact=(
                "Usually a trailing comma or a stray column in the source export. "
                "Harmless, but they clutter every subsequent operation."
            ),
            action="Drop them after confirming they hold nothing you need.",
            code="df = df.loc[:, ~df.columns.str.match(r'^(Unnamed|\\s*$)')]",
        ))

    if profile.missing_pct > 25:
        out.append(Finding(
            severity="medium",
            kind="question",
            column=None,
            title=f"{profile.missing_pct}% of all cells are empty",
            detail=(
                f"{profile.missing_cells:,} of {profile.total_cells:,} cells hold no value."
            ),
            impact=(
                "At this level, row-wise deletion would remove most of the dataset, "
                "so any complete-case analysis will be run on a small and probably "
                "unrepresentative subset."
            ),
            action=(
                "Look at whether the missingness is concentrated in a few columns you "
                "could drop, or spread across many, which is a harder problem."
            ),
        ))

    return out


# --------------------------------------------------------------------------
# Column-level checks
# --------------------------------------------------------------------------

def check_column(c: ColumnProfile, rows: int) -> list[Finding]:
    out: list[Finding] = []
    n = f"`{c.name}`"

    # --- Structural -------------------------------------------------------
    if c.inferred_type == "empty":
        out.append(Finding(
            severity="medium", kind="fix", column=c.name,
            title=f"{n} is completely empty",
            detail="Every value in this column is missing.",
            impact="It carries no information and cannot be used for anything.",
            action="Drop it, after checking the source system was supposed to populate it.",
            code=f"df = df.drop(columns=['{c.name}'])",
        ))
        return out

    if c.inferred_type == "constant":
        value = c.top_values[0][0] if c.top_values else c.sample_values[0]
        out.append(Finding(
            severity="low", kind="fix", column=c.name,
            title=f"{n} holds a single value",
            detail=f"Every one of the {c.count:,} non-null rows is `{value}`.",
            impact=(
                "It has zero variance, so it cannot explain anything or serve as a "
                "grouping key. It may still be worth keeping as documentation of scope."
            ),
            action="Note the value as a property of the dataset, then drop the column.",
            code=f"df = df.drop(columns=['{c.name}'])",
        ))
        return out

    # --- Disguised nulls --------------------------------------------------
    if c.disguised_null_count:
        tokens = ", ".join(f"`{t}`" for t in c.disguised_null_tokens if t)
        out.append(Finding(
            severity="high", kind="fix", column=c.name,
            title=f"{n} uses placeholder text for missing values",
            detail=(
                f"{c.disguised_null_count:,} values are placeholders rather than real "
                f"data: {tokens}. Pandas does not read these as null."
            ),
            impact=(
                "These count as a legitimate category in any groupby or value_counts, "
                "and they will not be caught by `.isna()`. A 'top city' analysis could "
                "return 'unknown' as a real answer."
            ),
            action="Convert them to proper nulls before doing anything else.",
            code=(
                f"df['{c.name}'] = df['{c.name}'].replace("
                f"{[t for t in c.disguised_null_tokens if t]}, pd.NA)"
            ),
            evidence=[f"{t} appears in the data" for t in c.disguised_null_tokens if t][:4],
        ))

    # --- Stored as the wrong type -----------------------------------------
    if c.dtype in {"object", "str", "string"} and (c.numeric_parseable_pct or 0) >= 0.85:
        pct = round(100 * c.numeric_parseable_pct, 1)
        out.append(Finding(
            severity="high", kind="fix", column=c.name,
            title=f"{n} holds numbers stored as text",
            detail=(
                f"{pct}% of values parse as numbers once currency symbols, commas and "
                f"percent signs are stripped. Examples: "
                + ", ".join(f"`{v}`" for v in c.sample_values[:3]) + "."
            ),
            impact=(
                "Arithmetic, sorting and aggregation all behave wrongly on text. "
                "Sorting puts `$9.00` after `$10.00`, and `.mean()` fails outright."
            ),
            action="Strip the symbols and convert to a numeric dtype.",
            code=(
                f"df['{c.name}'] = pd.to_numeric(\n"
                f"    df['{c.name}'].astype(str).str.replace(r'[$£€₹,%\\s]', '', regex=True),\n"
                f"    errors='coerce')"
            ),
        ))

    if (c.dtype in {"object", "str", "string"} and c.inferred_type == "datetime"):
        out.append(Finding(
            severity="high", kind="fix", column=c.name,
            title=f"{n} holds dates stored as text",
            detail=(
                f"{round(100 * (c.date_parseable_pct or 0), 1)}% of values parse as dates. "
                f"Examples: " + ", ".join(f"`{v}`" for v in c.sample_values[:3]) + "."
            ),
            impact=(
                "You cannot filter by range, resample, or extract month and weekday "
                "from text. Mixed formats in the same column are also a real risk here "
                "— `03/04/2025` is ambiguous between April 3rd and March 4th."
            ),
            action=(
                "Convert to datetime, and check the day/month order against a value you "
                "can verify independently before trusting it."
            ),
            code=f"df['{c.name}'] = pd.to_datetime(df['{c.name}'], errors='coerce')",
        ))

    if c.is_boolean_like and c.dtype in {"object", "str", "string"}:
        out.append(Finding(
            severity="low", kind="fix", column=c.name,
            title=f"{n} is a yes/no field stored as text",
            detail="Only two distinct values: "
                   + ", ".join(f"`{v}`" for v, _ in c.top_values[:2]) + ".",
            impact="Boolean dtype is smaller and works directly with `.sum()` and filters.",
            action="Map to True/False.",
            code=(
                f"df['{c.name}'] = df['{c.name}'].str.strip().str.lower()"
                f".map({{'yes': True, 'no': False, 'y': True, 'n': False, "
                f"'true': True, 'false': False}})"
            ),
        ))

    if c.mixed_type_count:
        out.append(Finding(
            severity="medium", kind="question", column=c.name,
            title=f"{n} mixes numbers and text",
            detail=(
                f"About {c.mixed_type_count:,} values are the minority type — some "
                f"entries parse as numbers and some do not."
            ),
            impact=(
                "Whichever way you convert, you lose the other group. Coercing to "
                "numeric silently turns the text entries into nulls."
            ),
            action=(
                "Look at the non-numeric values before converting. They are often "
                "meaningful — range markers like `<5`, or notes appended to a figure."
            ),
            code=(
                f"df.loc[pd.to_numeric(df['{c.name}'], errors='coerce').isna() "
                f"& df['{c.name}'].notna(), '{c.name}'].value_counts().head(20)"
            ),
        ))

    # --- Text hygiene ------------------------------------------------------
    if c.case_collapsed_unique is not None and c.case_collapsed_unique < c.unique_count:
        lost = c.unique_count - c.case_collapsed_unique
        out.append(Finding(
            severity="high", kind="fix", column=c.name,
            title=f"{n} has inconsistent capitalisation or spacing",
            detail=(
                f"{c.unique_count} distinct values collapse to {c.case_collapsed_unique} "
                f"once case and whitespace are normalised — {lost} are duplicates in "
                f"different clothing."
            ),
            impact=(
                "Any groupby, join or value_counts splits these across variants. "
                "A city with 300 orders can appear as three cities with 100 each, and "
                "nothing in the output tells you it happened."
            ),
            action=(
                "Normalise before aggregating. Be careful with `.title()` on proper "
                "nouns — it breaks names like `McAllen` and `O'Brien`."
            ),
            code=f"df['{c.name}'] = df['{c.name}'].str.strip().str.lower()",
            evidence=[f"{v} ({n_}) " for v, n_ in c.top_values[:5]],
        ))
    elif c.whitespace_count:
        out.append(Finding(
            severity="medium", kind="fix", column=c.name,
            title=f"{n} has leading or trailing whitespace",
            detail=f"{c.whitespace_count:,} values have spaces at the start or end.",
            impact="Joins and equality filters fail silently on these — `'Delhi ' != 'Delhi'`.",
            action="Strip whitespace.",
            code=f"df['{c.name}'] = df['{c.name}'].str.strip()",
        ))

    # --- Missingness -------------------------------------------------------
    if c.null_pct >= 50:
        sev = "high"
    elif c.null_pct >= 20:
        sev = "medium"
    elif c.null_pct >= 5:
        sev = "low"
    else:
        sev = None

    if sev:
        out.append(Finding(
            severity=sev, kind="question", column=c.name,
            title=f"{n} is {c.null_pct}% missing",
            detail=f"{c.null_count:,} of {rows:,} rows have no value.",
            impact=(
                "Dropping these rows shrinks your sample; filling them invents data. "
                "Which is worse depends entirely on *why* they are missing."
            ),
            action=(
                "Ask whether the missingness is random. If the people who skipped this "
                "field differ systematically from those who did not — high earners "
                "declining to state income, say — then both dropping and mean-filling "
                "will bias your results, in opposite directions. Check whether the "
                "nulls cluster by date, source, or another column."
            ),
            code=f"df[df['{c.name}'].isna()].describe(include='all')",
        ))

    # --- Identifier integrity ---------------------------------------------
    lowered = c.name.lower()
    looks_like_id = c.inferred_type == "identifier" or any(
        h in re.split(r"[\s_\-]+", lowered) for h in ("id", "key", "code", "ref")
    )
    if looks_like_id and c.count and c.unique_count < c.count:
        dupes = c.count - c.unique_count
        out.append(Finding(
            severity="high", kind="question", column=c.name,
            title=f"{n} looks like an identifier but is not unique",
            detail=(
                f"{c.unique_count:,} distinct values across {c.count:,} rows — "
                f"{dupes:,} rows share an identifier with another row."
            ),
            impact=(
                "If you join on this column, matching rows multiply: a value appearing "
                "twice on each side produces four rows. This is the single most common "
                "cause of silently inflated totals."
            ),
            action=(
                "Establish what actually makes a row unique before joining. It may be "
                "this column combined with a date or a line number."
            ),
            code=f"df['{c.name}'].value_counts().loc[lambda s: s > 1].head(20)",
        ))

    # --- Numeric plausibility ---------------------------------------------
    if c.stats and "mean" in c.stats:
        s = c.stats
        name_implies_positive = any(h in lowered for h in NON_NEGATIVE_HINTS)

        if s["negatives"] and name_implies_positive:
            out.append(Finding(
                severity="high", kind="question", column=c.name,
                title=f"{n} contains negative values",
                detail=(
                    f"{s['negatives']:,} values are below zero, with a minimum of "
                    f"{s['min']:,.2f}. The column name suggests it should not be negative."
                ),
                impact=(
                    "Sums and averages are pulled down by values that may not be real "
                    "measurements at all."
                ),
                action=(
                    "These are often codes rather than quantities — `-1` standing for "
                    "'unknown', or a negative amount marking a return or refund. Find "
                    "out which before aggregating, and separate them if they are a "
                    "different kind of event."
                ),
                code=f"df[df['{c.name}'] < 0].head(20)",
            ))

        # --- Sentinel detection ------------------------------------------
        # The question is NOT "does this number look like a placeholder"
        # (round, negative, 999-ish) — that misses -999 sitting in the middle
        # of a wide range, and false-alarms on genuine round maximums.
        #
        # The question is "does this number BEHAVE like a placeholder", which
        # means two things at once:
        #   1. it sits well outside the normal cluster of values, AND
        #   2. it repeats far more often than anything out there should.
        #
        # A genuine extreme — one customer really ordering 400 units — appears
        # once or twice. A code someone types when data is missing appears
        # dozens of times. Repetition is the giveaway, not appearance.
        iqr = s["q3"] - s["q1"]
        if iqr > 0 and c.frequent_values and c.count:
            # How many repeats count as "too many"?
            # 0.002 comes from the sensitivity analysis in tune_threshold.py,
            # not from intuition. Rates from 0.001 to 0.003 all catch every
            # planted sentinel with no false alarms; 0.005 and above start
            # missing them. 0.002 sits in the middle of that stable band, so
            # the result does not hinge on the exact number.
            # Note the floor of 3 is what actually binds below ~1,500 rows —
            # the rate only takes over on larger datasets.
            min_repeats = max(3, 0.002 * c.count)

            # Test A — is the value far from the middle of the data?
            # The usual IQR fence. Catches 999 in a column running 1 to 11.
            lower_fence = s["q1"] - 1.5 * iqr
            upper_fence = s["q3"] + 1.5 * iqr

            # Test B — is the value stranded on its own, with a gap between it
            # and everything else? This exists because Test A is not enough.
            # In this sample, Quantity runs 1 to 11 with -1 used as a code, but
            # the IQR fence reaches down to -6, so -1 sits *inside* it and Test
            # A never sees it. Yet -1 is obviously separated: the real values
            # step by 1, and then there is a jump of 2 down to -1.
            # `typical_value_gap` is the median step between neighbouring
            # values across the whole column; a value whose nearest neighbour
            # is much further away than that is stranded.
            def is_isolated(value: float) -> bool:
                # The gap test only makes sense on a discrete column with a
                # small, densely-packed set of values — order quantities,
                # ratings, counts. In a continuous column the values thin out
                # naturally in the tails, so a wide gap up there means only
                # "this is the tail", not "this is a code". Testing on the
                # sample showed exactly that: a plausible age of 63 got
                # flagged purely because ages are sparse at that end.
                if c.unique_count > 30:
                    return False
                gap = c.frequent_value_gaps.get(value)
                if not gap or c.typical_value_gap <= 0:
                    return False
                return gap > 1.5 * c.typical_value_gap

            suspects = [
                (value, count)
                for value, count in c.frequent_values
                if count >= min_repeats
                and (value < lower_fence or value > upper_fence or is_isolated(value))
            ]

            if suspects:
                listed = ", ".join(
                    f"`{v:,.0f}` ({n:,} times)" if float(v).is_integer()
                    else f"`{v:,.2f}` ({n:,} times)"
                    for v, n in suspects
                )
                out.append(Finding(
                    severity="medium", kind="question", column=c.name,
                    title=f"{n} may use sentinel values for missing data",
                    detail=(
                        f"{listed} — each sits outside the normal range "
                        f"({s['q1']:,.2f} to {s['q3']:,.2f} covers the middle half of "
                        f"the data) yet repeats often. Genuine extreme measurements "
                        f"usually appear once or twice, not dozens of times."
                    ),
                    impact=(
                        "If these are codes rather than measurements, every average, "
                        "sum and total computed from this column is wrong. A handful "
                        "of 999s in a column that otherwise tops out at 12 will "
                        "dominate the mean without any warning."
                    ),
                    action=(
                        "Check what these values mean in the source system. Common "
                        "conventions are -1 or 999 for 'unknown', 0 for 'not "
                        "recorded', and negative amounts marking returns. If they are "
                        "codes, convert them to nulls before aggregating; if they mark "
                        "a different kind of event, separate those rows out."
                    ),
                    code=(
                        f"df['{c.name}'].value_counts().head(15)\n"
                        f"# then, once confirmed:\n"
                        f"df['{c.name}'] = df['{c.name}'].replace("
                        f"{[v for v, _ in suspects]}, pd.NA)"
                    ),
                    evidence=[f"{v:,.0f} appears {n:,} times" for v, n in suspects[:4]],
                ))

        if s["zeros"] and c.count and s["zeros"] / c.count > 0.25:
            out.append(Finding(
                severity="low", kind="question", column=c.name,
                title=f"{n} is {round(100 * s['zeros'] / c.count)}% zeros",
                detail=f"{s['zeros']:,} of {c.count:,} values are exactly zero.",
                impact=(
                    "Zero-inflation pulls the mean toward zero and makes it a poor "
                    "summary. Ratios using this as a denominator will fail."
                ),
                action=(
                    "Decide whether zero means 'none' or 'not recorded'. If it is "
                    "standing in for missing, the mean of the non-zero values is the "
                    "more honest figure."
                ),
            ))

        # Skew alone is not enough to justify the claim that the mean is a bad
        # summary. A handful of impossible values (three rows of age 217) push
        # the skew statistic above 4 while leaving mean and median almost
        # identical — at which point the mean IS representative, and reporting
        # otherwise contradicts the evidence printed alongside it. Those
        # extreme values are already caught by the sentinel and outlier checks.
        # So: require the mean and median to have actually pulled apart, by at
        # least 10% of the interquartile spread.
        spread = s["q3"] - s["q1"]
        divergence = abs(s["mean"] - s["median"])
        if abs(s["skew"]) > 2 and spread > 0 and divergence > 0.1 * spread:
            direction = "right" if s["skew"] > 0 else "left"
            pulled = "above" if s["mean"] > s["median"] else "below"
            out.append(Finding(
                severity="low", kind="question", column=c.name,
                title=f"{n} is heavily {direction}-skewed",
                detail=(
                    f"Skew is {s['skew']:.1f}, and the mean ({s['mean']:,.2f}) sits "
                    f"{pulled} the median ({s['median']:,.2f}) by "
                    f"{divergence:,.2f} — around {100 * divergence / spread:.0f}% of "
                    f"the interquartile spread."
                ),
                impact=(
                    "A long tail is pulling the mean away from the typical row, so "
                    "the average describes the tail more than the bulk of the data. "
                    "Any method assuming normality will also be poorly calibrated."
                ),
                action=(
                    "Report the median alongside the mean, and consider a log scale "
                    "for charts. Check first whether the tail is genuine or the "
                    "result of a few bad values."
                ),
            ))

        # IQR outliers - reported, never auto-removed.
        iqr = s["q3"] - s["q1"]
        if iqr > 0:
            lo, hi = s["q1"] - 1.5 * iqr, s["q3"] + 1.5 * iqr
            if s["max"] > hi or s["min"] < lo:
                out.append(Finding(
                    severity="low", kind="question", column=c.name,
                    title=f"{n} has values outside the usual range",
                    detail=(
                        f"The middle 50% sits between {s['q1']:,.2f} and {s['q3']:,.2f}, "
                        f"but the full range runs {s['min']:,.2f} to {s['max']:,.2f}."
                    ),
                    impact=(
                        "These may be genuine extremes, data entry errors, or a "
                        "different kind of record mixed into the same column."
                    ),
                    action=(
                        "Look at them individually before deciding. Outliers are often "
                        "the most interesting rows in the dataset, not the least — "
                        "removing them by rule is rarely the right first move."
                    ),
                    code=(
                        f"q1, q3 = df['{c.name}'].quantile([.25, .75])\n"
                        f"iqr = q3 - q1\n"
                        f"df[(df['{c.name}'] < q1 - 1.5*iqr) | (df['{c.name}'] > q3 + 1.5*iqr)]"
                    ),
                ))

    # --- Dates -------------------------------------------------------------
    if c.inferred_type == "datetime" and c.stats.get("future_count"):
        out.append(Finding(
            severity="medium", kind="question", column=c.name,
            title=f"{n} contains dates in the future",
            detail=f"{c.stats['future_count']:,} values are later than today.",
            impact=(
                "Future dates in a historical dataset usually mean a typo in the year, "
                "a placeholder, or a genuinely scheduled record mixed with completed ones."
            ),
            action="Inspect them; decide whether they belong in this analysis at all.",
            code=f"df[df['{c.name}'] > pd.Timestamp.now()]",
        ))

    # --- Cardinality -------------------------------------------------------
    if c.inferred_type == "categorical" and c.unique_count > 50:
        out.append(Finding(
            severity="low", kind="question", column=c.name,
            title=f"{n} has {c.unique_count:,} distinct categories",
            detail=f"That is a lot of levels for {c.count:,} rows.",
            impact=(
                "Charts become unreadable and one-hot encoding explodes the feature "
                "count. Many levels will have too few rows to say anything about."
            ),
            action=(
                "Check whether a natural grouping exists, or keep the top N and bucket "
                "the rest as 'Other' — noting how much of the data that bucket holds."
            ),
        ))

    return out


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def diagnose(profile: DatasetProfile) -> list[Finding]:
    findings = check_dataset(profile)
    for c in profile.column_profiles:
        findings.extend(check_column(c, profile.rows))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.column or ""))
    return findings


def build_starting_points(profile: DatasetProfile, findings: list[Finding]) -> list[str]:
    """A short, ordered 'do this first' list - the primary direction."""
    steps: list[str] = []
    high = [f for f in findings if f.severity == "high"]

    if any("placeholder text" in f.title for f in high):
        steps.append(
            "Convert placeholder text to real nulls first. Every count you run before "
            "this will be wrong in a way that does not announce itself."
        )
    if any("stored as text" in f.title for f in high):
        steps.append(
            "Fix the dtypes next. Numbers and dates trapped as text cannot be "
            "aggregated or filtered correctly."
        )
    if any("capitalisation" in f.title for f in high):
        steps.append(
            "Normalise text categories before any groupby, or your category totals "
            "will be split across spelling variants."
        )
    if any("not unique" in f.title for f in high):
        steps.append(
            "Establish the true row key before joining anything to this dataset."
        )
    if profile.duplicate_rows:
        steps.append(
            "Decide what to do about the exact duplicate rows — they affect every "
            "total in the dataset."
        )

    usable = [
        c.name for c in profile.column_profiles
        if c.inferred_type in {"numeric", "datetime"} and c.null_pct < 20
    ]
    if usable:
        steps.append(
            "Once the above are done, the columns in the best shape to analyse first "
            "are: " + ", ".join(f"`{c}`" for c in usable[:6]) + "."
        )

    return steps
