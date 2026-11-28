#!/usr/bin/env bash
# Behavioral suite for GitHub PR review escape tracking, universal reviewer parsing,
# auto-discovered cache for reviews + papercuts, and offline backward compatibility.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

passed=0
failed=0
ok() {
	printf 'ok - %s\n' "$1"
	passed=$((passed + 1))
}
no() {
	printf 'not ok - %s\n' "$1" >&2
	failed=$((failed + 1))
}

# Create a fake git repo with a GitHub origin so auto-discovery resolves owner/repo.
repo="${WORK}/demo-repo"
mkdir -p "${repo}" "${WORK}/cache/meta" "${WORK}/cache/facets" "${WORK}/cache/github"
git -C "${repo}" init -q
git -C "${repo}" remote add origin "https://github.com/acme/demo.git"

# Seed two Stage 1 session metas (one joined by branch, one joined by commit SHA).
now_ep="$(python3 -c 'import time; print(int(time.time()))')"
cat >"${WORK}/cache/meta/muse__sess001.json" <<EOF
{
  "schema_version": 2, "harness": "muse", "id": "sess001",
  "project": "${repo}", "branch": "feat/keyed-probe", "commit": "aaaa1111bbbb",
  "first_epoch": $((now_ep - 3600)), "last_epoch": $((now_ep - 1800)), "source_mtime": ${now_ep},
  "prompts": 4, "tool_calls": 20, "errors": {"Command Failed": 1},
  "skill_loads": ["executor-preflight", "code-review"], "tools": {"bash": 10}
}
EOF
cat >"${WORK}/cache/meta/claude__sess002.json" <<EOF
{
  "schema_version": 2, "harness": "claude", "id": "sess002",
  "project": "${repo}", "branch": "main", "commit": "cccc3333dddd",
  "first_epoch": $((now_ep - 3000)), "last_epoch": $((now_ep - 1200)), "source_mtime": ${now_ep},
  "prompts": 3, "tool_calls": 15, "errors": {},
  "skill_loads": ["golang-engineering"], "tools": {"bash": 8}
}
EOF
: >"${WORK}/hooks.jsonl"

