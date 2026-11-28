#!/usr/bin/env python3
"""Deterministic offline HTML renderer for /debrief v2 (aggregate + synthesis JSON)."""
import argparse
import datetime
import html
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from debrief_common import default_reports_dir, read_json, safe_float, safe_int  # noqa: E402
from debrief_coaching import render_coaching_playbook_card, render_session_health_section  # noqa: E402
from debrief_html_assets import REPORT_CSS, REPORT_JS  # noqa: E402
from debrief_insights import (  # noqa: E402
    render_interjection_reasons_card,
    render_repo_activity_section,
    render_skill_recommendations_card,
)
from debrief_changepoints import render_changepoint_card  # noqa: E402
from debrief_diff import build_snapshot, save_snapshot  # noqa: E402
from debrief_pareto import render_pareto_card  # noqa: E402
from debrief_radar import render_diff_accountability_card, render_radar_card  # noqa: E402
from debrief_render_skills import render_friction_cards, render_harness_skill_section  # noqa: E402
from debrief_render_trends import render_skill_trends_card  # noqa: E402
from debrief_scope import render_single_session_banner  # noqa: E402
from debrief_summary import format_terminal_summary  # noqa: E402
from debrief_triggers import render_trigger_card  # noqa: E402


def _e(val):
    return html.escape(str(val if val is not None else ""), quote=True)


def _safe_js_json(obj):
    raw = json.dumps(obj, sort_keys=True)
    return raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def _label(key):
    """Humanize a data key without Title Casing every word: 'ship_a_fix' -> 'Ship a fix'."""
    raw = str(key or "").replace("_", " ").strip()
    return raw[:1].upper() + raw[1:] if raw else raw


def _render_bars(data, color, title_case=True, left_col="", right_col=""):
    if not data or not any(v for v in data.values()):
        return '<div class="card-hint">No observations in this window.</div>'
    mx = max(data.values()) or 1
    out = []
    if left_col or right_col:
        out.append(f'<div class="bar-head"><span>{_e(left_col)}</span><span>{_e(right_col)}</span></div>')
    for k, v in data.items():
        lbl = _label(k) if title_case else str(k)
        pct = (float(v) / float(mx)) * 100.0
        val_txt = f"{v:,}" if isinstance(v, int) else str(v)
        out.append(
            f'<div class="bar-row">'
            f'<div class="bar-label" title="{_e(lbl)}">{_e(lbl)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>'
            f'<div class="bar-value">{_e(val_txt)}</div></div>'
        )
    return "\n".join(out)


def _render_chart_card(title, data, color, title_case=True, footer="", left_col="", right_col="", hint=""):
    hint_html = (
        f'<details class="note"><summary>How to read</summary><p>{_e(hint)}</p></details>'
        if hint else ""
    )
    foot = f'<p class="chart-foot">{footer}</p>' if footer else ""
    return (
        '<div class="chart-card">'
        f'<div class="chart-title">{_e(title)}</div>'
        f'{_render_bars(data, color, title_case=title_case, left_col=left_col, right_col=right_col)}{foot}{hint_html}</div>'
    )


def _render_rules(items):
    if not items:
        return ""
    rows = []
    for i, item in enumerate(items):
        code = str(item.get("snippet") or item.get("code") or "")
        target = str(item.get("target") or "AGENTS.md")
        why = str(item.get("why") or "")
        payload = f"Add to {target}:\n\n{code}"
        rows.append(
            f'<div class="rule-item">'
            f'<input type="checkbox" id="rule-{i}" class="cmd-checkbox" checked data-text="{_e(payload)}">'
            f'<code class="cmd-code">{_e(code)}</code>'
            f'<button class="copy-btn" onclick="copyRuleItem({i})">Copy</button>'
            f'<div class="cmd-why"><strong>{_e(target)}:</strong> {_e(why)}</div></div>'
        )
    return (
        '<div class="rules-section">'
        '<h3>Suggested AGENTS.md, Role &amp; Hook Additions</h3>'
        '<div class="rules-actions"><button class="copy-all-btn" onclick="copyAllCheckedRules()">Copy All Checked</button></div>'
        + "\n".join(rows)
        + "</div>"
    )


