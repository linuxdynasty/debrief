#!/usr/bin/env bash
# Hermetic tests for scripts/check-release-changes.mjs release guard.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKER="${ROOT}/scripts/check-release-changes.mjs"

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

git -C "${work}" init -q
git -C "${work}" config user.name "Test"
git -C "${work}" config user.email "test@example.com"

mkdir -p "${work}/lib" "${work}/docs" "${work}/examples/screenshots" "${work}/skills/debrief" "${work}/.claude-plugin"
printf '{"name":"@test/pkg","version":"0.1.0","bin":{"debrief":"bin/debrief.mjs"}}\n' >"${work}/package.json"
printf '{"name":"debrief","version":"0.1.0"}\n' >"${work}/.claude-plugin/plugin.json"
printf 'export const x = 1;\n' >"${work}/lib/installer.mjs"
printf '# Skill\n' >"${work}/skills/debrief/SKILL.md"
printf '# Readme\n' >"${work}/README.md"
git -C "${work}" add .
git -C "${work}" commit -q -m "initial"
git -C "${work}" tag v0.1.0

# 1. Docs + images + version-only bump -> substantive=false (skip release).
printf 'updated docs\n' >>"${work}/README.md"
printf '# Guide\n' >"${work}/docs/guide.md"
printf 'fake-png-bytes' >"${work}/examples/screenshots/01.png"
printf '{"name":"@test/pkg","version":"0.1.1","bin":{"debrief":"bin/debrief.mjs"}}\n' >"${work}/package.json"
printf '{"name":"debrief","version":"0.1.1"}\n' >"${work}/.claude-plugin/plugin.json"
git -C "${work}" add .
git -C "${work}" commit -q -m "docs and images only"

out1="$(node "${CHECKER}" --cwd "${work}" --base v0.1.0 --head HEAD)"
python3 -B - "${out1}" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
assert d["substantive"] is False, d
assert d["realChanges"] == [], d
assert "README.md" in d["ignoredChanges"]
assert "examples/screenshots/01.png" in d["ignoredChanges"]
PY
echo "ok - docs, images, and version-only bump do not trigger a release"

# 2. Editing skills/debrief/SKILL.md counts as a real product change.
printf 'new rule\n' >>"${work}/skills/debrief/SKILL.md"
git -C "${work}" add skills/debrief/SKILL.md
git -C "${work}" commit -q -m "update skill"
out2="$(node "${CHECKER}" --cwd "${work}" --base v0.1.0 --head HEAD)"
python3 -B - "${out2}" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
assert d["substantive"] is True, d
assert d["realChanges"] == ["skills/debrief/SKILL.md"], d
PY
echo "ok - skills/debrief/SKILL.md edit triggers a release"

# 3. Real code change triggers a release.
git -C "${work}" tag v0.1.1
printf 'export const y = 2;\n' >>"${work}/lib/installer.mjs"
git -C "${work}" add lib/installer.mjs
git -C "${work}" commit -q -m "fix installer"
out3="$(node "${CHECKER}" --cwd "${work}" --base v0.1.1 --head HEAD)"
python3 -B - "${out3}" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
assert d["substantive"] is True, d
assert d["realChanges"] == ["lib/installer.mjs"], d
PY
echo "ok - code change triggers a release"

echo "PASS test-release-guard: 3 checks green"
