#!/usr/bin/env python3
"""Post-Push PR Review Catches & Escape Rate HTML card for /debrief."""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debrief_common import safe_int  # noqa: E402


def _e(val):
    return html.escape(str(val if val is not None else ""), quote=True)


def _fmt_pct_val(val):
    return "—" if val is None else f"{val:.1f}%"


def render_review_escapes_card(agg):
    """Render PR review escape card; returns '' when no PR review data is loaded."""
    rev = agg.get("review_escapes")
    if not isinstance(rev, dict) or safe_int(rev.get("prs_reviewed"), 0) == 0:
        return ""

    prs_rev = safe_int(rev.get("prs_reviewed"), 0)
    prs_esc = safe_int(rev.get("prs_with_real_escapes"), 0)
    esc_pct = _fmt_pct_val(rev.get("escape_rate_pct"))
    rep_prs = safe_int(rev.get("prs_with_repeat_p1"), 0)
    multi = safe_int(rev.get("prs_multi_round"), 0)
    rep_pct = _fmt_pct_val(rev.get("repeat_p1_rate_pct"))
    real_p1 = safe_int(rev.get("real_p0"), 0) + safe_int(rev.get("real_p1"), 0)
    real_p2 = safe_int(rev.get("real_p2"), 0)
    timing_p1 = safe_int(rev.get("timing_noise_p1"), 0)
    unans = safe_int(rev.get("threads_unanswered"), 0)
    th_tot = safe_int(rev.get("threads_total"), 0)
    unans_pct = _fmt_pct_val(rev.get("unanswered_pct"))
    unres_m = safe_int(rev.get("threads_unresolved_on_merged"), 0)
    joined = safe_int(rev.get("joined_prs"), 0)

    tiles = [
        (f"{esc_pct}", f"Real Escape Rate ({prs_esc}/{prs_rev} PRs)"),
        (f"{real_p1} P1 / {real_p2} P2", "Real Escaped Findings"),
        (f"{timing_p1}", "CI-Timing / Sandbox Noise P1s"),
        (f"{rep_pct}", f"Repeat-P1 Rate ({rep_prs}/{multi} multi-round)"),
        (f"{unans_pct}", f"Unanswered Threads ({unans}/{th_tot}; {unres_m} open at merge)"),
    ]
    tiles_html = "".join(
        f'<div class="stat"><div class="stat-value">{_e(v)}</div><div class="stat-label">{_e(lbl)}</div></div>'
        for v, lbl in tiles
    )

    src_chips = ", ".join(f"{k}: {v}" for k, v in (rev.get("by_reviewer_source") or {}).items())

    cat_rows = []
    for row in (rev.get("by_category") or [])[:10]:
        prs_str = ", ".join(f"#{n}" for n in (row.get("prs") or [])[:5])
        cat_rows.append(
            f'<tr><td><code>{_e(row.get("category"))}</code></td>'
            f'<td class="num">{safe_int(row.get("p0"), 0) + safe_int(row.get("p1"), 0)}</td>'
            f'<td class="num">{safe_int(row.get("p2"), 0)}</td>'
            f'<td class="num">{safe_int(row.get("repeat"), 0)}</td>'
            f'<td>{_e(prs_str or "—")}</td>'
            f'<td>{_e(row.get("hint"))}</td></tr>'
        )

    cat_tbl = ""
    if cat_rows:
        cat_tbl = (
            '<table><thead><tr><th>Escaped Defect Class</th>'
            '<th class="num">P0/P1</th><th class="num">P2</th><th class="num">Repeats</th>'
            '<th>PRs</th><th>Suggested Skill / Hook Fix</th></tr></thead>'
            f'<tbody>{"".join(cat_rows)}</tbody></table>'
        )

    sk_rows = []
    for sk, info in sorted(
        (rev.get("per_skill") or {}).items(),
        key=lambda kv: (-(kv[1].get("real_p1", 0) * 3 + kv[1].get("real_p2", 0)), kv[0]),
    )[:8]:
        if safe_int(info.get("real_p1"), 0) + safe_int(info.get("real_p2"), 0) == 0:
            continue
        top_c = ", ".join(f"{k} ({v})" for k, v in (info.get("top_categories") or {}).items())
        sk_rows.append(
            f'<tr><td><code>{_e(sk)}</code></td>'
            f'<td class="num">{safe_int(info.get("prs"), 0)}</td>'
            f'<td class="num">{safe_int(info.get("real_p1"), 0)}</td>'
            f'<td class="num">{safe_int(info.get("real_p2"), 0)}</td>'
            f'<td>{_e(top_c or "—")}</td></tr>'
        )
    sk_tbl = ""
    if sk_rows:
        sk_tbl = (
            '<div style="font-size:13px;font-weight:600;margin:14px 0 6px">'
            f'Loaded Skills in Escaped PR Sessions ({joined} PRs joined to local sessions)</div>'
            '<table><thead><tr><th>Skill Loaded</th><th class="num">Joined PRs</th>'
            '<th class="num">Escaped P1</th><th class="num">Escaped P2</th>'
            '<th>Top Escaped Classes</th></tr></thead>'
            f'<tbody>{"".join(sk_rows)}</tbody></table>'
        )

    meta_note = (
        f'<div class="chart-foot">'
        f'Reviewers observed: {_e(src_chips or "none")} &middot; '
        f'Joined to local sessions: {joined}/{prs_rev} PRs (by branch or commit SHA). '
        f'CI-pending / offline-sandbox P1s are separated from real escaped defects so skill fixes target real misses.</div>'
    )
    return (
        '<div class="chart-card" id="section-review-escapes" style="overflow-x:auto">'
        '<div class="chart-title">Post-Push PR Review Catches &amp; Escape Rate</div>'
        f'<div class="stats-row" style="margin-bottom:12px">{tiles_html}</div>'
        f'{cat_tbl}{sk_tbl}{meta_note}</div>'
    )
