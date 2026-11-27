#!/usr/bin/env bash
# scripts/run-tests.sh — Run all debrief Python/shell/Node test suites.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

for t in scripts/tests/test-debrief*.sh scripts/tests/test-installer.sh; do
	echo "=== ${t} ==="
	bash "${t}"
done

echo "=== scripts/tests/test-opencode-plugin.mjs ==="
node --test scripts/tests/test-opencode-plugin.mjs

echo "ALL DEBRIEF TESTS PASSED"
