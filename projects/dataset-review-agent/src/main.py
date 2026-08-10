"""
Dataset review agent.

    python -m src.main samples/messy_sales.csv
    python -m src.main data/file.xlsx --sheet "Sheet2" --format md
    python -m src.main data/file.csv --out reports --quiet

Reads a CSV or Excel file, profiles it, diagnoses the problems that will
affect your analysis, and writes a report telling you where to start.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .diagnostics import build_starting_points, diagnose
from .profiler import load_dataset, profile_dataset
from .reporter import write_reports

SEV_MARK = {"high": "!!", "medium": " !", "low": "  "}


def print_summary(profile, findings, steps) -> None:
    counts = {s: sum(1 for f in findings if f.severity == s)
              for s in ("high", "medium", "low")}
    w = 76
    print("\n" + "=" * w)
    print(f"  DATASET REVIEW — {profile.source}")
    print("=" * w)
    print(f"  {profile.rows:,} rows x {profile.columns} columns · "
          f"{profile.memory_mb} MB · {profile.missing_pct}% empty cells")
    print(f"  {profile.duplicate_rows:,} duplicate rows · "
          f"{counts['high']} high, {counts['medium']} medium, {counts['low']} low issues")

    if steps:
        print("\n  WHERE TO START")
        import textwrap
        for i, s in enumerate(steps, 1):
            lines = textwrap.wrap(s.replace("`", ""), w - 8)
            print(f"   {i}. {lines[0]}")
            for line in lines[1:]:
                print(f"      {line}")

    print("\n  FINDINGS")
    for f in findings:
        tag = "fix" if f.kind == "fix" else "decide"
        print(f"   {SEV_MARK[f.severity]} [{tag:<6}] {f.title.replace('`', '')}")
    print("=" * w + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Profile a dataset and report what needs attention before analysis."
    )
    ap.add_argument("file", help="Path to a .csv, .tsv, .xlsx or .xls file")
    ap.add_argument("--sheet", default=0, help="Excel sheet name or index (default: first)")
    ap.add_argument("--out", default="reports", help="Output directory (default: reports)")
    ap.add_argument("--format", default="both", choices=["md", "html", "both"])
    ap.add_argument("--quiet", action="store_true", help="Write files without console output")
    args = ap.parse_args(argv)

    try:
        raw, native = load_dataset(args.file, args.sheet)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if raw.empty:
        print("Error: the file loaded but contains no rows.", file=sys.stderr)
        return 1

    stem = Path(args.file).stem
    profile = profile_dataset(raw, native, Path(args.file).name)
    findings = diagnose(profile)
    steps = build_starting_points(profile, findings)

    formats = ("md", "html") if args.format == "both" else (args.format,)
    written = write_reports(profile, findings, steps, args.out, stem, formats)

    if not args.quiet:
        print_summary(profile, findings, steps)
    for path in written:
        print(f"  Report written: {path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