def _render_features(items):
    if not items:
        return ""
    cards = []
    for item in items:
        ex = str(item.get("example") or "")
        ex_html = (
            f'<div class="copyable-prompt-row"><code class="copyable-prompt">{_e(ex)}</code>'
            f'<button class="copy-btn" onclick="copyText(this)">Copy</button></div>'
        ) if ex else ""
        cards.append(
            f'<div class="feature-card">'
            f'<div class="feature-title">{_e(item.get("title"))}</div>'
            f'<div class="feature-oneliner">{_e(item.get("oneliner"))}</div>'
            f'<div class="feature-why"><strong>Why for you:</strong> {_e(item.get("why"))}</div>'
            f'{ex_html}</div>'
        )
    return '<div class="features-section">' + "\n".join(cards) + "</div>"


def _render_patterns(items):
    if not items:
        return ""
    cards = []
    for item in items:
        pr = str(item.get("prompt") or "")
        pr_html = (
            f'<div class="prompt-label">Paste into Muse / agy / Claude:</div>'
            f'<div class="copyable-prompt-row"><code class="copyable-prompt">{_e(pr)}</code>'
            f'<button class="copy-btn" onclick="copyText(this)">Copy</button></div>'
        ) if pr else ""
        cards.append(
            f'<div class="pattern-card">'
            f'<div class="pattern-title">{_e(item.get("title"))}</div>'
            f'<div class="pattern-summary">{_e(item.get("summary"))}</div>'
            f'<div class="pattern-detail">{_e(item.get("detail"))}</div>'
            f'{pr_html}</div>'
        )
    return '<div class="patterns-section">' + "\n".join(cards) + "</div>"


def _render_horizon(items):
    if not items:
        return ""
    cards = []
    for item in items:
        pr = str(item.get("prompt") or "")
        pr_html = (
            f'<div class="prompt-label">Ready-to-paste workflow prompt:</div>'
            f'<div class="copyable-prompt-row"><code class="copyable-prompt">{_e(pr)}</code>'
            f'<button class="copy-btn" onclick="copyText(this)">Copy</button></div>'
        ) if pr else ""
        tip = str(item.get("tip") or "")
        tip_html = f'<div class="horizon-tip"><strong>Getting started:</strong> {_e(tip)}</div>' if tip else ""
        cards.append(
            f'<div class="horizon-card">'
            f'<div class="horizon-title">{_e(item.get("title"))}</div>'
            f'<div class="horizon-possible">{_e(item.get("possible"))}</div>'
            f'{tip_html}{pr_html}</div>'
        )
    return '<div class="horizon-section">' + "\n".join(cards) + "</div>"


