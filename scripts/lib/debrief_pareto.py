#!/usr/bin/env python3
"""Multi-objective Pareto front optimizer and offline inline-SVG plot for /debrief."""
import html
import math

from debrief_common import safe_float, safe_int

_REVIEW_DIAGNOSTIC_SKILLS = frozenset({"code-review", "diagnostic-rigor", "resolve-review-threads"})


def _dominates(a, b, specs):
    """Return True iff point `a` strictly Pareto-dominates `b` under noise-aware specs.

    Each spec is (key, direction, noise_key_or_None). Missing values on an axis
    make that axis neutral (never allow a missing value to fabricate dominance).
    """
    strictly_better = False
    comparable_axes = 0
    for key, direction, noise_key in specs:
        va, vb = a.get(key), b.get(key)
        if va is None or vb is None:
            continue
        comparable_axes += 1
        va, vb = float(va), float(vb)
        margin = 1e-9
        if noise_key:
            na = safe_float(a.get(noise_key), 0.0)
            nb = safe_float(b.get(noise_key), 0.0)
            margin = max(margin, na, nb)
        if direction == "max":
            if va < vb - 1e-9:
                return False
            if va - vb > margin:
                strictly_better = True
        else:
            if va > vb + 1e-9:
                return False
            if vb - va > margin:
                strictly_better = True
    return comparable_axes > 0 and strictly_better


def _partition_pareto(items, specs, id_key):
    """Split items into non-dominated frontier and dominated list with dominated_by IDs."""
    dom_by = {it[id_key]: [] for it in items}
    for i, b in enumerate(items):
        for j, a in enumerate(items):
            if i == j:
                continue
            if _dominates(a, b, specs):
                dom_by[b[id_key]].append(a[id_key])
    frontier = []
    dominated = []
    for it in items:
        cid = it[id_key]
        row = dict(it)
        if dom_by[cid]:
            row["pareto_status"] = "dominated"
            row["dominated_by"] = sorted(set(dom_by[cid]))
            dominated.append(row)
        else:
            row["pareto_status"] = "frontier"
            row["dominated_by"] = []
            frontier.append(row)
    return frontier, dominated


def _find_knee(frontier, specs, id_key):
    """Return the frontier item closest in normalized Euclidean distance to the utopia point."""
    if not frontier:
        return None
    if len(frontier) == 1:
        return frontier[0][id_key]
    bounds = {}
    for key, direction, _ in specs:
        vals = [float(it[key]) for it in frontier if it.get(key) is not None]
        if vals:
            bounds[key] = (min(vals), max(vals), direction)
    best_id = None
    best_dist = float("inf")
    for it in frontier:
        sq = 0.0
        dims = 0
        for key, (lo, hi, direction) in bounds.items():
            v = it.get(key)
            if v is None:
                continue
            span = hi - lo
            norm = 1.0 if span <= 1e-12 else ((float(v) - lo) / span if direction == "max" else (hi - float(v)) / span)
            sq += (1.0 - norm) ** 2
            dims += 1
        dist = math.sqrt(sq / dims) if dims else float("inf")
        if dist < best_dist - 1e-12 or (abs(dist - best_dist) <= 1e-12 and str(it[id_key]) < str(best_id or "~")):
            best_dist = dist
            best_id = it[id_key]
    return best_id


def _hypervolume_2d(points):
    """Exact 2D hypervolume over (x in [0,1], y in [0,1]) relative to reference (0, 0)."""
    clean = [(max(0.0, min(1.0, float(x))), max(0.0, min(1.0, float(y)))) for x, y in points if x is not None and y is not None]
    if not clean:
        return None
    # Keep non-dominated envelope sorted by x ascending, y descending
    clean.sort(key=lambda p: (-p[0], -p[1]))
    env = []
    max_y = -1.0
    for x, y in clean:
        if y > max_y:
            env.append((x, y))
            max_y = y
    env.reverse()  # x ascending, y descending
    area = 0.0
    prev_x = 0.0
    for x, y in env:
        if x > prev_x:
            area += (x - prev_x) * y
            prev_x = x
    return round(area, 4)


