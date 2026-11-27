#!/usr/bin/env bash
# hooks/codex/skill-loaded.sh — Codex PostToolUse telemetry adapter.
# Translates Codex skill tool calls or SKILL.md reads to hooks/skill-loaded.sh
# with DEBRIEF_HARNESS=codex. Never blocks, always exits 0.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_HOOK="${HOOK_DIR}/skill-loaded.sh"
[ -x "${CORE_HOOK}" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

export DEBRIEF_HARNESS=codex
payload="$(cat)"
[ -n "${payload}" ] || exit 0

normalized="$(printf '%s' "${payload}" | python3 -B -c '
import json, re, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d, dict):
    raise SystemExit(0)
sid = str(d.get("session_id") or d.get("thread_id") or "").strip()
if not sid:
    raise SystemExit(0)
ti = d.get("tool_input")
if isinstance(ti, str):
    try:
        ti = json.loads(ti)
    except Exception:
        ti = {"raw": ti}
if not isinstance(ti, dict):
    ti = {}
skill = ""
tname = str(d.get("tool_name") or "").lower()
for key in ("skill", "skill_name", "name", "id"):
    v = ti.get(key)
    if isinstance(v, str) and v.strip():
        if key in ("skill", "skill_name") or tname in ("skill", "read_skill"):
            skill = v.strip().split(":")[-1]
            break
if not skill:
    blob = " ".join(str(v) for v in ti.values() if isinstance(v, str))
    m = re.search(r"(?:^|[/\\\s])([A-Za-z0-9._-]+)[/\\]SKILL\.md", blob)
    if m:
        skill = m.group(1)
if not skill:
    raise SystemExit(0)
print(json.dumps({
    "hook_event_name": "PostToolUse",
    "tool_name": "Skill",
    "session_id": sid,
    "tool_input": {"skill": skill},
}, separators=(",", ":")))
' 2>/dev/null)" || exit 0

[ -n "${normalized}" ] || exit 0
printf '%s' "${normalized}" | bash "${CORE_HOOK}"
exit 0
