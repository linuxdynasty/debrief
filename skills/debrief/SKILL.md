---
name: debrief
description: "Use when asked for a skills debrief, /debrief, a usage-insights-style report, or workflow recommendations across Claude Code, Codex, OpenCode, Antigravity (agy), Muse, and Cursor. Runs debrief (Stage 1 meta + Stage 2 cached semantic facets + optional hook telemetry) and renders an offline interactive HTML report."
---

# Multi-Harness Agent Debrief

Generate an `/insights`-grade operational debrief across **Claude Code**, **Codex**, **OpenCode**, **Antigravity (`agy`)**, and **Muse** sessions. Deterministic scripts extract session metadata, cache semantic facets locally under `$DEBRIEF_DATA_DIR/debrief-cache/` (default `$XDG_DATA_HOME/debrief/debrief-cache/`), merge optional hook telemetry (`skills-usage.jsonl`) and git history, and render an offline interactive HTML report. Your job is to orchestrate parallel fast-tier facet extraction for uncached sessions and write the high-signal narrative synthesis and actionable workflow fixes.

By default, debrief runs across **all 5 harnesses (`muse,agy,claude,codex,opencode`)** and **all repos** over the last **30 days**. Narrow or widen scope as requested:
- Current active session: `--current` (resolves via harness session env var or fail-closed CWD recency; pass `--harness` if two harnesses are active simultaneously).
- Explicit session(s): `--session ID` (repeatable, comma-separated, exact ID, unique >=8-char prefix, or `<harness>:<id>`) or `--sessions-file PATH`. Linked child subagents are auto-included unless `--no-children` is passed. Use `debrief sessions [--days N|--all-time] [--harness ...] [--limit N]` to list discoverable IDs.
- Single provider or all-time: `--harness <name[,name...]|all>` (strict validation; unknown names exit 2), `--since YYYY-MM-DD`, `--days N`, `--all-time`, or `--project SUB`.
- Optional skill alias mapping and skill directories: pass `--aliases FILE` (or `DEBRIEF_ALIASES_FILE`) and repeatable `--skills-dir DIR` (or `DEBRIEF_SKILLS_DIRS`).

Privacy boundary: local transcripts and cached facets stay under `$DEBRIEF_DATA_DIR/debrief-cache/` (never committed, never uploaded). Hook telemetry in `skills-usage.jsonl` stays content-free. Cite short session IDs in the report; never paste raw message text or secrets.

## Workflow (5 Steps)

### Step 1: Resolve Debrief CLI & Prepare Batches

Resolve the CLI in order:
1. If `debrief` is on `PATH` (installed via `npm i -g @linuxdynasty/debrief` or `~/.local/bin/debrief`), set `DEBRIEF="debrief"`.
2. Otherwise follow symlinks from this `SKILL.md` (`readlink -f`) and go up two levels (`skills/debrief/SKILL.md` -> package root containing `scripts/debrief.sh`), setting `DEBRIEF="bash $ROOT/scripts/debrief.sh"`.
3. Otherwise invoke `npx -y @linuxdynasty/debrief` (or check `~/.local/share/debrief/runtime/scripts/debrief.sh`).

Run Stage 1 extraction and batch preparation:

```bash
$DEBRIEF prepare --days 30 --max-new 100 --batch-size 10
```

Add `--since`, `--all-time`, `--project`, `--harness`, `--current`, `--session`, or `--sessions-file` if requested. `prepare`:
- Extracts/caches Stage 1 metadata (`tools`, `error_categories`, `languages`, `response_gaps`, `message_hours`, `skill_loads`, `turns_after_skill_load`, `post_load_attribution`, `git_commits`, `subagents`, and token/cache usage across all 5 harnesses) incrementally by file `mtime`.
- Auto-imports existing `~/.claude/usage-data/facets/*.json` so Claude sessions are not re-classified.
- Rolls child subagents into their parent coordinator digest (unless `--no-children`).
- Skips trivial sessions (`prompts < 2` and `tool_calls < 3`).
- Emits up to `--max-new` (default 100, newest first) uncached digests into `batch-01.json`, `batch-02.json`, ... and prints a JSON manifest.

### Step 2: Parallel Fast-Tier Facet Extraction (Stage 2)

If `manifest.facets_queued == 0`, skip directly to Step 3.

Otherwise, dispatch **one fast-tier subagent per `batch-XX.json` in parallel** (`haiku` on Claude, `flash` on `agy`, `muse-ember` on Muse, or a fast model on Codex/OpenCode). Give each subagent its batch file path and ask it to return strict JSON `{"facets": [...]}` with one object per digest in the batch using this exact schema:

```json
{
  "session_id": "<exact digest session_id>",
  "harness": "muse|agy|claude|codex|opencode",
  "source_mtime": 0,
  "underlying_goal": "1 concise sentence describing what the user wanted",
  "goal_categories": {"<snake_case_category>": 1},
  "outcome": "fully_achieved|mostly_achieved|partially_achieved|not_achieved|unclear",
  "satisfaction": "satisfied|likely_satisfied|dissatisfied|frustrated|unsure",
  "friction_counts": {"<friction_type>": 1},
  "friction_detail": "1-2 sentences naming the concrete failure mode (or empty string)",
  "primary_success": "multi_file_changes|good_debugging|correct_code_edits|good_explanations|proactive_help|fast_accurate_search|none",
  "session_type": "single_task|multi_task|iterative_refinement|exploration|quick_question",
  "brief_summary": "1-2 sentences summarizing what happened and how it ended"
}
```