def _compute_version_fronts(eval_trends):
    """Compute per-(skill, harness) Pareto fronts over skill_sha versions."""
    per_skill = (eval_trends or {}).get("per_skill") or {}
    specs = (
        ("quality", "max", "noise_band"),
        ("cost_delta", "min", None),
        ("friction_delta", "min", None),
    )
    fronts = []
    regressions = []
    hvs = []
    for skill, rows in sorted(per_skill.items()):
        if not isinstance(rows, list):
            continue
        by_harness = {}
        for r in rows:
            if isinstance(r, dict):
                by_harness.setdefault(str(r.get("harness") or "unknown"), []).append(r)
        for harness, hrows in sorted(by_harness.items()):
            if len(hrows) < 2:
                continue
            pts = []
            for r in hrows:
                q = r.get("win_rate") if r.get("win_rate") is not None else r.get("pass_rate_with")
                cin, cout = r.get("cost_delta_in"), r.get("cost_delta_out")
                cost = (float(cin or 0) + float(cout or 0)) if (cin is not None or cout is not None) else None
                fric = r.get("tool_errors_delta") if r.get("tool_errors_delta") is not None else r.get("latency_delta_s")
                pts.append({
                    "sha": str(r.get("sha_short") or r.get("skill_sha") or "unversioned"),
                    "skill_sha": r.get("skill_sha"),
                    "last_recorded_at": r.get("last_recorded_at") or "",
                    "quality": round(float(q), 4) if q is not None else None,
                    "noise_band": safe_float(r.get("noise_band"), 0.0),
                    "cost_delta": round(cost, 1) if cost is not None else None,
                    "friction_delta": round(float(fric), 4) if fric is not None else None,
                })
            frontier, dominated = _partition_pareto(pts, specs, "sha")
            knee_sha = _find_knee(frontier, specs, "sha")
            for f in frontier:
                f["is_knee"] = f["sha"] == knee_sha

            # Hypervolume over (quality, efficiency_from_cost)
            hv_pts = []
            for f in frontier:
                if f["quality"] is not None:
                    eff = 1.0 / (1.0 + max(0.0, float(f["cost_delta"] or 0.0)) / 5000.0)
                    hv_pts.append((eff, f["quality"]))
            hv = _hypervolume_2d(hv_pts)
            if hv is not None:
                hvs.append(hv)

            # Newest version (last in eval_trends chronological list) regressed?
            head_pt = pts[-1]
            head_dom = next((d for d in dominated if d["sha"] == head_pt["sha"]), None)
            if head_dom:
                regressions.append({
                    "skill": skill,
                    "harness": harness,
                    "head_sha": head_pt["sha"],
                    "dominated_by": head_dom["dominated_by"],
                    "head_quality": head_pt["quality"],
                    "head_cost_delta": head_pt["cost_delta"],
                })
            fronts.append({
                "skill": skill,
                "harness": harness,
                "versions_count": len(pts),
                "frontier": frontier,
                "dominated": dominated,
                "knee_sha": knee_sha,
                "hypervolume": hv,
                "head_sha": head_pt["sha"],
                "head_regressed": bool(head_dom),
            })
    return fronts, regressions, (round(sum(hvs) / len(hvs), 4) if hvs else None)


