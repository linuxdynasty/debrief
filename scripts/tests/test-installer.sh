#!/usr/bin/env bash
# Hermetic tests for bin/debrief.mjs, lib/installer.mjs, Claude plugin manifests,
# and per-harness install/uninstall with hook preservation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI="${ROOT}/bin/debrief.mjs"

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

export HOME="${work}/home"
export XDG_DATA_HOME="${work}/xdg-data"
export XDG_CONFIG_HOME="${work}/xdg-config"
mkdir -p "${HOME}/.claude" "${HOME}/.codex" "${HOME}/.gemini/config" \
	"${XDG_CONFIG_HOME}/opencode" "${XDG_CONFIG_HOME}/muse" "${HOME}/.cursor"

# Seed pre-existing user hooks to verify non-destructive merge + uninstall.
cat >"${HOME}/.claude/settings.json" <<'EOF'
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo keep-claude"}]}
    ]
  }
}
EOF
cat >"${HOME}/.codex/hooks.json" <<'EOF'
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "echo keep-codex"}]}
    ]
  }
}
EOF
cat >"${HOME}/.gemini/config/hooks.json" <<'EOF'
{
  "other-suite": {
    "PreToolUse": [{"matcher": "run_command", "hooks": [{"type": "command", "command": "echo keep-agy"}]}]
  }
}
EOF

# 1. Validate manifests (.claude-plugin/marketplace.json, plugin.json, package.json).
python3 -B - "${ROOT}" <<'PY'
import json, os, sys
root = sys.argv[1]
mp = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
pl = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json")))
pkg = json.load(open(os.path.join(root, "package.json")))
assert mp["name"] == "debrief" and mp["plugins"][0]["name"] == "debrief"
assert pl["name"] == "debrief" and "./skills" in pl["skills"]
assert os.path.isfile(os.path.join(root, pl["hooks"].lstrip("./")))
assert pkg["name"] == "@linuxdynasty/debrief" and pkg["bin"]["debrief"] == "bin/debrief.mjs"
PY
echo "ok - Claude marketplace, plugin, and npm package manifests validate"

# 2. Install across all 6 harnesses with --with-hooks --copy (simulating npx staging).
node "${CLI}" install --all --with-hooks --copy >/dev/null
# Run a second time to verify idempotency (no duplicate hook entries).
node "${CLI}" install --all --with-hooks --copy >/dev/null

python3 -B - "${HOME}" "${XDG_CONFIG_HOME}" "${XDG_DATA_HOME}" <<'PY'
import json, os, sys
home, cfg, data = sys.argv[1:4]
expected_skills = [
    os.path.join(home, ".claude", "skills", "debrief", "SKILL.md"),
    os.path.join(home, ".codex", "skills", "debrief", "SKILL.md"),
    os.path.join(cfg, "opencode", "skill", "debrief", "SKILL.md"),
    os.path.join(home, ".gemini", "config", "skills", "debrief", "SKILL.md"),
    os.path.join(home, ".agents", "skills", "debrief", "SKILL.md"),
    os.path.join(home, ".cursor", "skills", "debrief", "SKILL.md"),
]
for p in expected_skills:
    assert os.path.isfile(p), f"missing installed skill: {p}"

# Staged runtime & ~/.local/bin/debrief exist.
assert os.path.isfile(os.path.join(data, "debrief", "runtime", "scripts", "debrief.sh"))
assert os.path.islink(os.path.join(home, ".local", "bin", "debrief"))

# Claude hooks merged non-destructively and idempotently.
cl = json.load(open(os.path.join(home, ".claude", "settings.json")))
assert len(cl["hooks"]["PostToolUse"]) == 2, cl["hooks"]["PostToolUse"]
assert len(cl["hooks"]["StopFailure"]) == 1, cl["hooks"]["StopFailure"]
assert "keep-claude" in json.dumps(cl)

# Codex hooks merged non-destructively.
cx = json.load(open(os.path.join(home, ".codex", "hooks.json")))
assert len(cx["hooks"]["SessionStart"]) == 1 and len(cx["hooks"]["PostToolUse"]) == 1, cx

# OpenCode V2 plugin rendered with concrete HOOKS_DIR.
oc_p = os.path.join(cfg, "opencode", "plugins", "debrief-telemetry.js")
oc_txt = open(oc_p).read()
assert "%%HOOKS_DIR%%" not in oc_txt and "debrief/runtime/hooks" in oc_txt

