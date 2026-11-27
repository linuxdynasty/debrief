#!/usr/bin/env bash
# stop-failure.sh — StopFailure telemetry hook.
# Records a content-free `model-failure` event (category only, never details).
# Never blocks, never writes stdout, always exits 0.
set -uo pipefail

command -v python3 >/dev/null 2>&1 || exit 0
# shellcheck source=hooks/lib/telemetry-events.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/telemetry-events.sh" 2>/dev/null || exit 0

payload="$(cat)"
[ -n "${payload}" ] || exit 0

parsed="$(printf '%s' "${payload}" | python3 -B -c '
import json, re, sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d, dict):
    raise SystemExit(0)
def first(*keys, default=""):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return re.sub(r"\s+", "_", v.strip())
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
    return default
sid = first("session_id", "thread_id")
if not sid:
    raise SystemExit(0)
cat = first("failure_category", "category", "failureCategory", "error_category", default="unknown")
print(f"{sid}\t{cat}")
' 2>/dev/null)" || exit 0

[ -n "${parsed}" ] || exit 0
session_id="${parsed%%	*}"
category="${parsed#*	}"
[ -n "${session_id}" ] || exit 0
debrief_event "model-failure" "${session_id}" "category=${category:-unknown}"
exit 0
