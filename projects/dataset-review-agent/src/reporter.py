"""
Layer 4 - the report.

Two renderers over the same content:
  * Markdown - renders on GitHub without cloning, good for a repo
  * HTML     - standalone file, styled as an inspection report

The visual language is a spec sheet rather than a dashboard: this is a document
you read once at the start of a project, not something you monitor.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .diagnostics import Finding
from .profiler import DatasetProfile

SEV_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}
SEV_HEX = {"high": "#A61B2B", "medium": "#A8660A", "low": "#4C5670"}


def _fmt(v: float | int | None, dp: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1000 or (abs(v) < 0.01 and v != 0):
            return f"{v:,.{dp}g}"
        return f"{v:,.{dp}f}"
    return f"{v:,}"


# ==========================================================================
# Markdown
# ==========================================================================

def render_markdown(p: DatasetProfile, findings: list[Finding], steps: list[str]) -> str:
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("high", "medium", "low")}
    L: list[str] = []

    L.append(f"# Dataset review — `{p.source}`\n")
    L.append(
        f"*Generated {datetime.now():%d %B %Y, %H:%M}. "
        f"This is a starting point, not a verdict — every finding below should be "
        f"checked against what you know about where the data came from.*\n"
    )

    L.append("## At a glance\n")
    L.append("| | |")
    L.append("|---|---|")
    L.append(f"| Rows | {p.rows:,} |")
    L.append(f"| Columns | {p.columns} |")
    L.append(f"| Memory | {p.memory_mb} MB |")
    L.append(f"| Empty cells | {p.missing_cells:,} of {p.total_cells:,} ({p.missing_pct}%) |")
    L.append(f"| Duplicate rows | {p.duplicate_rows:,} ({p.duplicate_row_pct}%) |")
    L.append(
        f"| Issues found | {counts['high']} high · {counts['medium']} medium · "
        f"{counts['low']} low |\n"
    )

    if steps:
        L.append("## Where to start\n")
        L.append("Work through these in order — each one affects the results of the next.\n")
        for i, s in enumerate(steps, 1):
            L.append(f"{i}. {s}")
        L.append("")

    L.append("## Columns\n")
    L.append("| # | Column | Stored as | Reads as | Missing | Distinct | Notes |")
    L.append("|---:|---|---|---|---:|---:|---|")
    for c in p.column_profiles:
        flags = [f for f in findings if f.column == c.name]
        note = ""
        if flags:
            worst = min(flags, key=lambda f: {"high": 0, "medium": 1, "low": 2}[f.severity])
            note = f"{SEV_LABEL[worst.severity]}: {len(flags)} issue(s)"
        L.append(
            f"| {c.position} | `{c.name}` | {c.dtype} | {c.inferred_type} | "
            f"{c.null_pct}% | {c.unique_count:,} | {note} |"
        )
    L.append("")

    L.append("## Findings\n")
    for sev in ("high", "medium", "low"):
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        L.append(f"### {SEV_LABEL[sev]} ({len(group)})\n")
        for f in group:
            tag = "Fix" if f.kind == "fix" else "Decide"
            L.append(f"**{f.title}** · _{tag}_\n")
            L.append(f"{f.detail}\n")
            if f.impact:
                L.append(f"*Why it matters:* {f.impact}\n")
            if f.action:
                L.append(f"*What to do:* {f.action}\n")
            if f.code:
                L.append("```python")
                L.append(f.code)
                L.append("```\n")
        L.append("")

    L.append("## Numeric summary\n")
    nums = [c for c in p.column_profiles if c.stats and "mean" in c.stats]
    if nums:
        L.append("| Column | Mean | Median | Std | Min | Q1 | Q3 | Max | Zeros | Negatives |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for c in nums:
            s = c.stats
            L.append(
                f"| `{c.name}` | {_fmt(s['mean'])} | {_fmt(s['median'])} | {_fmt(s['std'])} "
                f"| {_fmt(s['min'])} | {_fmt(s['q1'])} | {_fmt(s['q3'])} | {_fmt(s['max'])} "
                f"| {s['zeros']:,} | {s['negatives']:,} |"
            )
    else:
        L.append("_No columns parsed as numeric._")
    L.append("")

    cats = [c for c in p.column_profiles if c.top_values and c.inferred_type == "categorical"]
    if cats:
        L.append("## Category breakdown\n")
        for c in cats:
            shown = ", ".join(f"`{v}` ({n:,})" for v, n in c.top_values[:6])
            more = f" … and {c.unique_count - 6:,} more" if c.unique_count > 6 else ""
            L.append(f"- **{c.name}** — {shown}{more}")
        L.append("")

    L.append("---\n")
    L.append(
        "*What this report does not know: what the data is for, how it was collected, "
        "or which of these columns matters to your question. It flags patterns that are "
        "usually problems — confirming whether they are problems here is your job.*"
    )
    return "\n".join(L)


# ==========================================================================
# HTML
# ==========================================================================

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'IBM Plex Sans',system-ui,sans-serif;background:#F5F6F8;color:#14192B;
line-height:1.65;padding:48px 24px;font-size:15px;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto}
.mono{font-family:'IBM Plex Mono',ui-monospace,monospace}

.masthead{border-bottom:2px solid #14192B;padding-bottom:20px;margin-bottom:0}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.18em;
text-transform:uppercase;color:#5C6577}
.masthead h1{font-size:30px;font-weight:600;letter-spacing:-.02em;margin:6px 0 4px}
.masthead .sub{color:#5C6577;font-size:14px}

.ledger{display:flex;border:1px solid #DCE0E7;border-top:none;background:#fff}
.ledger .cell{flex:1;padding:16px 18px;border-right:1px solid #DCE0E7}
.ledger .cell:last-child{border-right:none}
.ledger .k{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;
text-transform:uppercase;color:#5C6577;margin-bottom:5px}
.ledger .v{font-size:24px;font-weight:600;font-family:'IBM Plex Mono',monospace;
letter-spacing:-.02em}
.ledger .v small{font-size:13px;font-weight:400;color:#5C6577;letter-spacing:0}

.sevbar{display:flex;height:8px;border:1px solid #DCE0E7;border-top:none;overflow:hidden}
.sevbar span{display:block}

h2{font-size:13px;font-family:'IBM Plex Mono',monospace;letter-spacing:.16em;
text-transform:uppercase;color:#14192B;margin:44px 0 14px;padding-bottom:8px;
border-bottom:1px solid #DCE0E7}

.steps{counter-reset:s;list-style:none}
.steps li{counter-increment:s;position:relative;padding:10px 0 10px 44px;
border-bottom:1px solid #E6E9ED}
.steps li:last-child{border-bottom:none}
.steps li::before{content:counter(s,decimal-leading-zero);position:absolute;left:0;top:11px;
font-family:'IBM Plex Mono',monospace;font-size:12px;color:#1F4C73;font-weight:500}

table{width:100%;border-collapse:collapse;font-size:13px}
th{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;
text-transform:uppercase;color:#5C6577;text-align:left;padding:8px 10px;
border-bottom:1px solid #DCE0E7;font-weight:500}
td{padding:8px 10px;border-bottom:1px solid #E6E9ED;vertical-align:top}
td.num,th.num{text-align:right;font-family:'IBM Plex Mono',monospace}
tbody tr:hover{background:#FAFBFC}

.finding{background:#fff;border:1px solid #DCE0E7;border-left:3px solid;
border-radius:0;padding:18px 20px;margin-bottom:14px}
.finding .head{display:flex;align-items:baseline;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.finding h3{font-size:16px;font-weight:600;letter-spacing:-.01em}
.pill{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.12em;
text-transform:uppercase;padding:2.5px 7px;border:1px solid;border-radius:2px;white-space:nowrap}
.finding p{margin-bottom:9px;font-size:14px}
.finding .lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;
text-transform:uppercase;color:#5C6577;display:block;margin-bottom:2px}
pre{background:#14192B;color:#E8EAEF;padding:12px 14px;overflow-x:auto;font-size:12.5px;
font-family:'IBM Plex Mono',monospace;line-height:1.55;margin-top:10px}
code{font-family:'IBM Plex Mono',monospace;font-size:.92em;background:#EDEFF3;
padding:1px 4px;border-radius:2px}
pre code{background:none;padding:0;color:inherit}

.hist{display:flex;align-items:flex-end;gap:2px;height:36px;margin-top:6px}
.hist span{flex:1;background:#1F4C73;min-height:1px;opacity:.75}

.colcard{background:#fff;border:1px solid #DCE0E7;padding:14px 16px;margin-bottom:10px}
.colcard .name{font-family:'IBM Plex Mono',monospace;font-weight:500;font-size:14px}
.colcard .meta{font-size:12px;color:#5C6577;margin:3px 0 8px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(92px,1fr));gap:8px;
font-family:'IBM Plex Mono',monospace;font-size:12px}
.kv div span{display:block;font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
color:#5C6577}

footer{margin-top:52px;padding-top:18px;border-top:1px solid #DCE0E7;font-size:13px;
color:#5C6577}
@media(max-width:720px){
  body{padding:24px 14px}.ledger{flex-wrap:wrap}.ledger .cell{flex:1 1 50%;
  border-bottom:1px solid #DCE0E7}
}
"""


