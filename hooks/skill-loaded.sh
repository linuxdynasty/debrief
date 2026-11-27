#!/usr/bin/env bash
# skill-loaded.sh — PostToolUse telemetry hook for skill invocations.
# Records a content-free `skill-load` event in skills-usage.jsonl.
# Never blocks, never writes stdout, always exits 0.
set -u

# shellcheck source=hooks/lib/telemetry-events.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/telemetry-events.sh" 2>/dev/null || exit 0

INPUT="$(cat)"
[ -n "${INPUT}" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

PARSED="$(printf '%s' "${INPUT}" | python3 -B -c '
import json, re, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d, dict):
    raise SystemExit(0)
sid = str(d.get("session_id") or d.get("thread_id") or "").strip()[:12]
if not sid:
    raise SystemExit(0)
ti = d.get("tool_input") or {}
if isinstance(ti, str):
    try:
        ti = json.loads(ti)
    except Exception:
        ti = {}
if not isinstance(ti, dict):
    ti = {}
name = ""
for key in ("skill", "skill_name", "name"):
    v = ti.get(key)
    if isinstance(v, str) and v.strip():
        name = v.strip().split(":")[-1]
        break
if not name:
    for key in ("file_path", "filePath", "path", "Path"):
        v = ti.get(key)
        if isinstance(v, str):
            m = re.search(r"(?:^|[/\\])([A-Za-z0-9._-]+)[/\\]SKILL\.md$", v)
            if m:
                name = m.group(1)
                break
safe = re.sub(r"[^a-zA-Z0-9._-]", "", name)[:40]
if safe:
    print(f"{sid}\t{safe}")
' 2>/dev/null)" || exit 0

[ -n "${PARSED}" ] || exit 0
SID="${PARSED%%	*}"
SAFE="${PARSED#*	}"
[ -n "${SID}" ] && [ -n "${SAFE}" ] || exit 0
debrief_event "skill-load" "${SID}" "skill=${SAFE}"
exit 0