# Agy hooks added under separate 'debrief' key preserving 'other-suite'.
ag = json.load(open(os.path.join(home, ".gemini", "config", "hooks.json")))
assert "other-suite" in ag and "debrief" in ag

# Muse managed_hooks_path set cleanly.
mu = json.load(open(os.path.join(cfg, "muse", "settings.json")))
assert mu["managed_hooks_path"] == os.path.join(data, "debrief", "muse-hooks.json")
assert os.path.isfile(mu["managed_hooks_path"])
PY
echo "ok - install --all --with-hooks --copy installs skills, hooks, and staged runtime idempotently"

# 3. Doctor and pipeline forwarding work cleanly.
doc_out="$(node "${CLI}" doctor)"
echo "${doc_out}" | grep -q "skill=installed"
node "${CLI}" sessions --days 7 >/dev/null
echo "ok - doctor and pipeline subcommands run cleanly through bin/debrief.mjs"

# 4. Muse managed_hooks_path is never clobbered when owned by another tool.
cat >"${XDG_CONFIG_HOME}/muse/settings.json" <<'EOF'
{"schema_version": 1, "managed_hooks_path": "/custom/other/hooks.json"}
EOF
muse_out="$(node "${CLI}" install --harness muse --with-hooks)"
echo "${muse_out}" | grep -q "leaving it untouched"
python3 -B - "${XDG_CONFIG_HOME}/muse/settings.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["managed_hooks_path"] == "/custom/other/hooks.json", d
PY
echo "ok - Muse foreign managed_hooks_path is preserved untouched"

# 5. Uninstall removes debrief skills & hooks while preserving user hooks.
node "${CLI}" uninstall --all >/dev/null
python3 -B - "${HOME}" "${XDG_CONFIG_HOME}" <<'PY'
import json, os, sys
home, cfg = sys.argv[1:3]
assert not os.path.exists(os.path.join(home, ".claude", "skills", "debrief"))
assert not os.path.exists(os.path.join(cfg, "opencode", "plugins", "debrief-telemetry.js"))
cl = json.load(open(os.path.join(home, ".claude", "settings.json")))
assert len(cl["hooks"]["PostToolUse"]) == 1 and "keep-claude" in json.dumps(cl)
assert "StopFailure" not in cl["hooks"]
cx = json.load(open(os.path.join(home, ".codex", "hooks.json")))
assert len(cx["hooks"]["SessionStart"]) == 1 and "PostToolUse" not in cx["hooks"]
ag = json.load(open(os.path.join(home, ".gemini", "config", "hooks.json")))
assert "other-suite" in ag and "debrief" not in ag
PY
echo "ok - uninstall --all cleanly removes debrief skills & hooks while preserving user hooks"

# 6. DEBRIEF_DATA_DIR override does NOT relocate staged runtime or muse-hooks.json; DEBRIEF_RUNTIME_DIR does.
other_data="${work}/other-kit-data"
DEBRIEF_DATA_DIR="${other_data}" node "${CLI}" install --all --with-hooks --copy >/dev/null
python3 -B - "${HOME}" "${XDG_DATA_HOME}" "${other_data}" <<'PY'
import os, sys
home, xdg_data, other = sys.argv[1:4]
expected_runtime = os.path.join(xdg_data, "debrief", "runtime")
assert os.path.isfile(os.path.join(expected_runtime, "bin", "debrief.mjs"))
assert os.path.realpath(os.path.join(home, ".local", "bin", "debrief")) == os.path.realpath(
    os.path.join(expected_runtime, "bin", "debrief.mjs")
)
assert not os.path.exists(os.path.join(other, "runtime")), "runtime must not be staged inside DEBRIEF_DATA_DIR"
assert not os.path.exists(os.path.join(other, "muse-hooks.json")), "muse-hooks.json must not be written inside DEBRIEF_DATA_DIR"
PY
DEBRIEF_DATA_DIR="${other_data}" node "${CLI}" doctor | grep -q "data dir     : ${other_data}"
custom_rt="${work}/custom-runtime"
DEBRIEF_DATA_DIR="${other_data}" DEBRIEF_RUNTIME_DIR="${custom_rt}" node "${CLI}" install --harness claude --copy >/dev/null
test -f "${custom_rt}/bin/debrief.mjs"
DEBRIEF_DATA_DIR="${other_data}" node "${CLI}" uninstall --all >/dev/null
echo "ok - staged runtime stays under XDG_DATA_HOME/debrief/runtime even when DEBRIEF_DATA_DIR is overridden"

echo "PASS test-installer: 6 checks green"