def _esc(t: str) -> str:
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _md_inline(t: str) -> str:
    """Backticks to <code>, single asterisks to <em>. Minimal and safe."""
    out, parts = [], _esc(t).split("`")
    for i, part in enumerate(parts):
        out.append(f"<code>{part}</code>" if i % 2 else part)
    html = "".join(out)
    # Emphasis is only converted outside code spans, so split on the tags we
    # just inserted and leave their contents alone.
    segments = re.split(r"(<code>.*?</code>)", html)
    for i, seg in enumerate(segments):
        if not seg.startswith("<code>"):
            segments[i] = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", seg)
    return "".join(segments)


def render_html(p: DatasetProfile, findings: list[Finding], steps: list[str]) -> str:
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("high", "medium", "low")}
    total = max(sum(counts.values()), 1)

    bar = "".join(
        f'<span style="width:{100 * counts[s] / total:.1f}%;background:{SEV_HEX[s]}"></span>'
        for s in ("high", "medium", "low") if counts[s]
    )

    H: list[str] = []
    H.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    H.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    H.append(f"<title>Dataset review — {_esc(p.source)}</title>")
    H.append("<link rel='preconnect' href='https://fonts.googleapis.com'>")
    H.append("<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>")
    H.append("<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
             "&family=IBM+Plex+Sans:wght@400;500;600&display=swap' rel='stylesheet'>")
    H.append(f"<style>{CSS}</style></head><body><div class='wrap'>")

    # Masthead
    H.append("<header class='masthead'>")
    H.append("<div class='eyebrow'>Dataset review</div>")
    H.append(f"<h1 class='mono'>{_esc(p.source)}</h1>")
    H.append(f"<div class='sub'>Generated {datetime.now():%d %B %Y, %H:%M} · "
             f"a starting point for analysis, not a verdict on the data</div>")
    H.append("</header>")

    # Ledger
    H.append("<div class='ledger'>")
    for k, v in [
        ("Rows", f"{p.rows:,}"),
        ("Columns", f"{p.columns}"),
        ("Empty cells", f"{p.missing_pct}<small>%</small>"),
        ("Duplicate rows", f"{p.duplicate_rows:,}"),
        ("Issues", f"{sum(counts.values())}"),
    ]:
        H.append(f"<div class='cell'><div class='k'>{k}</div><div class='v'>{v}</div></div>")
    H.append("</div>")
    H.append(f"<div class='sevbar'>{bar}</div>")
    H.append(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#5C6577;"
        f"margin-top:7px;letter-spacing:.05em'>"
        f"{counts['high']} high · {counts['medium']} medium · {counts['low']} low</div>"
    )

    # Where to start
    if steps:
        H.append("<h2>Where to start</h2>")
        H.append("<ol class='steps'>")
        for s in steps:
            H.append(f"<li>{_md_inline(s)}</li>")
        H.append("</ol>")

    # Findings
    H.append("<h2>Findings</h2>")
    for f in findings:
        col = SEV_HEX[f.severity]
        tag = "Fix" if f.kind == "fix" else "Decide"
        H.append(f"<div class='finding' style='border-left-color:{col}'>")
        H.append("<div class='head'>")
        H.append(f"<h3>{_md_inline(f.title)}</h3>")
        H.append(f"<span class='pill' style='color:{col};border-color:{col}'>"
                 f"{SEV_LABEL[f.severity]}</span>")
        H.append(f"<span class='pill' style='color:#5C6577;border-color:#DCE0E7'>{tag}</span>")
        H.append("</div>")
        H.append(f"<p>{_md_inline(f.detail)}</p>")
        if f.impact:
            H.append(f"<p><span class='lbl'>Why it matters</span>{_md_inline(f.impact)}</p>")
        if f.action:
            H.append(f"<p><span class='lbl'>What to do</span>{_md_inline(f.action)}</p>")
        if f.code:
            H.append(f"<pre><code>{_esc(f.code)}</code></pre>")
        H.append("</div>")

    # Column table
    H.append("<h2>Columns</h2><table><thead><tr>")
    for h, cls in [("#", "num"), ("Column", ""), ("Stored as", ""), ("Reads as", ""),
                   ("Missing", "num"), ("Distinct", "num"), ("Issues", "num")]:
        H.append(f"<th class='{cls}'>{h}</th>")
    H.append("</tr></thead><tbody>")
    for c in p.column_profiles:
        flags = [f for f in findings if f.column == c.name]
        mark = ""
        if flags:
            worst = min(flags, key=lambda f: {"high": 0, "medium": 1, "low": 2}[f.severity])
            mark = (f"<span style='color:{SEV_HEX[worst.severity]};font-weight:500'>"
                    f"{len(flags)}</span>")
        H.append(
            f"<tr><td class='num'>{c.position}</td>"
            f"<td class='mono'>{_esc(c.name)}</td>"
            f"<td>{c.dtype}</td><td>{c.inferred_type}</td>"
            f"<td class='num'>{c.null_pct}%</td>"
            f"<td class='num'>{c.unique_count:,}</td>"
            f"<td class='num'>{mark}</td></tr>"
        )
    H.append("</tbody></table>")

    # Per-column detail
    H.append("<h2>Column detail</h2>")
    for c in p.column_profiles:
        H.append("<div class='colcard'>")
        H.append(f"<div class='name'>{_esc(c.name)}</div>")
        H.append(f"<div class='meta'>{c.inferred_type} · stored as {c.dtype} · "
                 f"{c.count:,} values · {c.unique_count:,} distinct · {c.null_pct}% missing</div>")

        if c.stats and "mean" in c.stats:
            s = c.stats
            H.append("<div class='kv'>")
            for k, v in [("mean", s["mean"]), ("median", s["median"]), ("std", s["std"]),
                         ("min", s["min"]), ("q1", s["q1"]), ("q3", s["q3"]),
                         ("max", s["max"]), ("zeros", s["zeros"]), ("neg", s["negatives"])]:
                H.append(f"<div><span>{k}</span>{_fmt(v)}</div>")
            H.append("</div>")
            if c.histogram:
                top = max(n for _, n in c.histogram) or 1
                bars = "".join(
                    f"<span style='height:{100 * n / top:.0f}%' title='{_esc(lbl)}: {n}'></span>"
                    for lbl, n in c.histogram
                )
                H.append(f"<div class='hist'>{bars}</div>")
        elif c.stats and "min_date" in c.stats:
            s = c.stats
            H.append("<div class='kv'>")
            H.append(f"<div><span>from</span>{s['min_date']:%Y-%m-%d}</div>")
            H.append(f"<div><span>to</span>{s['max_date']:%Y-%m-%d}</div>")
            H.append(f"<div><span>span</span>{s['span_days']:,}d</div>")
            H.append(f"<div><span>future</span>{s['future_count']}</div>")
            H.append("</div>")
        elif c.top_values:
            biggest = c.top_values[0][1] or 1
            H.append("<table style='margin-top:4px'>")
            for v, n in c.top_values[:6]:
                pct = 100 * n / max(c.count, 1)
                H.append(
                    f"<tr><td class='mono' style='width:45%'>{_esc(v)}</td>"
                    f"<td><div style='background:#1F4C73;opacity:.75;height:8px;"
                    f"width:{100 * n / biggest:.0f}%'></div></td>"
                    f"<td class='num' style='width:22%'>{n:,} ({pct:.1f}%)</td></tr>"
                )
            H.append("</table>")
        H.append("</div>")

    H.append(
        "<footer>This report does not know what the data is for, how it was collected, "
        "or which columns matter to your question. It flags patterns that are usually "
        "problems. Confirming whether they are problems here — and deciding what to do "
        "about them — remains the analyst's job.</footer>"
    )
    H.append("</div></body></html>")
    return "\n".join(H)


# ==========================================================================

def write_reports(
    p: DatasetProfile,
    findings: list[Finding],
    steps: list[str],
    out_dir: str,
    stem: str,
    formats: tuple[str, ...] = ("md", "html"),
) -> list[Path]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if "md" in formats:
        path = Path(out_dir) / f"{stem}_review.md"
        path.write_text(render_markdown(p, findings, steps), encoding="utf-8")
        written.append(path)

    if "html" in formats:
        path = Path(out_dir) / f"{stem}_review.html"
        path.write_text(render_html(p, findings, steps), encoding="utf-8")
        written.append(path)

    return written