def render_html(agg, syn):
    meta = agg.get("meta") or {}
    charts = agg.get("charts") or {}
    glance = syn.get("at_a_glance") or {}
    repos = [r for r in (meta.get("repos") or []) if not r.get("unreadable")]
    lines_added = sum(r.get("added", 0) for r in repos)
    lines_del = sum(r.get("deleted", 0) for r in repos)
    merges = sum(r.get("merges", 0) for r in repos)
    lines_str = f"+{lines_added:,}/-{lines_del:,}" if repos else "—"

    areas_html = "\n".join(
        f'<div class="project-area"><div class="area-header">'
        f'<span class="area-name">{_e(a.get("name"))}</span>'
        f'<span class="area-count">{_e(a.get("sessions_label"))}</span></div>'
        f'<div class="area-desc">{_e(a.get("description"))}</div></div>'
        for a in (syn.get("project_areas") or [])
    )
    narr_paras = "\n".join(f"<p>{_e(p)}</p>" for p in (syn.get("narrative_paragraphs") or []))
    key_ins = syn.get("key_insight") or ""
    wins_html = "\n".join(
        f'<div class="big-win"><div class="big-win-title">{_e(w.get("title"))}</div>'
        f'<div class="big-win-desc">{_e(w.get("description"))}</div></div>'
        for w in (syn.get("big_wins") or [])
    )
    fric_intro, fric_html = render_friction_cards(agg, syn)
    raw_pdist = charts.get("prompt_distribution") or {}
    pdist_labels = {"1": "1 prompt (one-shot)", "2-3": "2-3 prompts", "4-9": "4-9 prompts", "10+": "10+ prompts"}
    prompt_dist_disp = {pdist_labels.get(str(k), str(k)): v for k, v in raw_pdist.items()}
    ov = charts.get("multi_agent_overlap") or {}
    med_g = charts.get("median_response_gap_s")
    avg_g = charts.get("avg_response_gap_s")
    med_by_h = charts.get("median_response_gap_s_by_harness") or {}
    gap_rows = []
    for h in sorted(med_by_h):
        cell = f'{_e(med_by_h[h])}s' if med_by_h[h] is not None else "—"
        gap_rows.append(f'<tr><td><code>{_e(h)}</code></td><td class="num">{cell}</td></tr>')
    gap_harness_table = (
        '<div class="chart-card">'
        '<div class="chart-title">Median Response Gap by Harness</div>'
        '<table><thead><tr><th>Harness</th><th class="num">Median gap</th></tr></thead>'
        f'<tbody>{"".join(gap_rows) or "<tr><td colspan=2>No multi-turn gaps observed.</td></tr>"}</tbody></table></div>'
    )
    if med_g is not None:
        per_h = ", ".join(
            f'{h}: {med_by_h[h]}s' if med_by_h.get(h) is not None else f'{h}: —'
            for h in sorted(med_by_h)
        )
        gap_foot = (f"Median: {_e(med_g)}s &bull; Average: {_e(avg_g)}s"
                    + (f" &bull; Per harness — {_e(per_h)}" if per_h else ""))
    else:
        gap_foot = "No multi-turn gaps observed."
    ij = agg.get("interjections") or {}
    ij_rate = ij.get("follow_up_rate_pct")
    ij_bearing = safe_int(ij.get("prompt_bearing_sessions"), 0)
    ij_zero = safe_int(ij.get("zero_prompt_sessions"), 0)
    ij_foot = (
        f"{_e(ij_rate)}% of {ij_bearing} prompt-bearing sessions had follow-ups"
        f" &bull; {ij_zero} sessions mined zero prompts (rates are lower bounds)"
        if ij_rate is not None else "No prompt-bearing sessions in window."
    )
    caveats_li = "".join(f"<li>{_e(c)}</li>" for c in (agg.get("not_tracked") or []))
    raw_hours = charts.get("hour_counts_utc") if isinstance(charts.get("hour_counts_utc"), dict) else {}
    clean_hours = {str(h): safe_int(raw_hours.get(str(h)), 0) for h in range(24)}
    utc_hours_json = _safe_js_json(clean_hours)
    harnesses_lbl = ", ".join(str(x) for x in (meta.get("harnesses") or ["muse", "agy", "claude"]))
    proj_lbl = f" &middot; Project: {_e(meta['project'])}" if meta.get("project") else " &middot; All projects"
    m_prompts = safe_int(meta.get("prompts"), 0)
    m_tools = safe_int(meta.get("tool_calls"), 0)
    m_top = safe_int(meta.get("top_level_sessions"), 0)
    m_sub_total = safe_int(meta.get("total_sessions"), 0)
    session_sub = f'<span class="meta-sub"> of {m_sub_total}</span>' if m_sub_total > m_top else ""
    m_tot = safe_int(meta.get("total_sessions"), 0)
    m_fac = safe_int(meta.get("facets_analyzed"), 0)
    m_days = safe_int(meta.get("days_active"), 1)
    m_mpd = safe_float(meta.get("msgs_per_day"), 0.0)
    m_commits = safe_int(meta.get("git_commits_in_transcripts"), 0)
    m_fix = safe_int(meta.get("fixtures_excluded"), 0)
    ov_ev = safe_int(ov.get("overlap_events"), 0)
    ov_sess = safe_int(ov.get("sessions_involved"), 0)
    ov_pct = safe_int(ov.get("pct_of_messages"), 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Multi-Harness Agent Debrief ({_e(meta.get("from"))} to {_e(meta.get("to"))})</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<svg class="grain" aria-hidden="true" focusable="false">
  <filter id="grain-filter"><feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="3" stitchTiles="stitch"></feTurbulence></filter>
  <rect width="100%" height="100%" filter="url(#grain-filter)"></rect>
</svg>
<div class="container">
  <header class="masthead">
    <div class="masthead-top">
      <p class="eyebrow">Operational debrief</p>
      <div class="theme-control">
        <span class="theme-label">Theme</span>
        <button id="theme-toggle" class="theme-toggle" type="button" onclick="cycleTheme()" aria-label="Color theme: follow system">Auto</button>
      </div>
    </div>
    <h1>Multi-Harness Agent Debrief</h1>
    <p class="subtitle">{_e(meta.get("from"))} to {_e(meta.get("to"))} &middot; Harnesses: {_e(harnesses_lbl)}{proj_lbl}</p>
    <dl class="masthead-meta">
      <div><dt>Prompts</dt><dd>{m_prompts:,}</dd></div>
      <div><dt>Tool calls</dt><dd>{m_tools:,}</dd></div>
      <div><dt>Sessions</dt><dd>{m_top}{session_sub}</dd></div>
      <div><dt>Lines changed</dt><dd>{_e(lines_str)}</dd></div>
      <div><dt>{"Merges" if repos else "Commits"}</dt><dd>{merges if repos else m_commits}</dd></div>
      <div><dt>Active days</dt><dd>{m_days}d</dd></div>
    </dl>
  </header>

  <nav class="site-nav" aria-label="Report sections">
    <div class="nav-links">
      <a href="#g-summary" data-index="01">Summary</a>
      <a href="#g-health" data-index="02">Health</a>
      <a href="#g-work" data-index="03">Work</a>
      <a href="#g-flow" data-index="04">Flow</a>
      <a href="#g-skills" data-index="05">Skills</a>
      <a href="#g-coach" data-index="06">Coach</a>
      <a href="#g-next" data-index="07">Next</a>
    </div>
    <button class="nav-action" id="expand-toggle" type="button" aria-expanded="false">Expand all</button>
  </nav>

{render_single_session_banner(agg)}

  <details class="group" id="g-summary" open>
    <summary>
      <span class="group-num">01</span>
      <span class="group-title">Summary</span>
      <span class="group-hint">What the window produced, in the order it matters.</span>
    </summary>
    <div class="group-body">
      <section class="briefing" aria-label="Briefing">
        <div class="briefing-lead">
          <span class="briefing-label">What's working</span>
          <p class="briefing-statement">{_e(glance.get("working"))}</p>
          <a href="#section-wins" class="see-more">The wins &rarr;</a>
        </div>
        <div class="briefing-items">
          <div class="briefing-item">
            <span class="briefing-label">What's hindering you</span>
            <p>{_e(glance.get("hindering"))}</p>
            <a href="#section-friction" class="see-more">See the friction &rarr;</a>
          </div>
          <div class="briefing-item">
            <span class="briefing-label">Quick wins to try</span>
            <p>{_e(glance.get("quick_wins"))}</p>
            <a href="#section-coach-rules" class="see-more">See the fixes &rarr;</a>
          </div>
          <div class="briefing-item">
            <span class="briefing-label">Ambitious workflows</span>
            <p>{_e(glance.get("ambitious"))}</p>
            <a href="#section-horizon" class="see-more">See what's next &rarr;</a>
          </div>
        </div>
        <p class="briefing-note">{m_top} top-level sessions &middot; {m_fac} facets analyzed &middot; {m_days} active days</p>
      </section>
    </div>
  </details>

  <details class="group" id="g-health">
    <summary>
      <span class="group-num">02</span>
      <span class="group-title">Health</span>
      <span class="group-hint">The six-axis profile, and what moved since the last report.</span>
    </summary>
    <div class="group-body">
      {render_radar_card(agg)}
      {render_diff_accountability_card(agg)}
      {render_changepoint_card(agg)}
      {render_session_health_section(agg)}
    </div>
  </details>

  <details class="group" id="g-work">
    <summary>
      <span class="group-num">03</span>
      <span class="group-title">Work</span>
      <span class="group-hint">Where the time went, by project, repository, and language.</span>
    </summary>
    <div class="group-body">
      <h2 id="section-work">What You Work On</h2>
      <div class="project-areas">{areas_html}</div>
      {render_repo_activity_section(agg)}
      <div class="charts-row">
        {_render_chart_card("What You Wanted", charts.get("what_you_wanted"), "var(--evidence)", left_col="Goal", right_col="Sessions")}
        {_render_chart_card("Top Tools Used", charts.get("top_tools"), "var(--evidence)", title_case=False, left_col="Tool", right_col="Calls")}
      </div>
      <div class="charts-row">
        {_render_chart_card("Languages Touched", charts.get("languages"), "var(--evidence)", title_case=False, left_col="Language", right_col="File touches")}
        {_render_chart_card("Session Types", charts.get("session_types"), "var(--evidence)", left_col="Type", right_col="Sessions")}
      </div>
    </div>
  </details>

  <details class="group" id="g-flow">
    <summary>
      <span class="group-num">04</span>
      <span class="group-title">Flow</span>
      <span class="group-hint">How you steered, how fast you answered, and where the loop broke.</span>
    </summary>
    <div class="group-body">
      <h2 id="section-usage">How You Use Your Harnesses</h2>
      <div class="narrative">
        {narr_paras}
        <div class="key-insight"><span style="color:var(--muted);font-family:var(--font-mono);font-size:var(--fs-6);letter-spacing:0.08em;text-transform:uppercase">Key pattern</span><br>{_e(key_ins)}</div>
      </div>

      <div class="charts-row">
        {_render_chart_card("User Response Time Distribution", charts.get("response_time_buckets"), "var(--evidence)", title_case=False, footer=gap_foot, left_col="Time until your next reply", right_col="Replies", hint="How long you took to reply after an agent finished a turn. Fast (2s-1m) = live back-and-forth; 1-5m = reviewing output or switching agents; over 5m = async or parallel delegation. The average includes overnight pauses, so read the median for active pace.")}
        {_render_chart_card("Prompts Per Session", prompt_dist_disp, "var(--evidence)", title_case=False, footer=ij_foot, left_col="Prompts in session", right_col="Sessions", hint="How many messages you sent in a single main chat. One prompt is an autonomous one-shot, two or three is a light nudge, four or more is interactive iteration or heavy steering.")}
      </div>

      {gap_harness_table}

      {render_interjection_reasons_card(agg)}

      <div class="chart-card">
        <div class="chart-title">Multi-Agent Parallelism</div>
        <div class="overlap-stats">
          <div><div class="overlap-num">{ov_ev}</div><div class="stat-label">Overlap Events</div></div>
          <div><div class="overlap-num">{ov_sess}</div><div class="stat-label">Sessions Involved</div></div>
          <div><div class="overlap-num">{ov_pct}%</div><div class="stat-label">Of Prompts</div></div>
        </div>
        <details class="note"><summary>How to read</summary><p>Sessions overlap in wall-clock time across the harnesses in this window. Overlap is not a problem by itself; it explains fast reply gaps and split attention.</p></details>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-title chart-title-row">
            <span>Prompts by Time of Day</span>
            <select id="timezone-select">
              <option value="-8">PT (UTC-8)</option>
              <option value="-5" selected>ET (UTC-5)</option>
              <option value="0">UTC</option>
              <option value="1">CET (UTC+1)</option>
              <option value="9">Tokyo (UTC+9)</option>
            </select>
          </div>
          <div id="hour-histogram"></div>
        </div>
        {_render_chart_card("Tool Errors Encountered", charts.get("tool_error_categories"), "var(--adverse)", title_case=False, left_col="Error type", right_col="Occurrences")}
      </div>
    </div>
  </details>

  <details class="group" id="g-skills">
    <summary>
      <span class="group-num">05</span>
      <span class="group-title">Skills</span>
      <span class="group-hint">Load counts, cost, and the skills worth changing.</span>
    </summary>
    <div class="group-body">
      {render_harness_skill_section(agg)}
      {render_skill_trends_card(agg)}
      {render_trigger_card(agg)}
      {render_pareto_card(agg)}
      {render_skill_recommendations_card(agg)}
    </div>
  </details>

  <details class="group" id="g-coach">
    <summary>
      <span class="group-num">06</span>
      <span class="group-title">Coach</span>
      <span class="group-hint">What worked, what failed, and the rules that would have prevented it.</span>
    </summary>
    <div class="group-body">
      <h2 id="section-wins">Impressive Things You Did</h2>
      <p class="section-intro">{_e(syn.get("wins_intro"))}</p>
      <div class="big-wins">{wins_html}</div>
      <div class="charts-row">
        {_render_chart_card("What Helped Most", charts.get("what_helped_most"), "var(--evidence)", left_col="Factor", right_col="Sessions")}
        {_render_chart_card("Session Outcomes", charts.get("outcomes"), "var(--evidence)", left_col="Outcome", right_col="Sessions")}
      </div>

      <h2 id="section-friction">Where Things Go Wrong</h2>
      <p class="section-intro">{_e(fric_intro)}</p>
      <div class="friction-categories">{fric_html}</div>
      <div class="charts-row">
        {_render_chart_card("Primary Friction Types", charts.get("primary_friction_types"), "var(--adverse)", left_col="Friction type", right_col="Sessions")}
        {_render_chart_card("Inferred Satisfaction", charts.get("satisfaction"), "var(--evidence)", left_col="Rating", right_col="Sessions")}
      </div>

      <h2 id="section-coaching">Coaching Playbook</h2>
      {render_coaching_playbook_card(agg)}

      <h2 id="section-coach-rules">Rules, Skills &amp; Hooks to Add or Tune</h2>
      {_render_rules(syn.get("agents_md_additions"))}
      {_render_features(syn.get("features_to_try"))}
    </div>
  </details>

  <details class="group" id="g-next">
    <summary>
      <span class="group-num">07</span>
      <span class="group-title">Next</span>
      <span class="group-hint">Patterns to keep, workflows to try, and what this report cannot see.</span>
    </summary>
    <div class="group-body">
      <h2 id="section-patterns">New Ways to Use Your Harnesses</h2>
      {_render_patterns(syn.get("usage_patterns"))}

      <h2 id="section-horizon">On the Horizon</h2>
      <p class="section-intro">{_e(syn.get("horizon_intro"))}</p>
      {_render_horizon(syn.get("horizon_workflows"))}

      <div class="caveats">
        <strong>Not tracked on purpose</strong>
        <ul>{caveats_li}</ul>
        <p class="chart-foot">Fixtures excluded from the hook log: {m_fix}. Generated offline with zero external requests.</p>
      </div>
    </div>
  </details>
</div>
<script>
const rawUtcHours = {utc_hours_json};
{REPORT_JS}
</script>
</body>
</html>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="debrief-render")
    ap.add_argument("--aggregate", required=True)
    ap.add_argument("--synthesis", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--reports-dir", default="")
    ap.add_argument("--snapshot-out", default="", help="Optional extra path for the content-free report snapshot JSON")
    ap.add_argument("--no-snapshot", action="store_true", help="Skip persisting a report snapshot")
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--skills-dir", action="append", default=[])
    ap.add_argument("--json", action="store_true", help="Emit compact JSON paths instead of human-legible summary")
    args = ap.parse_args(argv)

    agg = read_json(args.aggregate)
    syn = read_json(args.synthesis)
    if not agg or not syn:
        raise SystemExit("debrief-render: both --aggregate and --synthesis must be valid JSON objects")

    doc = render_html(agg, syn)
    rdir = args.reports_dir or default_reports_dir()
    snap_path = None
    if not args.no_snapshot:
        snap = build_snapshot(agg, syn=syn, repo_paths=args.repo, skills_dirs=args.skills_dir)
        snap_path = save_snapshot(snap, reports_dir=rdir, explicit_out=args.snapshot_out)
    elif args.snapshot_out:
        snap = build_snapshot(agg, syn=syn, repo_paths=args.repo, skills_dirs=args.skills_dir)
        os.makedirs(os.path.dirname(os.path.abspath(args.snapshot_out)), exist_ok=True)
        with open(args.snapshot_out, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, sort_keys=True)
            fh.write("\n")
        snap_path = args.snapshot_out

    latest = None
    if args.out:
        out_path = args.out
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(doc)
        res = {"report": out_path}
    else:
        os.makedirs(rdir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        out_path = os.path.join(rdir, f"report-{ts}.html")
        latest = os.path.join(rdir, "report-latest.html")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(doc)
        shutil.copyfile(out_path, latest)
        res = {"report": out_path, "latest": latest}
    if snap_path:
        res["snapshot"] = snap_path
    if args.json:
        sys.stdout.write(json.dumps(res) + "\n")
    else:
        sys.stdout.write(
            format_terminal_summary(
                agg,
                syn=syn,
                report_path=out_path,
                latest_path=latest,
                snapshot_path=snap_path,
            )
        )


if __name__ == "__main__":
    main()