def _compute_portfolio_fronts(skill_table):
    """Compute stratified Skill Portfolio Pareto fronts (quality vs overhead/load vs friction/load)."""
    strata = {}
    for row in skill_table or []:
        sk = row.get("skill")
        loads = safe_int(row.get("mined_loads"), 0)
        if not sk or loads < 5:
            continue
        stratum = "review_diagnostic" if sk in _REVIEW_DIAGNOSTIC_SKILLS else "execution"
        tax = safe_float(row.get("estimated_context_tax_tokens"), 0.0)
        ov_per_load = round(tax / loads, 1)
        err_rate = safe_float(row.get("error_rate_per_session"), 0.0)
        red_rate = safe_int(row.get("redirect_interjections"), 0) / float(loads)
        forced = safe_float(row.get("forced_pct"), 0.0) / 100.0 if (row.get("forced_pct") is not None and safe_int(row.get("hook_loads"), 0) >= 3) else 0.0
        fric = round(err_rate + red_rate + forced, 4)

        if row.get("eval_win_rate") is not None:
            q_src = "eval_win_rate"
            eff = round(safe_float(row.get("eval_win_rate"), 0.0), 4)
            noise = safe_float(row.get("eval_noise_band"), 0.0)
        elif row.get("trigger_f1") is not None:
            q_src = "trigger_f1"
            eff = round(safe_float(row.get("trigger_f1"), 0.0), 4)
            noise = 0.0
        else:
            q_src = "operational"
            eff = round(1.0 / (1.0 + err_rate + red_rate), 4)
            noise = 0.0

        strata.setdefault((stratum, q_src), []).append({
            "skill": sk,
            "loads": loads,
            "effectiveness": eff,
            "noise_band": noise,
            "overhead_per_load": ov_per_load,
            "friction_per_load": fric,
            "stratum": stratum,
            "quality_source": q_src,
        })

    specs = (
        ("effectiveness", "max", "noise_band"),
        ("overhead_per_load", "min", None),
        ("friction_per_load", "min", None),
    )
    out = []
    all_dominated = []
    for (stratum, q_src), items in sorted(strata.items()):
        if len(items) < 2:
            continue
        frontier, dominated = _partition_pareto(items, specs, "skill")
        knee_skill = _find_knee(frontier, specs, "skill")
        for f in frontier:
            f["is_knee"] = f["skill"] == knee_skill
        hv = _hypervolume_2d([
            (1.0 / (1.0 + f["overhead_per_load"] / 5_000_000.0), f["effectiveness"])
            for f in frontier
        ])
        out.append({
            "stratum": stratum,
            "quality_source": q_src,
            "skills_count": len(items),
            "frontier": frontier,
            "dominated": dominated,
            "knee_skill": knee_skill,
            "hypervolume": hv,
        })
        all_dominated.extend(dominated)
    return out, all_dominated


def compute_pareto_analysis(skill_table, eval_trends=None):
    """Compute both Skill Version and Skill Portfolio Pareto fronts."""
    v_fronts, v_regs, mean_vhv = _compute_version_fronts(eval_trends)
    p_fronts, p_dom = _compute_portfolio_fronts(skill_table)
    p_hvs = [f["hypervolume"] for f in p_fronts if f.get("hypervolume") is not None]
    mean_phv = round(sum(p_hvs) / len(p_hvs), 4) if p_hvs else None
    return {
        "version_fronts": v_fronts,
        "head_regressions": v_regs,
        "portfolio_fronts": p_fronts,
        "portfolio_dominated": p_dom,
        "summary": {
            "version_series": len(v_fronts),
            "head_regressions_count": len(v_regs),
            "portfolio_strata": len(p_fronts),
            "portfolio_dominated_count": len(p_dom),
            "mean_version_hv": mean_vhv if mean_vhv is not None else mean_phv,
            "mean_portfolio_hv": mean_phv,
        },
    }


def _e(val):
    return html.escape(str(val if val is not None else ""), quote=True)


def _fmt_ov_tick(val):
    if val <= 0:
        return "0"
    return f"{val / 1e6:.2f}M".rstrip("0").rstrip(".") if val >= 1_000_000 else (f"{val / 1e3:.0f}k" if val >= 1_000 else f"{int(round(val))}")


