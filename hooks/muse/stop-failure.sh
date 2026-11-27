#!/usr/bin/env bash
# hooks/muse/stop-failure.sh — Muse Code StopFailure telemetry adapter.
# Delegates to hooks/stop-failure.sh with DEBRIEF_HARNESS=muse. Always exits 0.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_HOOK="${HOOK_DIR}/stop-failure.sh"
[ -x "${CORE_HOOK}" ] || exit 0

export DEBRIEF_HARNESS=muse
exec bash "${CORE_HOOK}"