# Seed raw GraphQL-shaped PR nodes covering reviewd, chatgpt-codex, cursor-bugbot, human,
# CI-timing noise vs real escapes, and repeat P1s across rounds.
now_iso="$(python3 -c 'import datetime; print(datetime.datetime.now(datetime.timezone.utc).isoformat())')"
cat >"${WORK}/cache/github/acme__demo.reviews.json" <<EOF
{
  "schema_version": 1,
  "repo": "acme/demo",
  "synced_at": "${now_iso}",
  "prs": [
    {
      "number": 101,
      "state": "MERGED",
      "headRefName": "feat/keyed-probe",
      "createdAt": "${now_iso}",
      "updatedAt": "${now_iso}",
      "mergedAt": "${now_iso}",
      "commits": {"nodes": [{"commit": {"oid": "aaaa1111bbbb2222"}}, {"commit": {"oid": "aaaa2222bbbb3333"}}]},
      "reviews": {"nodes": [
        {"author": {"login": "owner"}, "state": "COMMENTED", "submittedAt": "${now_iso}", "commit": {"oid": "aaaa1111bbbb2222"}, "body": "**P0** 0 · **P1** 2 · **P2** 1 · **P3** 0\n<!-- reviewd:head=aaaa1111bbbb2222 -->"},
        {"author": {"login": "owner"}, "state": "COMMENTED", "submittedAt": "${now_iso}", "commit": {"oid": "aaaa2222bbbb3333"}, "body": "Repeat P1\n**P0** 0 · **P1** 1 · **P2** 0 · **P3** 0\n<!-- reviewd:head=aaaa2222bbbb3333 -->"}
      ]},
      "reviewThreads": {"nodes": [
        {
          "id": "T1", "isResolved": false, "isOutdated": false, "path": "pkg/probe.go", "line": 42,
          "comments": {"nodes": [{"author": {"login": "owner"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "aaaa1111bbbb2222"}, "body": "**P1** · evidence-overclaim · high confidence\nPerf evidence measured on statement production never executes."}]}
        },
        {
          "id": "T2", "isResolved": true, "isOutdated": false, "path": "pkg/fill.go", "line": 70,
          "comments": {"nodes": [
            {"author": {"login": "owner"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "aaaa1111bbbb2222"}, "body": "**P1** · runtime-proof-gap · high confidence\nNo executed live proof on this head; CI pending, sandbox has no database."},
            {"author": {"login": "owner"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "aaaa1111bbbb2222"}, "body": "CI passed."}
          ]}
        },
        {
          "id": "T3", "isResolved": false, "isOutdated": false, "path": "pkg/fill.go", "line": 70,
          "comments": {"nodes": [{"author": {"login": "owner"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "aaaa2222bbbb3333"}, "body": "**P1** · runtime-proof-gap · high confidence\nStill no observed live-database proof on this head (repeat finding); live lanes pending."}]}
        }
      ]}
    },
    {
      "number": 102,
      "state": "OPEN",
      "headRefName": "fix/codex-catch",
      "createdAt": "${now_iso}",
      "updatedAt": "${now_iso}",
      "mergedAt": null,
      "commits": {"nodes": [{"commit": {"oid": "cccc3333dddd4444"}}]},
      "reviews": {"nodes": [
        {"author": {"login": "chatgpt-codex-connector[bot]"}, "state": "COMMENTED", "submittedAt": "${now_iso}", "commit": {"oid": "cccc3333dddd4444"}, "body": "Found a blocking bug."}
      ]},
      "reviewThreads": {"nodes": [
        {
          "id": "T4", "isResolved": false, "isOutdated": false, "path": "pkg/store.go", "line": 12,
          "comments": {"nodes": [{"author": {"login": "chatgpt-codex-connector[bot]"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "cccc3333dddd4444"}, "body": "![P1 Badge](https://img.shields.io/badge/P1-red) Race condition under concurrent writes."}]}
        },
        {
          "id": "T5", "isResolved": false, "isOutdated": false, "path": "pkg/store.go", "line": 90,
          "comments": {"nodes": [{"author": {"login": "cursor-bugbot[bot]"}, "createdAt": "${now_iso}", "originalCommit": {"oid": "cccc3333dddd4444"}, "body": "Medium: missing coverage on error branch."}]}
        }
      ]}
    }
  ]
}
EOF

cat >"${WORK}/cache/github/acme__demo.papercuts.json" <<EOF
{
  "schema_version": 1,
  "issues": [
    {"number": 501, "title": "[papercut] preflight missed skip", "state": "OPEN", "body": "skill: executor-preflight\nMissed skipped live test."}
  ]
}
EOF

# 1. Aggregate auto-discovers cached reviews + papercuts for --repo offline.
bash "${ROOT}/scripts/debrief.sh" aggregate \
	--days 30 --cache-dir "${WORK}/cache" --log "${WORK}/hooks.jsonl" \
	--repo "${repo}" --out "${WORK}/agg.json" >/dev/null