def _render_portfolio_svg(front):
    """Render readable offline inline SVG scatter plot (overhead/load vs effectiveness) with collision-free labels."""
    pts = list(front.get("frontier") or []) + list(front.get("dominated") or [])
    if not pts:
        return ""
    w, h, pad_l, pad_r, pad_t, pad_b = 820.0, 340.0, 58.0, 28.0, 24.0, 48.0
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    max_ov = max(max((p["overhead_per_load"] for p in pts), default=1.0) * 1.12, 1000.0)
    min_eff = max(0.0, min((p["effectiveness"] for p in pts), default=0.0) - 0.08)
    max_eff = min(1.0, max((p["effectiveness"] for p in pts), default=1.0) + 0.06)
    eff_span = max(max_eff - min_eff, 0.1)
    max_loads = max((p["loads"] for p in pts), default=1)
    sx = lambda ov: pad_l + (ov / max_ov) * pw
    sy = lambda ef: pad_t + (1.0 - (ef - min_eff) / eff_span) * ph

    svg = [f'<svg viewBox="0 0 {int(w)} {int(h)}" width="100%" role="img" aria-label="Skill Portfolio Pareto Frontier" style="max-width:{int(w)}px;height:auto;display:block;background:#fcfdff;border:1px solid #e2e8f0;border-radius:8px">']
    for step in (0.0, 0.25, 0.5, 0.75, 1.0):
        gy, val = pad_t + (1.0 - step) * ph, min_eff + step * eff_span
        gx, ov_val = pad_l + step * pw, step * max_ov
        svg.append(f'<line x1="{pad_l:.1f}" y1="{gy:.1f}" x2="{w - pad_r:.1f}" y2="{gy:.1f}" stroke="#eef2f7" stroke-width="1"/>')
        svg.append(f'<text x="{pad_l - 8:.1f}" y="{gy + 3.5:.1f}" text-anchor="end" font-size="11" fill="#64748b">{val:.2f}</text>')
        svg.append(f'<line x1="{gx:.1f}" y1="{pad_t:.1f}" x2="{gx:.1f}" y2="{h - pad_b:.1f}" stroke="#f1f5f9" stroke-width="1"/>')
        svg.append(f'<text x="{gx:.1f}" y="{h - pad_b + 16:.1f}" text-anchor="middle" font-size="11" fill="#64748b">{_e(_fmt_ov_tick(ov_val))}</text>')

    svg.append(f'<line x1="{pad_l:.1f}" y1="{pad_t:.1f}" x2="{pad_l:.1f}" y2="{h - pad_b:.1f}" stroke="#94a3b8" stroke-width="1.3"/>')
    svg.append(f'<line x1="{pad_l:.1f}" y1="{h - pad_b:.1f}" x2="{w - pad_r:.1f}" y2="{h - pad_b:.1f}" stroke="#94a3b8" stroke-width="1.3"/>')
    svg.append(f'<text x="{pad_l + pw / 2:.1f}" y="{h - 8:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="#475569">Overhead Tokens / Load (Lower is Better &larr;)</text>')
    svg.append(f'<text x="16" y="{pad_t + ph / 2:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="#475569" transform="rotate(-90 16 {pad_t + ph / 2:.1f})">Effectiveness (&uarr;)</text>')
    svg.append(f'<text x="{pad_l + 8:.1f}" y="{pad_t + 14:.1f}" font-size="10" font-weight="600" fill="#0f766e">&#9733; Ideal zone (high eff, low overhead)</text>')

    f_pts = sorted(front.get("frontier") or [], key=lambda p: (p["overhead_per_load"], -p["effectiveness"]))
    if len(f_pts) >= 2:
        poly = " ".join(f"{sx(p['overhead_per_load']):.1f},{sy(p['effectiveness']):.1f}" for p in f_pts)
        svg.append(f'<polyline points="{poly}" fill="none" stroke="#0f766e" stroke-width="2.2" stroke-dasharray="6,4"/>')

    ordered = sorted(pts, key=lambda p: (1 if p.get("pareto_status") == "frontier" else 0, 1 if p.get("is_knee") else 0, p["loads"]))
    placed_dots = []
    for p in ordered:
        cx, cy = sx(p["overhead_per_load"]), sy(p["effectiveness"])
        rad = 5.0 + 6.5 * math.sqrt(p["loads"] / float(max_loads))
        is_front, is_knee = p.get("pareto_status") == "frontier", bool(p.get("is_knee"))
        fill = "#d97706" if is_knee else ("#0f766e" if is_front else "#e11d48")
        tip = f"{p['skill']} ({p['pareto_status']}{' / KNEE' if is_knee else ''}): eff={p['effectiveness']:.2f}, overhead={p['overhead_per_load']/1e6:.2f}M/load, friction={p['friction_per_load']:.2f}, loads={p['loads']}"
        if p.get("dominated_by"):
            tip += f" | dominated by: {', '.join(p['dominated_by'][:5])}"
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{fill}" fill-opacity="0.82" stroke="#ffffff" stroke-width="1.6"><title>{_e(tip)}</title></circle>')
        placed_dots.append((p, cx, cy, rad, is_front, is_knee))

    label_order = sorted(placed_dots, key=lambda t: (0 if t[5] else (1 if t[4] else 2), -(t[0]["loads"] + (1000 if t[0]["overhead_per_load"] > max_ov * 0.6 else 0))))
    boxes = []
    for p, cx, cy, rad, is_front, is_knee in label_order:
        lbl = ("★ " if is_knee else "") + str(p["skill"])[:22]
        tw, th = max(36.0, len(lbl) * 6.3 + 6.0), 13.0
        for lx, ly, anc in (
            (cx + rad + 5, cy + 3.5, "start"), (cx - rad - 5, cy + 3.5, "end"),
            (cx + rad + 4, cy - rad - 3, "start"), (cx - rad - 4, cy - rad - 3, "end"),
            (cx + rad + 4, cy + rad + 11, "start"), (cx - rad - 4, cy + rad + 11, "end"),
            (cx, cy - rad - 5, "middle"), (cx, cy + rad + 13, "middle"),
        ):
            x0 = lx if anc == "start" else (lx - tw if anc == "end" else lx - tw / 2.0)
            x1, y0, y1 = x0 + tw, ly - th + 2.0, ly + 2.0
            if x0 < pad_l + 3 or x1 > w - pad_r - 3 or y0 < pad_t + 14 or y1 > h - pad_b - 3:
                continue
            cand_box = (x0 - 2, y0 - 2, x1 + 2, y1 + 2)
            if any(not (cand_box[2] < b[0] or cand_box[0] > b[2] or cand_box[3] < b[1] or cand_box[1] > b[3]) for b in boxes):
                continue
            boxes.append(cand_box)
            col = "#b45309" if is_knee else ("#0f766e" if is_front else "#334155")
            wt = "700" if (is_front or is_knee) else "500"
            svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-size="11" font-weight="{wt}" fill="{col}" stroke="#ffffff" stroke-width="3" paint-order="stroke">{_e(lbl)}</text>')
            break

    svg.append("</svg>")
    return "".join(svg)


