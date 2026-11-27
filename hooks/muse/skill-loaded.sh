#!/usr/bin/env bash
# hooks/muse/skill-loaded.sh — Muse Code PostToolUse (read_skill) telemetry adapter.
# Delegates to hooks/skill-loaded.sh with DEBRIEF_HARNESS=muse. Always exits 0.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_HOOK="${HOOK_DIR}/skill-loaded.sh"
[ -x "${CORE_HOOK}" ] || exit 0

export DEBRIEF_HARNESS=muse
exec bash "${CORE_HOOK}"