Use concrete `goal_categories` (e.g. `bug_fix`, `feature_implementation`, `ci_workflow_maintenance`, `pr_review_and_merge`, `performance_investigation`, `docs_and_process`, `refactoring`, `testing_and_verification`) and canonical `friction_counts` keys (`buggy_code`, `wrong_approach`, `hook_or_env_retry`, `stale_status`, `tool_failure`, `misunderstood_request`, `missing_path_probe`, `excessive_changes`, `context_loss`, `user_rejected_action`).

As each subagent replies, validate and write its facets atomically:

```bash
$DEBRIEF cache-write /path/to/batch-01-facets.json
```

(Or pipe JSON on stdin with `cache-write -`.) Re-run or fix any rejected record before proceeding.

### Step 3: Aggregate Across Harnesses, Hooks & Git

```bash
$DEBRIEF aggregate --days 30 --repo "$PWD" --compare-prev --out "$WORK/aggregate.json"
```

Pass `--log` for extra telemetry logs, repeatable `--repo` / `--skills-dir` flags for active repos and skill trees, and the same scoping flags used in Step 1.
- **Report Diff & Accountability**: `--compare-prev` auto-matches the most recent saved snapshot for this scope (or `--compare SNAPSHOT.json`) to compute KPI deltas, overlaid 6-axis **Trajectory Radar** movement, Pareto hypervolume delta (`ΔHV`), and deterministic recommendation accountability (`implemented_verified`, `implemented_ineffective`, `implemented_pending_data`, `not_done` with `carry_over_count`, `resolved_externally`). Diff any two snapshots directly via `$DEBRIEF diff --prev A.json --curr B.json`.
- **Git Change-Point Attribution**: automatically detects per-skill `SKILL.md` and `hooks/` last-edit commits, splitting each edited target into `pre` vs `post` sessions (`improved`, `awaiting_data`, `unchanged`, `regressed`) so pre-fix history does not trigger stale `MODIFY` nags. Pass `--ignore-changepoints` for raw unsplit history or `--since-last-edit` to filter sessions to post-change runs.
- **Multi-Objective Pareto Fronts**: computed over effectiveness, overhead/load, and friction/load (plus per-`(skill, harness)` version fronts with `HEAD` regression alerts and hypervolume `HV` when `--evals` / `--eval-history` is supplied).
- **Optional Joins**: `--papercuts FILE` (offline JSON export of labeled issues), `--evals PATH` (A/B replay-eval summaries), `--trigger-evals PATH` (trigger precision/recall JSON), `--eval-history [PATH]` (version trend JSONL).

Read `$WORK/aggregate.json` — key top-level sections: `meta`, `by_harness`, `hooks`, `charts`, `interjections`, `skill_table`, `skill_costs`, `repositories`, `skill_recommendations`, `changepoints`, `pareto`, `radar_profile`, `diff_from_prev`, `session_health`, `coaching_playbook`, `facet_summaries`.

### Step 4: Synthesize Usage-Driven Recommendations & Render HTML

Write `$WORK/synthesis.json` grounded strictly in `aggregate.json`. When `aggregate.diff_from_prev` is present, **audit prior recommendations first**: highlight `implemented_verified` wins, flag `implemented_ineffective` edits, and escalate `not_done` items with high `carry_over_count` before proposing net-new work. Call out any `pareto.head_regressions` and strictly dominated skills from `pareto.portfolio_dominated`. Every recommendation must cite the pattern, count, or short session IDs that motivate it. Never rank people or harnesses, and never confuse correlation with causation.

Required `synthesis.json` keys: `at_a_glance` (`working`, `hindering`, `quick_wins`, `ambitious`), `project_areas`, `narrative_paragraphs`, `key_insight`, `wins_intro`, `big_wins`, `friction_intro`, `friction_categories` (each with `title`, `description`, `examples`, `remediation`), `agents_md_additions`, `features_to_try`, `usage_patterns`, `horizon_intro`, `horizon_workflows`.

Render the offline HTML report (and persist the scope-keyed content-free snapshot under `$DEBRIEF_DATA_DIR/debrief-reports/snapshots/`):

```bash
$DEBRIEF render \
  --aggregate "$WORK/aggregate.json" \
  --synthesis "$WORK/synthesis.json"
```

By default, `render` writes `$XDG_DATA_HOME/debrief/debrief-reports/report-YYYY-MM-DD-HHMMSS.html`, updates `report-latest.html`, and prints a human-legible terminal summary with the exact report/snapshot paths, coverage, 6-axis Trajectory Radar scores, post-edit change-point verdicts, Pareto stats, key insight, and top recommended actions (pass `--json` for compact machine JSON paths, or run `$DEBRIEF summary --aggregate "$WORK/aggregate.json" --synthesis "$WORK/synthesis.json"` anytime). Override output paths with `--out PATH`, `--snapshot-out PATH`, or `--no-snapshot`.

### Step 5: Chat Summary

Reply concisely with:
1. Clickable `file://` link to the generated HTML report (and `report-latest.html`).
2. Coverage line (window, harnesses, top-level sessions, facets analyzed, any deferred by `--max-new`).
3. The **Key Insight** and **Top 3 Actionable Fixes** (leading with accountability results when `--compare-prev` was used).
4. What the data could not answer (`not_tracked` items and correlation caveats).