def render_pareto_card(agg):
    """Render Multi-Objective Pareto Optimization HTML card (full-width scatter + compact table)."""
    pareto = agg.get("pareto")
    if not isinstance(pareto, dict):
        return ""
    p_fronts = pareto.get("portfolio_fronts") or []
    v_fronts = pareto.get("version_fronts") or []
    regs = pareto.get("head_regressions") or []
    if not p_fronts and not v_fronts:
        return ""

    parts = []
    if regs:
        reg_li = "".join(
            f'<li><strong>{_e(r["skill"])} ({_e(r["harness"])})</strong>: current HEAD <code>{_e(r["head_sha"])}</code> '
            f'is strictly Pareto-dominated by prior version(s) <code>{_e(", ".join(r["dominated_by"]))}</code> — revert or beat them.</li>'
            for r in regs
        )
        parts.append(
            '<div style="background:#fef2f2;border:1px solid #ef4444;border-radius:6px;padding:10px 12px;margin-bottom:14px;font-size:12px">'
            f'<strong style="color:#991b1b">Pareto HEAD Regression Alert ({len(regs)}):</strong><ul style="margin:4px 0 0 18px">{reg_li}</ul></div>'
        )

    if p_fronts:
        primary = max(p_fronts, key=lambda f: f.get("skills_count", 0))
        svg_html = _render_portfolio_svg(primary)
        all_dom = []
        for f in p_fronts:
            for d in f.get("dominated") or []:
                all_dom.append((f, d))
        all_dom.sort(key=lambda t: (-t[1].get("loads", 0), -t[1].get("overhead_per_load", 0.0)))
        dom_rows = []
        for f, d in all_dom[:10]:
            peers = list(d.get("dominated_by") or [])
            shown = ", ".join(peers[:3]) + (f" (+{len(peers) - 3} more)" if len(peers) > 3 else "")
            dom_rows.append(
                f'<tr><td><strong>{_e(d["skill"])}</strong></td>'
                f'<td style="font-size:11px">{_e(f["stratum"])} / {_e(f["quality_source"])}</td>'
                f'<td style="font-family:monospace">{d["effectiveness"]:.2f}</td>'
                f'<td style="font-family:monospace">{_e(_fmt_ov_tick(d["overhead_per_load"]))}</td>'
                f'<td style="font-family:monospace">{d["friction_per_load"]:.2f}</td>'
                f'<td style="font-size:12px;color:#b91c1c" title="{_e(", ".join(peers))}">{_e(shown)}</td></tr>'
            )
        more_note = (
            f'<div style="font-size:11px;color:#64748b;margin-top:6px">Showing top 10 of {len(all_dom)} strictly dominated skills by load volume. Hover any bubble or cell for full peer list.</div>'
            if len(all_dom) > 10 else ""
        )
        dom_html = (
            '<table class="skill-table" style="margin:12px 0 0;width:100%">'
            '<thead><tr><th>Dominated Skill</th><th>Stratum</th><th>Eff.</th><th>Ov/Load</th><th>Friction</th><th>Dominated By</th></tr></thead>'
            f'<tbody>{"".join(dom_rows)}</tbody></table>{more_note}'
        ) if dom_rows else '<div style="font-size:12px;color:#15803d;margin-top:8px">All active skills in this stratum sit on the Pareto frontier (zero strictly dominated skills).</div>'
        hv_txt = f"{primary['hypervolume']:.3f}" if primary.get("hypervolume") is not None else "n/a"
        parts.append(
            f'<div style="font-size:12px;color:#475569;margin-bottom:8px">'
            f'Stratum: <strong>{_e(primary["stratum"])}</strong> ({_e(primary["quality_source"])}) &middot; '
            f'Knee: <strong>{_e(primary.get("knee_skill") or "n/a")}</strong> &middot; Hypervolume: <code>{_e(hv_txt)}</code> '
            f'&nbsp;|&nbsp; <span style="color:#0f766e">&#9679; Frontier</span> &nbsp;<span style="color:#d97706">&#9733; Knee</span> &nbsp;<span style="color:#e11d48">&#9679; Dominated</span> '
            f'&nbsp;&middot;&nbsp; <span style="color:#64748b">Bubble size = loads · Hover any dot for full metrics</span></div>'
            f'<div style="margin-bottom:4px">{svg_html}</div>'
            f'<div>{dom_html}</div>'
        )

    if v_fronts:
        v_rows = []
        for vf in v_fronts:
            f_shas = ", ".join(f"{x['sha']}{'*' if x.get('is_knee') else ''}" for x in vf["frontier"])
            d_shas = ", ".join(x["sha"] for x in vf["dominated"]) or "none"
            st = '<span style="color:#b91c1c;font-weight:700">HEAD REGRESSED</span>' if vf["head_regressed"] else '<span style="color:#15803d;font-weight:700">HEAD ON FRONTIER</span>'
            hv_s = f"{vf['hypervolume']:.3f}" if vf.get("hypervolume") is not None else "n/a"
            v_rows.append(
                f'<tr><td><strong>{_e(vf["skill"])}</strong> ({_e(vf["harness"])})</td>'
                f'<td>{st}</td><td><code>{_e(f_shas)}</code></td><td><code>{_e(d_shas)}</code></td><td style="font-family:monospace">{_e(hv_s)}</td></tr>'
            )
        parts.append(
            '<h4 style="margin:14px 0 6px;font-size:13px;color:#334155">Per-Skill Version Pareto Fronts (* = Knee)</h4>'
            '<table class="skill-table" style="width:100%">'
            '<thead><tr><th>Skill (Harness)</th><th>HEAD Status</th><th>Frontier SHAs</th><th>Dominated SHAs</th><th>HV</th></tr></thead>'
            f'<tbody>{"".join(v_rows)}</tbody></table>'
        )

    return (
        '<div class="chart-card" id="section-pareto" style="margin:20px 0">'
        '<div class="chart-title">Multi-Objective Pareto Front (Quality vs. Overhead vs. Friction)</div>'
        + "".join(parts)
        + "</div>"
    )
