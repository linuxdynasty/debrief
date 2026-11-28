#!/usr/bin/env python3
"""Deterministic synthetic debrief fixture for design work and tests.

The fixture exists for three reasons:

1. Design iteration must not read a real person's sessions. Every number here is
   invented, and no session id, path, model name, or skill name comes from a real
   transcript.
2. A design problem needs a design-sized document. The real window that produced
   the current preview held three sessions and no repositories, which hid half the
   report: no repo table, no papercuts, no evals, no diff overlay, and a scorecard
   with two populated rows.
3. Maintainers need the same document on every machine. The value of every field
   is derived from a fixed table below, so two runs produce byte-identical JSON.

Usage:
    python3 debrief_demo_fixture.py --out-dir scripts/fixtures
    python3 debrief_demo_fixture.py --html /tmp/demo.html

The world is fictional: the *Atlas Relay* project family, four repositories, three
harnesses, eighteen skills, sixteen days of activity.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from debrief_common import safe_int  # noqa: E402
from debrief_coaching import build_coaching_playbook, session_health_stats  # noqa: E402
from debrief_pareto import compute_pareto_analysis  # noqa: E402
from debrief_radar import compute_radar_profile  # noqa: E402




def _pct(part, whole):
    return round(100.0 * part / float(whole), 1) if whole else 0.0


def _derive_repositories(metas):
    """Repository table straight from the session population."""
    rows = {}
    for m in metas:
        r = rows.setdefault(m["project"], {
            "repo": m["project"], "main_sessions": 0, "total_sessions": 0,
            "unattributed_sessions": 0, "prompts": 0, "tool_calls": 0,
            "errors": 0, "interjections": 0, "tokens_total": 0, "skills": {},
            "reasons": {},
        })
        errs = sum(safe_int(v) for v in (m.get("error_categories") or {}).values())
        r["main_sessions"] += 1
        r["total_sessions"] += 1
        r["prompts"] += safe_int(m.get("prompts"))
        r["tool_calls"] += safe_int(m.get("tool_calls"))
        r["errors"] += errs
        r["tokens_total"] += safe_int(m.get("tokens_in")) + safe_int(m.get("tokens_out"))
        for sk in m.get("skill_loads") or []:
            r["skills"][sk] = r["skills"].get(sk, 0) + 1
    out = []
    for r in sorted(rows.values(), key=lambda x: (-x["main_sessions"], x["repo"])):
        total_prompts = sum(x["prompts"] for x in rows.values()) or 1
        share = r["prompts"] / float(total_prompts)
        reasons = {k: int(round(v * share * 2.2)) for k, v in INTERJECTIONS.items()}
        r["interjections"] = sum(reasons.values())
        r["top_skills"] = [k for k, _ in sorted(r["skills"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
        r["interjection_reasons"] = reasons
        r["top_interjection_reason"] = max(reasons.items(), key=lambda kv: kv[1])[0]
        r.pop("skills")
        r.pop("reasons")
        out.append(r)
    return out


def _derive_by_harness(metas):
    rows = {}
    for m in metas:
        h = rows.setdefault(m["harness"], {"sessions": 0, "facets": 0, "prompts": 0, "tool_calls": 0, "errors": 0, "top_sessions": 0})
        h["sessions"] += 1
        h["top_sessions"] += 1
        h["facets"] += 1
        h["prompts"] += safe_int(m.get("prompts"))
        h["tool_calls"] += safe_int(m.get("tool_calls"))
        h["errors"] += sum(safe_int(v) for v in (m.get("error_categories") or {}).values())
    return {k: rows[k] for k in sorted(rows)}



# --- The fictional world -------------------------------------------------------

FROM_DATE = "2026-02-02"
TO_DATE = "2026-02-16"
HARNESSES = ("muse", "agy", "claude")
REPOS = ("atlas-relay", "atlas-relay-docs", "quarry-cli", "signal-desk")
PROJECTS = ("atlas-relay", "quarry-cli", "signal-desk")

# skill -> (sessions used, hook loads, nudged, tokens total, overhead, gap s,
#           session len min, errors, papercuts open, fixed, win rate, noise band)
SKILLS = {
    "map-the-surface":      (11, 9, 2, 4_820_000, 12_400, 74, 41, 6, 1, 2, 0.62, 0.11),
    "split-the-work":       (10, 8, 1, 4_140_000, 18_900, 61, 52, 9, 0, 3, 0.71, 0.09),
    "guard-the-contract":   (9, 7, 0, 3_760_000, 21_500, 88, 47, 4, 2, 1, 0.58, 0.12),
    "prove-the-path":       (9, 9, 3, 3_120_000, 7_800, 52, 33, 12, 3, 1, 0.66, 0.10),
    "trim-the-noise":       (8, 6, 2, 2_940_000, 34_200, 95, 58, 5, 0, 0, 0.49, 0.13),
    "seed-the-fixture":     (7, 7, 1, 2_610_000, 9_600, 68, 29, 3, 1, 1, 0.74, 0.08),
    "trace-the-regression": (7, 5, 2, 2_480_000, 15_100, 112, 63, 14, 2, 0, 0.44, 0.14),
    "lock-the-interface":   (6, 6, 0, 2_150_000, 11_300, 57, 36, 2, 0, 2, 0.69, 0.10),
    "ship-the-slice":       (6, 4, 1, 1_980_000, 8_200, 81, 44, 7, 1, 0, 0.53, 0.11),
    "draft-the-note":       (5, 4, 0, 1_640_000, 6_400, 134, 22, 1, 0, 1, 0.61, 0.12),
    "stage-the-env":        (5, 5, 2, 1_520_000, 13_900, 76, 31, 11, 2, 0, 0.47, 0.13),
    "watch-the-drift":      (4, 3, 1, 1_280_000, 10_700, 118, 55, 6, 0, 0, 0.51, 0.12),
    "name-the-boundary":    (4, 4, 0, 1_140_000, 5_900, 64, 27, 2, 0, 1, 0.72, 0.09),
    "break-the-cycle":      (3, 2, 1, 940_000, 16_800, 143, 71, 9, 1, 0, 0.41, 0.15),
    "score-the-run":        (3, 3, 0, 810_000, 4_700, 58, 24, 1, 0, 0, 0.67, 0.11),
    "close-the-loop":       (2, 1, 0, 520_000, 3_600, 91, 19, 0, 0, 0, 0.59, 0.12),
    "read-the-signal":      (2, 2, 1, 460_000, 8_900, 103, 38, 4, 0, 0, 0.46, 0.14),
    "mark-the-gap":         (1, 1, 0, 210_000, 2_800, 47, 14, 0, 0, 0, None, None),
}

PROMPT_DISTRIBUTION = {"1": 14, "2-3": 21, "4-9": 17, "10+": 6}
RESPONSE_BUCKETS = {"2-10s": 19, "10-30s": 16, "30s-1m": 13, "1-2m": 18, "2-5m": 15, "5-15m": 7, ">15m": 12}
INTERJECTIONS = {
    "approval": 41,
    "clarification": 33,
    "thought_process": 19,
    "redirect_goal": 14,
    "debugging": 11,
    "new_scope": 7,
}
TOOL_ERRORS = {
    "Command Failed": 22,
    "Edit Failed": 9,
    "File Not Found": 12,
    "Permission/Sandbox": 5,
    "Timeout": 4,
    "Hook Blocked": 6,
}
SESSION_TYPES = {"implementation": 31, "debugging": 12, "refactor": 9, "review": 6}
OUTCOMES = {"fully_achieved": 26, "mostly_achieved": 14, "partially_achieved": 8, "not_achieved": 3}
WHAT_YOU_WANTED = {"ship a fix": 24, "understand the code": 17, "explore options": 9}
WHAT_HELPED = {"clear task statement": 28, "small diffs": 19, "tests first": 12}
LANGUAGES = {"Python": 96, "TypeScript": 41, "Markdown": 33, "Shell": 18}
TOP_TOOLS = {"bash": 611, "read": 384, "edit": 219, "write": 96, "grep": 78, "search_skills": 41}
HOURS = {str(h): n for h, n in zip(
    range(24),
    (2, 1, 0, 0, 0, 1, 3, 6, 14, 22, 19, 15, 11, 24, 27, 21, 16, 12, 9, 7, 5, 4, 3, 2),
)}
FRICTION_TYPES = {"wrong_approach": 9, "tool_failure": 8, "missing_path_probe": 6, "context_loss": 4}
SATISFACTION = {"satisfied": 33, "neutral": 11, "frustrated": 7}
MODELS = {"atlas-large": 38, "atlas-mini": 22, "quarry-flash": 17, "signal-pro": 9}

# Synthetic session metas. The health and coaching builders read these, so the
# fixture exercises the same code path as a real run instead of hand-written JSON.
_SPEC = (
    # (id, harness, repo, prompts, tool_calls, errors, tokens_in, tokens_out,
    #  duration_min, skills)
    ("demo-a1", "muse", "atlas-relay", 34, 96, 11, 1_310_000, 630_000, 214.0,
     ("map-the-surface", "split-the-work", "prove-the-path", "trim-the-noise",
      "guard-the-contract", "trace-the-regression", "lock-the-interface")),
    ("demo-b2", "agy", "quarry-cli", 27, 74, 8, 790_000, 390_000, 168.0,
     ("guard-the-contract", "trace-the-regression", "ship-the-slice",
      "stage-the-env", "prove-the-path")),
    ("demo-c3", "claude", "atlas-relay", 19, 51, 2, 430_000, 180_000, 96.0,
     ("map-the-surface", "split-the-work", "seed-the-fixture")),
    ("demo-d4", "muse", "signal-desk", 16, 44, 4, 340_000, 145_000, 88.0,
     ("seed-the-fixture", "draft-the-note")),
    ("demo-e5", "agy", "atlas-relay-docs", 11, 26, 1, 180_000, 74_000, 41.0,
     ("draft-the-note", "lock-the-interface")),
    ("demo-f6", "muse", "quarry-cli", 9, 31, 3, 240_000, 96_000, 63.0,
     ("guard-the-contract", "name-the-boundary")),
    ("demo-g7", "claude", "atlas-relay", 8, 22, 0, 150_000, 61_000, 34.0,
     ("map-the-surface",)),
    ("demo-h8", "muse", "atlas-relay", 7, 19, 2, 128_000, 52_000, 29.0,
     ("prove-the-path", "score-the-run")),
    ("demo-i9", "agy", "signal-desk", 6, 17, 1, 96_000, 38_000, 26.0, ()),
    ("demo-j10", "muse", "atlas-relay", 5, 14, 0, 74_000, 31_000, 21.0,
     ("split-the-work",)),
    ("demo-k11", "claude", "quarry-cli", 5, 12, 1, 61_000, 24_000, 18.0, ()),
    ("demo-l12", "muse", "atlas-relay-docs", 4, 9, 0, 42_000, 18_000, 14.0,
     ("draft-the-note",)),
    ("demo-m13", "agy", "atlas-relay", 13, 38, 5, 310_000, 128_000, 74.0,
     ("map-the-surface", "trim-the-noise", "watch-the-drift")),
    ("demo-n14", "muse", "quarry-cli", 12, 35, 4, 288_000, 119_000, 69.0,
     ("prove-the-path", "stage-the-env")),
    ("demo-o15", "claude", "signal-desk", 10, 28, 2, 205_000, 88_000, 52.0,
     ("seed-the-fixture", "read-the-signal")),
    ("demo-p16", "muse", "atlas-relay", 9, 24, 1, 176_000, 72_000, 44.0,
     ("split-the-work", "guard-the-contract", "close-the-loop")),
    ("demo-q17", "agy", "atlas-relay-docs", 8, 21, 0, 132_000, 55_000, 33.0,
     ("draft-the-note",)),
    ("demo-r18", "muse", "signal-desk", 7, 18, 2, 118_000, 47_000, 28.0,
     ("stage-the-env", "break-the-cycle")),
    ("demo-s19", "claude", "quarry-cli", 6, 16, 1, 92_000, 37_000, 23.0,
     ("name-the-boundary",)),
    ("demo-t20", "muse", "atlas-relay", 5, 13, 0, 71_000, 29_000, 19.0, ()),
    ("demo-u21", "agy", "atlas-relay", 4, 11, 1, 58_000, 23_000, 16.0,
     ("score-the-run",)),
    ("demo-v22", "muse", "atlas-relay-docs", 3, 8, 0, 36_000, 15_000, 12.0, ()),
    ("demo-w23", "claude", "atlas-relay", 3, 7, 0, 31_000, 12_000, 10.0,
     ("lock-the-interface",)),
    ("demo-x24", "agy", "signal-desk", 2, 5, 0, 22_000, 9_000, 8.0, ()),
)

_CACHE_FACTOR = {"muse": 1.12, "agy": 0.92, "claude": 1.34}
_MODEL_CYCLE = (
    "atlas-large",
    "atlas-mini",
    "quarry-flash",
    "signal-pro",
)


_REPO_CYCLE = (
    "atlas-relay", "atlas-relay", "quarry-cli", "atlas-relay",
    "signal-desk", "quarry-cli", "atlas-relay-docs", "atlas-relay",
)
_HARNESS_CYCLE = ("muse", "agy", "claude", "muse", "muse", "agy")
_STACK_CYCLE = (0, 1, 2, 1, 3, 2, 4, 1, 0, 2)
_SKILL_NAMES = tuple(SKILLS)


def _demo_metas(count=62):
    """One population drives every derived table, so the numbers agree."""
    out = []
    for i, (sid, harness, repo, prompts, tools, errors, tin, tout, dur, skills) in enumerate(_SPEC):
        out.append({
            "id": sid,
            "harness": harness,
            "project": repo,
            "prompts": prompts,
            "tool_calls": tools,
            "errors": {"Command Failed": errors, "Edit Failed": errors // 3},
            "error_categories": {"Command Failed": errors, "Edit Failed": errors // 3},
            "tokens_in": tin,
            "tokens_out": tout,
            "duration_minutes": dur,
            "skill_loads": list(skills),
            "session_models": {_MODEL_CYCLE[i % 4]: 2 + i % 3},
        })
    for i in range(len(_SPEC), count):
        prompts = 2 + (i * 7) % 13
        tools = prompts * 2 + (i * 5) % 17
        errors = (i * 3) % 4
        tin = 20_000 + (i * 13_000) % 260_000
        want = _STACK_CYCLE[i % len(_STACK_CYCLE)]
        start = (i * 3) % len(_SKILL_NAMES)
        skills = tuple(_SKILL_NAMES[(start + k) % len(_SKILL_NAMES)] for k in range(want))
        out.append({
            "id": f"demo-{i + 1:02d}",
            "harness": _HARNESS_CYCLE[i % len(_HARNESS_CYCLE)],
            "project": _REPO_CYCLE[i % len(_REPO_CYCLE)],
            "prompts": prompts,
            "tool_calls": tools,
            "errors": {"Command Failed": errors, "Edit Failed": errors // 2},
            "error_categories": {"Command Failed": errors, "Edit Failed": errors // 2},
            "tokens_in": tin,
            "tokens_out": tin // 3,
            "duration_minutes": float(6 + (i * 11) % 70),
            "skill_loads": list(skills),
            "session_models": {_MODEL_CYCLE[i % 4]: 1 + i % 4},
        })
    return out


DEMO_METAS = _demo_metas()


def _skill_row(name):
    (sessions, loads, nudged, tokens, overhead, gap, duration, errors,
     pc_open, pc_fixed, win, band) = SKILLS[name]
    forced = nudged
    forced_pct = round(100.0 * nudged / loads, 1) if loads else None
    return {
        "skill": name,
        "mined_loads": sessions,
        "hook_loads": loads,
        "forced": forced,
        "forced_pct": forced_pct,
        "attributed_cache_read": float(tokens) * 3.1,
        "attributed_cache_write": 0.0,
        "attributed_tokens_in": float(tokens) * 0.72,
        "attributed_tokens_out": float(tokens) * 0.28,
        "attributed_tokens_total": float(tokens),
        "estimated_context_tax_tokens": float(overhead),
        "token_bearing_sessions": max(1, sessions - 1),
        "median_gap_s": float(gap),
        "median_duration_min": float(duration),
        "attributed_errors": float(errors),
        "error_rate_per_session": round(errors / sessions, 2) if sessions else 0.0,
        "papercut_filed": pc_open + pc_fixed,
        "papercut_fixed": pc_fixed,
        "papercut_open": pc_open,
        "eval_pass_rate": None if win is None else round(0.55 + win / 4, 3),
        "eval_win_rate": win,
        "eval_noise_band": band,
        "eval_pairs": None if win is None else 2 * (pc_open + 4),
        "redirect_interjections": max(0, 12 - sessions // 2),
        "top_interjection_reason": "approval" if sessions % 2 else "clarification",
        "no_progress_share_pct": None,
        "goal_sessions": 0,
        "trigger_precision": round(0.42 + (sessions % 5) * 0.09, 3),
        "trigger_recall": round(0.55 + (sessions % 4) * 0.07, 3),
        "trigger_f1": round(0.48 + (sessions % 6) * 0.06, 3),
        "trigger_decider": "rubric",
    }


def build_demo_aggregate():
    """Build the full aggregate document. Pure function of the tables above."""
    total_sessions = len(DEMO_METAS)
    days_active = 11

    per_skill = []
    for name in SKILLS:
        row = _skill_row(name)
        per_skill.append({
            "skill": row["skill"],
            "sessions": row["mined_loads"],
            "token_bearing_sessions": row["token_bearing_sessions"],
            "attributed_cache_read": row["attributed_cache_read"],
            "attributed_cache_write": row["attributed_cache_write"],
            "attributed_tokens_in": row["attributed_tokens_in"],
            "attributed_tokens_out": row["attributed_tokens_out"],
            "attributed_tokens_total": row["attributed_tokens_total"],
            "attributed_errors": row["attributed_errors"],
            "error_rate_per_session": row["error_rate_per_session"],
            "estimated_context_tax_tokens": row["estimated_context_tax_tokens"],
            "median_gap_s": row["median_gap_s"],
            "median_duration_min": row["median_duration_min"],
        })

    skill_table = [_skill_row(name) for name in SKILLS]

    repositories = _derive_repositories(DEMO_METAS)
    by_harness = _derive_by_harness(DEMO_METAS)

    agg = {
        "meta": {
            "from": FROM_DATE,
            "to": TO_DATE,
            "since": FROM_DATE,
            "harnesses": list(HARNESSES),
            "project": None,
            "repos": [
                {"name": "atlas-relay", "added": 2140, "deleted": 780, "merges": 6},
                {"name": "quarry-cli", "added": 680, "deleted": 240, "merges": 3},
                {"name": "signal-desk", "added": 410, "deleted": 95, "merges": 1},
                {"name": "atlas-relay-docs", "added": 260, "deleted": 40, "merges": 0},
            ],
            "prompts": sum(m["prompts"] for m in DEMO_METAS),
            "tool_calls": sum(m["tool_calls"] for m in DEMO_METAS),
            "top_level_sessions": len(DEMO_METAS),
            "total_sessions": len(DEMO_METAS),
            "child_sessions": 0,
            "facets_analyzed": len(DEMO_METAS) + 6,
            "days_active": days_active,
            "msgs_per_day": round(sum(m["prompts"] for m in DEMO_METAS) / float(days_active), 1),
            "git_commits_in_transcripts": 21,
            "git_pushes_in_transcripts": 5,
            "fixtures_excluded": 2,
            "scope": {
                "mode": "harness",
                "harnesses": list(HARNESSES),
                "project": None,
                "days": 14,
                "since": FROM_DATE,
                "session_ids": [],
                "missing_sessions": [],
                "all_time": False,
                "scope_key": "demo-fixture",
            },
        },
        "by_harness": by_harness,
        "repositories": repositories,
        "projects": {name: 2 + i for i, name in enumerate(PROJECTS)},
        "charts": {
            "prompt_distribution": dict(PROMPT_DISTRIBUTION),
            "response_time_buckets": dict(RESPONSE_BUCKETS),
            "median_response_gap_s": 96.0,
            "avg_response_gap_s": 412.4,
            "median_response_gap_s_by_harness": {"muse": 88.0, "agy": 104.0, "claude": 71.0},
            "hour_counts_utc": dict(HOURS),
            "interjection_reasons": dict(INTERJECTIONS),
            "tool_error_categories": dict(TOOL_ERRORS),
            "top_tools": dict(TOP_TOOLS),
            "languages": dict(LANGUAGES),
            "session_types": dict(SESSION_TYPES),
            "outcomes": dict(OUTCOMES),
            "what_you_wanted": dict(WHAT_YOU_WANTED),
            "what_helped_most": dict(WHAT_HELPED),
            "primary_friction_types": dict(FRICTION_TYPES),
            "satisfaction": dict(SATISFACTION),
            "multi_agent_overlap": {"overlap_events": 7, "sessions_involved": 5, "pct_of_messages": 14},
        },
        "interjections": {
            "follow_up_rate_pct": 78.4,
            "prompt_bearing_sessions": 58,
            "zero_prompt_sessions": 16,
            "reasons": dict(INTERJECTIONS),
            "by_harness": {
                h: {"follow_up_rate_pct": 70.0 + i * 6, "median_prompts": 8.0 + i, "sessions_with_prompts": 20 - i}
                for i, h in enumerate(HARNESSES)
            },
            "top_steered": [
                {"harness": "muse", "session_id": "demo-session-a1", "prompts": 34, "tool_calls": 96},
                {"harness": "agy", "session_id": "demo-session-b2", "prompts": 27, "tool_calls": 74},
                {"harness": "claude", "session_id": "demo-session-c3", "prompts": 19, "tool_calls": 51},
            ],
        },
        "hooks": {
            "events": 96,
            "sessions": 41,
            "goal_done": 12,
            "goal_blocked_watcher": 3,
            "goal_released": 9,
            "nudge_blocked": {"map-the-surface": 2, "prove-the-path": 3},
            "model_failures": {"bash": 4, "edit": 2},
            "agy": {"hook_events": 31, "sessions": 18, "sessions_with_hook_events": 16},
        },
        "skill_costs": {
            "per_skill": per_skill,
            "by_harness": {
                h: {
                    "sessions": v["sessions"],
                    "token_bearing_sessions": v["sessions"] - 3,
                    "tokens_in": float(v["prompts"] * 9100),
                    "tokens_out": float(v["prompts"] * 3100),
                    "tokens_cache_read": float(v["prompts"] * 6200) * _CACHE_FACTOR[h],
                    "tokens_cache_write": float(v["prompts"] * 400),
                    "attributed_tokens_in": float(v["prompts"] * 7100),
                    "attributed_tokens_out": float(v["prompts"] * 2400),
                    "attributed_cache_read": float(v["prompts"] * 24000),
                    "attributed_cache_write": 0.0,
                    "attributed_errors": float(v["errors"] - 4),
                    "errors": float(v["errors"]),
                    "unattributed_sessions": 3,
                    "unattributed_tokens_in": float(v["prompts"] * 1400),
                    "unattributed_tokens_out": float(v["prompts"] * 500),
                    "unattributed_cache_read": float(v["prompts"] * 900),
                    "unattributed_cache_write": 0.0,
                    "unattributed_errors": 4.0,
                }
                for h, v in by_harness.items()
            },
            "totals": {
                "sessions": total_sessions,
                "tokens_in": 9_420_000.0,
                "tokens_out": 3_180_000.0,
                "tokens_cache_read": 31_600_000.0,
                "tokens_cache_write": 410_000.0,
                "errors": 45,
            },
            "unattributed": {
                "sessions": 9,
                "tokens_in": 1_240_000.0,
                "tokens_out": 420_000.0,
                "tokens_cache_read": 4_100_000.0,
                "tokens_cache_write": 0.0,
                "errors": 7.0,
            },
            "mined_skills": {name: 1 for name in list(SKILLS)[:9]},
            "caveats": [
                "Post-load attribution credits tokens and errors only to skills already loaded at each turn (pre-load work and skill-free sessions land in unattributed).",
                "Tokens are mined across the three harnesses in this fixture; older sessions without usage fields report 0.",
                "Estimated context tax approximates (SKILL.md bytes / 4) * turns after load, so it is a lower bound.",
            ],
        },
        "skill_table": skill_table,
        "skill_recommendations": [
            {
                "action": "modify",
                "target": "trace-the-regression",
                "reason": "Highest error rate per session among loaded skills (2.00), and the most common follow-up reason is a goal redirect.",
                "suggestion": "Add a required failing-test-first step and a stop condition before the third retry of the same command.",
            },
            {
                "action": "create",
                "target": "hold-the-invariant",
                "reason": "Four sessions lost context across compaction while editing a shared schema.",
                "suggestion": "Create a skill that writes the invariant list to a file before the first edit and re-reads it after any compaction.",
            },
            {
                "action": "remove",
                "target": "mark-the-gap",
                "reason": "Loaded once in sixteen days and produced no attributed tokens.",
                "suggestion": "Fold its checklist into prove-the-path, or delete it.",
            },
        ],
        "papercuts": {
            "total_filed": 14,
            "total_fixed": 6,
            "total_open": 8,
            "per_skill": {
                "prove-the-path": {"filed": 3, "fixed": 1, "open": 2},
                "trace-the-regression": {"filed": 2, "fixed": 0, "open": 2},
                "guard-the-contract": {"filed": 3, "fixed": 1, "open": 2},
                "stage-the-env": {"filed": 2, "fixed": 0, "open": 2},
            },
        },
        "evals": {
            "skills_evaluated": 9,
            "mean_win_rate": 0.58,
            "mean_noise_band": 0.11,
        },
        "trigger_evals": {
            "skills_evaluated": 9,
            "per_skill": {
                name: {
                    "rubric": {
                        "decider": "rubric",
                        "mode": "rubric",
                        "recorded_at": "2026-02-14T10:00:00+00:00",
                        "partial": False,
                        "errors": 0,
                        "tp": 8, "fp": 2, "fn": 3, "tn": 11,
                        "precision": 0.8, "recall": 0.73, "f1": 0.76,
                        "trigger_rate": 0.42, "false_trigger_rate": 0.15,
                    }
                }
                for name in list(SKILLS)[:9]
            },
        },
        "eval_trends": {
            "per_skill": {
                "split-the-work": [
                    {"harness": "muse", "sha_short": "a1b2c3d", "skill_sha": "a1b2c3d4e5", "last_recorded_at": "2026-02-04T09:00:00+00:00",
                     "runs": 12, "win_rate": 0.52, "noise_band": 0.10, "pass_rate_with": 0.61,
                     "tool_calls_delta": -1.2, "tool_errors_delta": -0.4, "cost_delta_in": -3200, "cost_delta_out": -900},
                    {"harness": "muse", "sha_short": "d4e5f6a", "skill_sha": "d4e5f6a7b8", "last_recorded_at": "2026-02-11T09:00:00+00:00",
                     "runs": 14, "win_rate": 0.71, "noise_band": 0.09, "pass_rate_with": 0.74,
                     "tool_calls_delta": -2.6, "tool_errors_delta": -1.1, "cost_delta_in": -8100, "cost_delta_out": -2400},
                ],
                "trace-the-regression": [
                    {"harness": "agy", "sha_short": "9f8e7d6", "skill_sha": "9f8e7d6c5b", "last_recorded_at": "2026-02-06T09:00:00+00:00",
                     "runs": 10, "win_rate": 0.55, "noise_band": 0.13, "pass_rate_with": 0.50,
                     "tool_calls_delta": 0.8, "tool_errors_delta": 0.6, "cost_delta_in": 1400, "cost_delta_out": 600},
                    {"harness": "agy", "sha_short": "3c2b1a0", "skill_sha": "3c2b1a09f8", "last_recorded_at": "2026-02-13T09:00:00+00:00",
                     "runs": 11, "win_rate": 0.44, "noise_band": 0.14, "pass_rate_with": 0.41,
                     "tool_calls_delta": 1.9, "tool_errors_delta": 1.4, "cost_delta_in": 5200, "cost_delta_out": 2100},
                ],
            }
        },
        "diff_from_prev": {
            "prev_snapshot_id": "2026-01-29-demo",
            "kpi_deltas": {
                "errors_per_session": {"prev": 0.71, "curr": 0.61, "delta": -0.10, "improved": True},
                "hook_blocked": {"prev": 9, "curr": 6, "delta": -3, "improved": True},
                "redirect_per_session": {"prev": 0.31, "curr": 0.23, "delta": -0.08, "improved": True},
                "cache_hit_pct": {"prev": 69.4, "curr": 73.2, "delta": 3.8, "improved": True},
                "eval_mean_win_rate": {"prev": 0.54, "curr": 0.58, "delta": 0.04, "improved": None},
            },
            "pareto_hv": {"prev": 0.388, "curr": 0.412, "delta": 0.024},
            "scope_warnings": [],
            "accountability": [
                {
                    "status": "implemented_verified", "target": "prove-the-path", "summary": "Added failing-test-first step",
                    "metric": {"name": "errors/session", "prev": 1.8, "curr": 1.33},
                    "evidence": ["tool_error_categories.Command Failed -6"], "carry_over_count": 0,
                },
                {
                    "status": "implemented_ineffective", "target": "trace-the-regression", "summary": "Added stop condition before third retry",
                    "metric": {"name": "eval win rate", "prev": 0.55, "curr": 0.44},
                    "evidence": ["eval_trends.agy.win_rate -0.11"], "carry_over_count": 1,
                },
                {
                    "status": "not_done", "target": "hold-the-invariant", "summary": "Write invariant list before first edit",
                    "metric": {}, "evidence": ["no target change detected"], "carry_over_count": 2,
                },
            ],
            "radar_diff": {
                "axes": {
                    "quality": {"prev": 0.54, "curr": 0.58, "delta": 0.04, "direction": "improved"},
                    "trigger": {"prev": 0.64, "curr": 0.64, "delta": 0.0, "direction": "flat"},
                    "reliability": {"prev": 0.55, "curr": 0.62, "delta": 0.07, "direction": "improved"},
                    "alignment": {"prev": 0.76, "curr": 0.82, "delta": 0.06, "direction": "improved"},
                    "efficiency": {"prev": 0.71, "curr": 0.71, "delta": 0.0, "direction": "flat"},
                    "cache": {"prev": 0.69, "curr": 0.73, "delta": 0.04, "direction": "improved"},
                },
                "area_prev": 0.41, "area_curr": 0.44, "area_delta_pct": 7.3,
                "improved_axes": ["Quality", "Reliability", "Alignment", "Cache"],
                "regressed_axes": [],
            },
        },
        "changepoints": {
            "skills": {
                "split-the-work": {
                    "edited_at": "2026-02-11T09:00:00+00:00", "edited_sha": "d4e5f6a", "source": "git",
                    "verdict": "improved",
                    "pre": {"loads": 4, "errors_per_session": 1.25, "redirects_per_session": 0.5},
                    "post": {"loads": 6, "errors_per_session": 0.5, "redirects_per_session": 0.17},
                },
                "trace-the-regression": {
                    "edited_at": "2026-02-13T09:00:00+00:00", "edited_sha": "3c2b1a0", "source": "git",
                    "verdict": "regressed",
                    "pre": {"loads": 3, "errors_per_session": 1.0, "redirects_per_session": 0.33},
                    "post": {"loads": 4, "errors_per_session": 2.0, "redirects_per_session": 0.75},
                },
            },
            "hooks": {
                "edited_at": "2026-02-09T09:00:00+00:00", "edited_sha": "77aa11b", "source": "git",
                "verdict": "improved",
                "pre": {"sessions": 18, "hook_blocked_per_session": 0.44},
                "post": {"sessions": 22, "hook_blocked_per_session": 0.14},
            },
            "summary": {"improved": 1, "regressed": 1, "unchanged": 0, "awaiting_data": 0, "skills_edited_in_window": 2},
        },
        "facet_summaries": [],
        "sessions_detail": [],
        "not_tracked": [
            "Per-hook firing counts (volume without signal; first-fire witnesses plus transcript joins cover compliance).",
            "Codex and OpenCode hook nudge telemetry when their skill hooks are not installed.",
            "Correlation is never causation: facet outcomes and satisfaction are model-estimated from bounded session digests.",
        ],
    }
    # Derived documents are computed by the same functions the pipeline uses, so
    # the fixture cannot drift from the aggregator's shapes.
    agg["session_health"] = session_health_stats(DEMO_METAS, agg["skill_costs"])
    agg["coaching_playbook"] = build_coaching_playbook(agg, agg["session_health"])
    agg["radar_profile"] = compute_radar_profile(agg)
    agg["pareto"] = compute_pareto_analysis(agg["skill_table"], agg["eval_trends"])
    return agg


_REPO_DESC = {
    "atlas-relay": "Relay transport, retry policy, and the fixture harness.",
    "quarry-cli": "Command surface, argument parsing, and the schema guard.",
    "signal-desk": "Alert routing and the digest writer.",
    "atlas-relay-docs": "Reference pages and the migration guide.",
}


def _demo_project_areas():
    """Project labels follow the same population as the repository table."""
    return [
        {
            "name": r["repo"],
            "sessions_label": f'{r["main_sessions"]} sessions',
            "description": _REPO_DESC.get(r["repo"], ""),
        }
        for r in _derive_repositories(DEMO_METAS)
    ]


def build_demo_synthesis():
    return {
        "at_a_glance": {
            "working": "Four repositories moved forward without a rollback, and the two slow suites finally run in one command.",
            "hindering": "Retried shell commands and stale edit targets still cost more turns than any design decision.",
            "quick_wins": "Give the two busiest skills a copy-pasteable verification command.",
            "ambitious": "Run one task in two harnesses and score both against the same rubric.",
        },
        "project_areas": _demo_project_areas(),
        "narrative_paragraphs": [
            "Half the window was one repository at a time, with short supervised loops and a test run between turns.",
            "The four long threads all crossed a refactor boundary. Their error counts came from retried shell commands after a moved path, not from scope changes.",
        ],
        "key_insight": "Work concentrates in two repositories, and the tool-error count follows command retries rather than scope changes.",
        "wins_intro": "The window produced two finished slices and one migration guide that did not need a rewrite.",
        "big_wins": [
            {"title": "Retry policy landed in one pass", "description": "The atlas-relay session wrote the backoff policy and its tests without a second design pass."},
            {"title": "Schema guard closed the loop", "description": "quarry-cli shipped a guard that rejects the exact mismatch that broke three earlier sessions."},
            {"title": "Migration guide survived review", "description": "The docs session produced a guide that needed edits, not restructure."},
        ],
        "friction_categories": [
            {"title": "Blind path guesses after a move (12 occurrences)", "description": "Agents opened paths from an older layout and paid a failed read for each one.",
             "examples": ["[demo-a1] read src/relay/queue.py after the module moved to src/relay/pipeline/queue.py"],
             "remediation": "Keep the directory map in AGENTS.md current, and tell agents to search before opening a guessed path."},
            {"title": "Stale edit targets (9 occurrences)", "description": "Edits failed because the target lines had changed since the agent last read them.",
             "examples": ["[demo-b2] edit failed on a function that had been renamed two turns earlier"],
             "remediation": "Read the exact target lines immediately before editing, and never edit from a cached snippet."},
        ],
        "agents_md_additions": [
            {"target": "AGENTS.md", "snippet": "Run the focused test file before claiming a change is complete.", "why": "Retried shell commands were the largest single error source."},
            {"target": "AGENTS.md", "snippet": "Search for a path before opening it; the layout changed this month.", "why": "Twelve failed reads came from paths that had moved."},
        ],
        "features_to_try": [
            {"title": "Parallel harness split", "oneliner": "Give two harnesses one workstream each and compare the debriefs.",
             "why": "You already run three harnesses; the split makes the comparison cheap.",
             "example": "Split this refactor into two independent workstreams and report the files each one touched."},
        ],
        "usage_patterns": [
            {"title": "Short supervised loops", "summary": "Most sessions stay under ten prompts.",
             "detail": "You check output between turns instead of delegating a long unattended run.",
             "prompt": "Plan the next three edits, then wait for approval before applying them."},
            {"title": "Test first, then widen", "summary": "The successful sessions ran one focused test before the full suite.",
             "detail": "Failures surface in seconds, and the full suite runs once at the end.",
             "prompt": "Run the focused test for the file you are about to change, then propose the edit."},
        ],
        "horizon_intro": "Two workflows are worth trying once the current migration settles.",
        "horizon_workflows": [
            {"title": "Cross-harness replay", "possible": "Score the same task in two harnesses against one rubric.",
             "tip": "Start with a single failing test and one shared repository.",
             "prompt": "Run this failing test in both harnesses and report the minimal diff each one needed."},
            {"title": "Invariant file", "possible": "Keep the schema invariant list in a file the agent must re-read after compaction.",
             "tip": "Write the list once by hand, then let the skill maintain it.",
             "prompt": "Write the current schema invariants to invariants.md, then re-read that file before every edit in this session."},
        ],
    }


def write_fixture(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    agg_path = os.path.join(out_dir, "demo-aggregate.json")
    syn_path = os.path.join(out_dir, "demo-synthesis.json")
    with open(agg_path, "w", encoding="utf-8") as fh:
        json.dump(build_demo_aggregate(), fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(syn_path, "w", encoding="utf-8") as fh:
        json.dump(build_demo_synthesis(), fh, indent=2, sort_keys=True)
        fh.write("\n")
    return agg_path, syn_path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="debrief-demo-fixture")
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures"))
    ap.add_argument("--html", default="", help="Also render the fixture to this HTML path")
    args = ap.parse_args(argv)

    agg_path, syn_path = write_fixture(args.out_dir)
    sys.stdout.write(f"wrote {agg_path}\nwrote {syn_path}\n")
    if args.html:
        from debrief_render import render_html
        doc = render_html(build_demo_aggregate(), build_demo_synthesis())
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(doc)
        sys.stdout.write(f"wrote {args.html} ({len(doc.encode('utf-8'))} bytes)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
