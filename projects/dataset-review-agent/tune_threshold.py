"""
Sensitivity analysis for the sentinel-detection threshold.

The rule flags a value as a probable sentinel when it repeats at least
`min_repeats` times AND sits outside the normal range. `min_repeats` is
defined as `max(3, rate * n_rows)` — and `rate` was originally set to 0.005
because it happened to work, which is not a justification.

This script tests a range of rates against datasets where the planted values
are known, and reports precision and recall for each. The output is the
evidence for whatever rate the project ends up using.

Run:  python tune_threshold.py
"""

from __future__ import annotations

import pandas as pd

from src.profiler import load_dataset, profile_dataset

# Ground truth — the values deliberately planted by generate_messy_sample.py,
# plus the clean file where nothing should fire.
GROUND_TRUTH = {
    "samples/messy_sales.csv": {
        "Quantity": {-1.0, 999.0},        # -1 = return code, 999 = unknown
        "Customer Age": {0.0, 217.0},     # impossible ages used as placeholders
    },
    "samples/clean_sales.csv": {},         # nothing planted
}

RATES = [0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03]


def detect_with_rate(profile, rate: float) -> dict[str, set[float]]:
    """Re-run the sentinel rule with a given rate, returning what it flags."""
    flagged: dict[str, set[float]] = {}

    for c in profile.column_profiles:
        if not c.stats or "mean" not in c.stats or not c.frequent_values:
            continue
        s = c.stats
        iqr = s["q3"] - s["q1"]
        if iqr <= 0 or not c.count:
            continue

        lower, upper = s["q1"] - 1.5 * iqr, s["q3"] + 1.5 * iqr
        min_repeats = max(3, rate * c.count)

        def isolated(value: float) -> bool:
            if c.unique_count > 30:
                return False
            gap = c.frequent_value_gaps.get(value)
            if not gap or c.typical_value_gap <= 0:
                return False
            return gap > 1.5 * c.typical_value_gap

        hits = {
            v for v, n in c.frequent_values
            if n >= min_repeats and (v < lower or v > upper or isolated(v))
        }
        if hits:
            flagged[c.name] = hits

    return flagged


def score(flagged: dict, truth: dict) -> tuple[int, int, int]:
    """Return (true positives, false positives, false negatives)."""
    tp = fp = fn = 0
    for col in set(flagged) | set(truth):
        found = flagged.get(col, set())
        expected = truth.get(col, set())
        tp += len(found & expected)
        fp += len(found - expected)
        fn += len(expected - found)
    return tp, fp, fn


def main() -> None:
    profiles = {}
    for path in GROUND_TRUTH:
        raw, native = load_dataset(path)
        profiles[path] = profile_dataset(raw, native, path)

    rows = []
    for rate in RATES:
        TP = FP = FN = 0
        detail = []
        for path, truth in GROUND_TRUTH.items():
            flagged = detect_with_rate(profiles[path], rate)
            tp, fp, fn = score(flagged, truth)
            TP, FP, FN = TP + tp, FP + fp, FN + fn
            for col, vals in flagged.items():
                for v in sorted(vals):
                    mark = "ok" if v in truth.get(col, set()) else "FALSE POSITIVE"
                    detail.append(f"{path.split('/')[-1]}:{col}={v:g} ({mark})")

        precision = TP / (TP + FP) if (TP + FP) else float("nan")
        recall = TP / (TP + FN) if (TP + FN) else float("nan")
        rows.append({
            "rate": rate,
            "min_repeats (922 rows)": f"{max(3, rate * 922):.1f}",
            "found": TP,
            "false_alarms": FP,
            "missed": FN,
            "precision": f"{precision:.2f}" if TP + FP else "—",
            "recall": f"{recall:.2f}",
            "_detail": "; ".join(detail),
        })

    table = pd.DataFrame(rows)
    print("\nSENTINEL THRESHOLD SENSITIVITY")
    print("=" * 78)
    print(table.drop(columns="_detail").to_string(index=False))
    print("=" * 78)

    print("\nWhat each rate actually flags:\n")
    for r in rows:
        print(f"  rate={r['rate']:<6} {r['_detail'] or '(nothing)'}")
    print()


if __name__ == "__main__":
    main()
