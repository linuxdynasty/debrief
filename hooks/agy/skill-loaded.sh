#!/usr/bin/env bash
# hooks/agy/skill-loaded.sh — Antigravity (agy) PostToolUse telemetry adapter
# for read_file|view_file on SKILL.md. Translates camelCase agy envelopes to
# hooks/skill-loaded.sh with DEBRIEF_HARNESS=agy. Always exits 0 with {}.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_HOOK="${HOOK_DIR}/skill-loaded.sh"
[ -x "${CORE_HOOK}" ] || { printf '{}\n'; exit 0; }
command -v python3 >/dev/null 2>&1 || { printf '{}\n'; exit 0; }

export DEBRIEF_HARNESS=agy
payload="$(cat)"
if [ -n "${payload}" ]; then
	normalized="$(printf '%s' "${payload}" | python3 -B -c '
import json, re, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d, dict):
    raise SystemExit(0)
sid = str(d.get("sessionId") or d.get("conversationId") or d.get("session_id") or "").strip()
if not sid:
    raise SystemExit(0)
ti = d.get("toolInput") or d.get("tool_input") or d.get("arguments") or {}
if isinstance(ti, str):
    try:
        ti = json.loads(ti)
    except Exception:
        ti = {}
if not isinstance(ti, dict):
    ti = {}
path = ""
for key in ("Path", "path", "filePath", "file_path", "AbsolutePath"):
    v = ti.get(key)
    if isinstance(v, str) and v.strip():
        path = v.strip()
        break
m = re.search(r"(?:^|[/\\])([A-Za-z0-9._-]+)[/\\]SKILL\.md$", path)
if not m:
    raise SystemExit(0)
print(json.dumps({
    "hook_event_name": "PostToolUse",
    "tool_name": "Skill",
    "session_id": sid,
    "tool_input": {"skill": m.group(1)},
}, separators=(",", ":")))
' 2>/dev/null)" || normalized=""
	if [ -n "${normalized}" ]; then
		printf '%s' "${normalized}" | bash "${CORE_HOOK}" >/dev/null 2>&1 || true
	fi
fi
printf '{}\n'
exit 0