python3 - "${WORK}/agg.json" <<'PY' && ok "aggregate auto-loads cached PR reviews + papercuts and joins sessions/skills" || no "aggregate auto-loads cached PR reviews + papercuts and joins sessions/skills"
import json, sys
d = json.load(open(sys.argv[1]))
rev = d["review_escapes"]
assert rev is not None, "review_escapes missing"
assert rev["prs_reviewed"] == 2, rev
assert rev["prs_with_real_escapes"] == 2, rev
assert rev["real_p1"] == 2, rev          # T1 (evidence-overclaim) + T4 (codex P1 race)
assert rev["real_p2"] == 1, rev          # T5 (cursor-bugbot Medium -> P2)
assert rev["timing_noise_p1"] == 2, rev  # T2 + T3 (CI pending / sandbox has no database)
assert rev["repeat_p1_timing"] == 1, rev
assert rev["threads_total"] == 5 and rev["threads_unanswered"] == 4, rev
assert rev["threads_unresolved_on_merged"] == 2, rev  # T1 + T3 on MERGED PR #101
assert rev["joined_prs"] == 2, rev       # PR #101 by branch, PR #102 by commit
assert set(rev["by_reviewer_source"].keys()) >= {"reviewd", "chatgpt-codex"}, rev["by_reviewer_source"]
assert rev["per_skill"]["executor-preflight"]["real_p1"] == 1, rev["per_skill"]
assert rev["per_skill"]["golang-engineering"]["real_p1"] == 1, rev["per_skill"]
assert d["papercuts"] is not None and d["papercuts"]["total_open"] == 1, d["papercuts"]
by_sk = {r["skill"]: r for r in d["skill_table"]}
assert by_sk["executor-preflight"]["escaped_p1"] == 1 and by_sk["executor-preflight"]["papercut_open"] == 1, by_sk
PY

# 2. Render HTML + terminal summary include PR review catches when loaded.
cat >"${WORK}/syn.json" <<'EOF'
{"at_a_glance":{"working":"ok","hindering":"escapes","quick_wins":"guards","ambitious":"loop"},"project_areas":[],"narrative_paragraphs":["test"],"key_insight":"test","wins_intro":"","big_wins":[],"friction_intro":"","friction_categories":[],"agents_md_additions":[],"features_to_try":[],"usage_patterns":[],"horizon_intro":"","horizon_workflows":[]}
EOF
summary_out="$(bash "${ROOT}/scripts/debrief.sh" render --aggregate "${WORK}/agg.json" --synthesis "${WORK}/syn.json" --out "${WORK}/report.html" --no-snapshot)"
if grep -q "Post-Push PR Review Catches" "${WORK}/report.html" && printf '%s' "${summary_out}" | grep -q "POST-PUSH PR REVIEW CATCHES"; then
	ok "HTML report and terminal summary render PR review escapes card"
else
	no "HTML report and terminal summary render PR review escapes card"
fi

# 3. --no-github-cache (and repos without cached GitHub data) stay 100% clean with zero clutter.
bash "${ROOT}/scripts/debrief.sh" aggregate \
	--days 30 --cache-dir "${WORK}/cache" --log "${WORK}/hooks.jsonl" \
	--repo "${repo}" --no-github-cache --out "${WORK}/agg-offline.json" >/dev/null
bash "${ROOT}/scripts/debrief.sh" render --aggregate "${WORK}/agg-offline.json" --synthesis "${WORK}/syn.json" --out "${WORK}/report-offline.html" --no-snapshot >/dev/null
python3 - "${WORK}/agg-offline.json" "${WORK}/report-offline.html" <<'PY' && ok "--no-github-cache leaves review_escapes/papercuts None and omits HTML card" || no "--no-github-cache leaves review_escapes/papercuts None and omits HTML card"
import json, sys
d = json.load(open(sys.argv[1]))
html = open(sys.argv[2]).read()
assert d["review_escapes"] is None and d["papercuts"] is None, (d["review_escapes"], d["papercuts"])
assert "Post-Push PR Review Catches" not in html, "HTML card leaked when no review data loaded"
PY

# 4. sync-github --best-effort fails open cleanly on a non-GitHub directory.
nogit="${WORK}/not-a-git-dir"
mkdir -p "${nogit}"
be_out="$(cd "${nogit}" && bash "${ROOT}/scripts/debrief.sh" sync-github --best-effort)"
if printf '%s' "${be_out}" | grep -q '"skipped": true'; then
	ok "sync-github --best-effort exits 0 with skipped=true outside GitHub repos"
else
	no "sync-github --best-effort exits 0 with skipped=true outside GitHub repos"
fi

printf '\ndebrief-reviews: %s passed, %s failed\n' "${passed}" "${failed}"
[ "${failed}" -eq 0 ]
