#!/usr/bin/env python3
"""Human-legible terminal summary formatter for /debrief reports."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debrief_common import read_json, safe_float, safe_int

AXIS_SPEC = (
    ("quality", "Outcome Quality"),
    ("trigger", "Trigger Precision"),
    ("reliability", "Reliability"),
    ("alignment", "Goal Alignment"),
    ("efficiency", "Token Efficiency"),
    ("cache", "Cache Efficiency"),
)


def _fmt_num(n):
    v = safe_float(n, 0.0)
    if abs(v) >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f}B"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 10_000:
        return f"{v / 1_000:.1f}k"
    return f"{int(round(v)):,}"


def _axis_score(entry):
    if isinstance(entry, dict):
        return entry.get("score")
    if isinstance(entry, (int, float)):
        return float(entry)
    return None


def _fmt_pct(val):
    if val is None:
        return "n/a"
    return f"{round(safe_float(val, 0.0) * 100):3d}%"


def _fmt_delta_pct(entry):
    if isinstance(entry, dict):
        val = entry.get("delta")
    elif isinstance(entry, (int, float)):
        val = float(entry)
    else:
        val = None
    if val is None:
        return ""
    pts = round(safe_float(val, 0.0) * 100)
    sign = "+" if pts > 0 else ""
    return f" ({sign}{pts}pp)"


def _extract_cache_pct(agg):
    sh = agg.get("session_health") or {}
    cbh = sh.get("cache_by_harness") or {}
    c_hits, c_tot = 0.0, 0.0
    if isinstance(cbh, dict):
        for row in cbh.values():
            if not isinstance(row, dict):
                continue
            tin = safe_float(row.get("tokens_in"), 0.0)
            hpct = row.get("cache_hit_pct")
            if tin > 0 and hpct is not None:
                c_hits += tin * (safe_float(hpct, 0.0) / 100.0)
                c_tot += tin
    if c_tot <= 0:
        totals = (agg.get("skill_costs") or {}).get("totals") or {}
        tin = safe_float(totals.get("tokens_in"), 0.0)
        cr = safe_float(totals.get("tokens_cache_read"), 0.0)
        if tin > 0 and cr > 0:
            c_hits, c_tot = min(cr, tin), tin
    if c_tot <= 0:
        return None
    return min(1.0, max(0.0, c_hits / c_tot))


def format_terminal_summary(agg, syn=None, report_path=None, latest_path=None, snapshot_path=None):
    """Build a concise, scannable plain-text summary of a debrief report."""
    agg = agg if isinstance(agg, dict) else {}
    syn = syn if isinstance(syn, dict) else {}
    meta = agg.get("meta") or {}
    by_h = agg.get("by_harness") or {}
    diff = agg.get("diff_from_prev") or {}

    since = str(meta.get("since") or "all-time")
    gen = str(meta.get("generated_at") or "")[:10]
    scope = meta.get("scope") or {}
    scope_lbl = scope.get("label") or (f"since {since}" if since else "all-time")
    header_span = f"{since} -> {gen}" if since and gen and since != "all-time" else scope_lbl

    lines = [
        "=" * 72,
        f"DEBRIEF SUMMARY  ({header_span})",
        "=" * 72,
    ]
    if report_path:
        lines.append(f"  Report   : {report_path}")
    if latest_path and latest_path != report_path:
        lines.append(f"  Latest   : {latest_path}")
    if snapshot_path:
        lines.append(f"  Snapshot : {snapshot_path}")

    total_s = safe_int(meta.get("total_sessions"), 0)
    top_s = safe_int(meta.get("top_level_sessions"), total_s)
    facets = safe_int(meta.get("facets_analyzed"), 0)
    days_active = safe_int(meta.get("days_active"), 0)
    prompts = sum(safe_int(v.get("prompts"), 0) for v in by_h.values() if isinstance(v, dict))
    tools = sum(safe_int(v.get("tool_calls"), 0) for v in by_h.values() if isinstance(v, dict))
    errs = sum(safe_int(v.get("errors"), 0) for v in by_h.values() if isinstance(v, dict))
    h_parts = [
        f"{h}={safe_int(v.get('sessions'), 0)}"
        for h, v in sorted(by_h.items(), key=lambda kv: -safe_int((kv[1] or {}).get("sessions"), 0))
        if isinstance(v, dict) and safe_int(v.get("sessions"), 0) > 0
    ]
    cache_pct = _extract_cache_pct(agg)
    cache_str = f" | cache hit {cache_pct * 100:.1f}%" if cache_pct is not None else ""

    lines.append("")
    lines.append("COVERAGE")
    lines.append(
        f"  Sessions : {total_s:,} total ({top_s:,} top-level) | {facets:,} facets | {days_active} active day(s)"
    )
    if h_parts:
        lines.append(f"  Harnesses: {', '.join(h_parts)}")
    lines.append(
        f"  Activity : {_fmt_num(prompts)} prompts | {_fmt_num(tools)} tool calls | {_fmt_num(errs)} errors{cache_str}"
    )

    radar = agg.get("radar_profile") or {}
    axes = radar.get("axes") if isinstance(radar.get("axes"), dict) else {}
    rd_obj = diff.get("radar_diff") or {}
    rdiff = rd_obj.get("axes") if isinstance(rd_obj.get("axes"), dict) else (rd_obj.get("deltas") or {})
    present_axes = [(k, lbl) for k, lbl in AXIS_SPEC if _axis_score(axes.get(k)) is not None]
    if present_axes:
        lines.append("")
        lines.append("TRAJECTORY RADAR (0-100%, higher = better)")
        for i in range(0, len(present_axes), 2):
            pair = present_axes[i:i + 2]
            cells = []
            for k, lbl in pair:
                val = _fmt_pct(_axis_score(axes.get(k)))
                d_str = _fmt_delta_pct(rdiff.get(k)) if k in rdiff else ""
                cells.append(f"{lbl:<18}: {val}{d_str:<9}")
            lines.append("  " + " | ".join(cells).rstrip())

    cp = agg.get("changepoints") or {}
    cp_sum = cp.get("summary") or {}
    edited_n = safe_int(cp_sum.get("skills_edited_in_window"), 0)
    hooks_cp = cp.get("hooks") or {}
    if edited_n > 0 or (hooks_cp and hooks_cp.get("verdict")):
        lines.append("")
        lines.append("POST-EDIT IMPACT (Git Change-Points)")
        if edited_n > 0:
            lines.append(
                f"  Skills   : {edited_n} edited in window "
                f"({safe_int(cp_sum.get('improved'), 0)} improved, "
                f"{safe_int(cp_sum.get('awaiting_data'), 0)} awaiting data, "
                f"{safe_int(cp_sum.get('unchanged'), 0)} unchanged, "
                f"{safe_int(cp_sum.get('regressed'), 0)} regressed)"
            )
            for sk, info in sorted((cp.get("skills") or {}).items()):
                verdict = (info or {}).get("verdict")
                if verdict in ("improved", "regressed"):
                    pre_e = (info.get("pre") or {}).get("errors_per_session")
                    post_e = (info.get("post") or {}).get("errors_per_session")
                    sha = info.get("edited_sha") or ""
                    if pre_e is not None and post_e is not None:
                        lines.append(f"    - {sk} ({sha}) [{verdict}]: {pre_e:.2f} -> {post_e:.2f} errors/session")
                    else:
                        lines.append(f"    - {sk} ({sha}) [{verdict}]")
        if hooks_cp and hooks_cp.get("verdict"):
            lines.append(f"  Hooks    : {hooks_cp.get('edited_sha') or 'hooks/'} — {hooks_cp.get('verdict')}")

    pf = agg.get("pareto") or {}
    pf_sum = pf.get("summary") or {}
    acct_counts = diff.get("accountability_counts") or {}
    if pf_sum or acct_counts:
        lines.append("")
        lines.append("PARETO FRONT & DIFF ACCOUNTABILITY")
        if pf_sum:
            hv = pf_sum.get("mean_portfolio_hv")
            hv_s = f"{safe_float(hv, 0.0):.4f}" if hv is not None else "n/a"
            dhv = (diff.get("pareto_hv") or {}).get("delta")
            dhv_s = f" (Δ {dhv:+.4f})" if isinstance(dhv, (int, float)) else ""
            lines.append(
                f"  Pareto    : {safe_int(pf_sum.get('portfolio_strata'), 0)} strata | "
                f"{safe_int(pf_sum.get('portfolio_dominated_count'), 0)} dominated | "
                f"HEAD regressions: {safe_int(pf_sum.get('head_regressions_count'), 0)} | "
                f"HV={hv_s}{dhv_s}"
            )
        if acct_counts:
            lines.append(
                f"  Prior Recs: {safe_int(acct_counts.get('implemented_verified'), 0)} verified | "
                f"{safe_int(acct_counts.get('implemented_ineffective'), 0)} ineffective | "
                f"{safe_int(acct_counts.get('implemented_pending_data'), 0)} pending data | "
                f"{safe_int(acct_counts.get('not_done'), 0)} not done"
            )

    key_insight = str(syn.get("key_insight") or "").strip()
    if not key_insight:
        aag = syn.get("at_a_glance") or {}
        if isinstance(aag, dict):
            key_insight = str(aag.get("working") or "").strip()
    if key_insight:
        lines.append("")
        lines.append("KEY INSIGHT")
        lines.append(f"  {key_insight}")

    recs = agg.get("skill_recommendations") or []
    if recs:
        lines.append("")
        lines.append(f"TOP RECOMMENDED ACTIONS ({min(5, len(recs))} of {len(recs)})")
        for idx, rec in enumerate(recs[:5], 1):
            act = str(rec.get("action") or "action").upper()
            tgt = str(rec.get("target") or "")
            reason = str(rec.get("reason") or "").strip()
            if len(reason) > 110:
                reason = reason[:107].rstrip() + "..."
            lines.append(f"  {idx}. [{act}] {tgt} — {reason}")

    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="debrief-summary")
    ap.add_argument("--aggregate", required=True, help="Path to aggregate.json")
    ap.add_argument("--synthesis", default="", help="Optional path to synthesis.json")
    ap.add_argument("--report", default="", help="Optional path to rendered HTML report")
    ap.add_argument("--latest", default="", help="Optional path to report-latest.html")
    ap.add_argument("--snapshot", default="", help="Optional path to saved snapshot JSON")
    args = ap.parse_args(argv)
    agg = read_json(args.aggregate)
    if not agg:
        raise SystemExit(f"debrief-summary: invalid or missing aggregate JSON: {args.aggregate}")
    syn = read_json(args.synthesis) if args.synthesis else {}
    sys.stdout.write(
        format_terminal_summary(
            agg,
            syn=syn,
            report_path=args.report or None,
            latest_path=args.latest or None,
            snapshot_path=args.snapshot or None,
        )
    )


if __name__ == "__main__":
    main()
