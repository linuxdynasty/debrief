#!/usr/bin/env bash
# Hermetic tests for the Pi harness: discovery, extraction, scoping, session-root
# resolution, telemetry sink contract, and the install lifecycle.
# Every assertion traces to a criterion in output/verification-strategy.md.
set -uo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEBRIEF="${KIT_DIR}/scripts/debrief.sh"
CLI="${KIT_DIR}/bin/debrief.mjs"

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
export XDG_DATA_HOME="${work}/xdg"
export HOME="${work}/home"
export XDG_CONFIG_HOME="${work}/config"
mkdir -p "${XDG_DATA_HOME}" "${HOME}" "${XDG_CONFIG_HOME}"
unset PI_CODING_AGENT_DIR PI_CODING_AGENT_SESSION_DIR PI_SESSION_ID PI_SESSION_FILE

passed=0
failed=0
ok() {
	printf 'ok - %s\n' "$1"
	passed=$((passed + 1))
}
no() {
	printf 'not ok - %s\n' "$1"
	failed=$((failed + 1))
}

SID="aabbccdd-1111-2222-3333-444444444444"
PI_ROOT="${HOME}/.pi/agent/sessions"
PROJ="${PI_ROOT}/--repo-pioneer--"
mkdir -p "${PROJ}"

# --- Fixture: one Pi session exercising every entry branch ---
cat >"${PROJ}/2026-11-15T10-00-00-000Z_${SID}.jsonl" <<'EOF'
{"type":"session","version":3,"id":"aabbccdd-1111-2222-3333-444444444444","timestamp":"2026-11-15T10:00:00.000Z","cwd":"/repo/pioneer"}
{"type":"model_change","id":"e2","parentId":"e1","timestamp":"2026-11-15T10:00:00.500Z","provider":"deepseek","modelId":"deepseek-v4-flash"}
{"type":"message","id":"e3","parentId":"e2","timestamp":"2026-11-15T10:00:01.000Z","message":{"role":"user","content":[{"type":"text","text":"Audit the billing retry loop"}]}}
{"type":"message","id":"e4","parentId":"e3","timestamp":"2026-11-15T10:00:02.000Z","message":{"role":"assistant","model":"deepseek-v4-flash","usage":{"input":1000,"output":100,"cacheRead":400,"cacheWrite":0,"totalTokens":1500},"content":[{"type":"text","text":"Reading the skill."},{"type":"toolCall","id":"call_1","name":"read","arguments":{"path":"/repo/skills/pioneer-rigor/SKILL.md"}}]}}
{"type":"message","id":"e5","parentId":"e4","timestamp":"2026-11-15T10:00:03.000Z","message":{"role":"toolResult","toolCallId":"call_1","toolName":"read","isError":false,"content":[{"type":"text","text":"skill body"}]}}
{"type":"message","id":"e6","parentId":"e5","timestamp":"2026-11-15T10:00:04.000Z","message":{"role":"assistant","model":"deepseek-v4-flash","content":[{"type":"toolCall","id":"call_2","name":"bash","arguments":{"command":"git commit -m wip"}}]}}
{"type":"message","id":"e7","parentId":"e6","timestamp":"2026-11-15T10:00:05.000Z","message":{"role":"toolResult","toolCallId":"call_2","toolName":"bash","isError":true,"content":[{"type":"text","text":"exit status 1"}]}}
{"type":"model_change","id":"e8","parentId":"e7","timestamp":"2026-11-15T10:00:06.000Z","provider":"deepseek","modelId":"deepseek-v4-pro"}
{"type":"message","id":"e9","parentId":"e8","timestamp":"2026-11-15T10:00:07.000Z","message":{"role":"user","content":[{"type":"text","text":"Now fix the retry cap"}]}}
{"type":"label","id":"e10","parentId":"e9","timestamp":"2026-11-15T10:00:08.000Z","targetId":"e4","label":"skill-read"}
{"type":"thinking_level_change","id":"e11","parentId":"e10","timestamp":"2026-11-15T10:00:09.000Z","thinkingLevel":"high"}
{"type":"message","id":"e12","parentId":"e11","timestamp":"2026-11-15T10:00:10.000Z","message":{"role":"assistant","model":"deepseek-v4-pro","usage":{"input":500,"output":50,"cacheRead":0,"cacheWrite":0,"totalTokens":550},"content":[{"type":"text","text":"Raised the retry cap to 5."}]}}
EOF

# A foreign transcript in the Pi root must never be claimed as a Pi session.
cat >"${PROJ}/2026-11-15T11-00-00-000Z_foreign.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":"claude style transcript"},"timestamp":"2026-11-15T11:00:00.000Z","sessionId":"cl-foreign"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"true"}}]},"timestamp":"2026-11-15T11:00:01.000Z","sessionId":"cl-foreign"}
EOF

PREP="${work}/prep.json"
bash "${DEBRIEF}" prepare --all-time --harness pi \
	--cache-dir "${work}/cache" --out-dir "${work}/batches" >"${PREP}" 2>"${work}/prep.err" &&
	rc=0 || rc=1
META="${work}/cache/meta/pi__${SID}.json"

if [ "${rc}" -eq 0 ] && [ -f "${META}" ]; then
	python3 - "${META}" "${PREP}" <<'PYEOF' && ok "V1/V3/V16 discover and extract one Pi session with header id, cwd and schema version" || no "V1/V3/V16 discover and extract one Pi session with header id, cwd and schema version"
import json, sys
m = json.load(open(sys.argv[1]))
p = json.load(open(sys.argv[2]))
assert m["id"] == "aabbccdd-1111-2222-3333-444444444444", m["id"]
assert m["project"] == "/repo/pioneer", m["project"]
assert m["harness"] == "pi" and m["meta_version"] == 4, m
assert p["sessions_discovered"] == 1, p
PYEOF
else
	no "V1/V3/V16 discover and extract one Pi session with header id, cwd and schema version"
fi

if [ -f "${META}" ]; then
	python3 - "${META}" <<'PYEOF' && ok "V2 counts user prompts and tool calls exactly once each" || no "V2 counts user prompts and tool calls exactly once each"
import json, sys
m = json.load(open(sys.argv[1]))
assert m["prompts"] == 2, m["prompts"]
assert m["tool_calls"] == 2, m["tool_calls"]
assert m["tools"] == {"read": 1, "bash": 1}, m["tools"]
assert m["assistant_messages"] == 3, m["assistant_messages"]
PYEOF
	python3 - "${META}" <<'PYEOF' && ok "V4 reports the model from the latest model_change, not the first" || no "V4 reports the model from the latest model_change, not the first"
import json, sys
m = json.load(open(sys.argv[1]))
assert m["model"] == "deepseek/deepseek-v4-pro", m["model"]
PYEOF
	python3 - "${META}" <<'PYEOF' && ok "V5 sums input/output tokens across assistant usage records" || no "V5 sums input/output tokens across assistant usage records"
import json, sys
m = json.load(open(sys.argv[1]))
assert m["tokens_in"] == 1500, m["tokens_in"]
assert m["tokens_out"] == 150, m["tokens_out"]
assert m["tokens_cache_read"] == 400, m["tokens_cache_read"]
PYEOF
	python3 - "${META}" <<'PYEOF' && ok "V6 counts only isError toolResult entries, keyed by tool name" || no "V6 counts only isError toolResult entries, keyed by tool name"
import json, sys
m = json.load(open(sys.argv[1]))
assert m["errors"] == {"bash": 1}, m["errors"]
assert sum(m["errors"].values()) == 1, m
PYEOF
	python3 - "${META}" <<'PYEOF' && ok "V7 detects a skill load from a SKILL.md read path" || no "V7 detects a skill load from a SKILL.md read path"
import json, sys
m = json.load(open(sys.argv[1]))
assert m["skill_loads"] == ["pioneer-rigor"], m["skill_loads"]
PYEOF
	python3 - "${work}/cache/meta" <<'PYEOF' && ok "V1 guard rejects a foreign transcript sharing the Pi root" || no "V1 guard rejects a foreign transcript sharing the Pi root"
import glob, json, os, sys
metas = glob.glob(os.path.join(sys.argv[1], "pi__*.json"))
names = sorted(os.path.basename(p) for p in metas)
assert len(metas) == 1, names
assert names[0] == "pi__aabbccdd-1111-2222-3333-444444444444.json", names
PYEOF
fi

if bash "${DEBRIEF}" sessions --harness p --all-time >/dev/null 2>&1; then
	no "V8 rejects an unknown --harness value with exit 2"
else
	[ "$?" -eq 2 ] && ok "V8 rejects an unknown --harness value with exit 2" || no "V8 rejects an unknown --harness value with exit 2"
fi

if PI_SESSION_ID="${SID}" bash "${DEBRIEF}" prepare --current --harness pi \
	--cache-dir "${work}/cache2" --out-dir "${work}/b2" >"${work}/cur.json" 2>/dev/null; then
	python3 - "${work}/cur.json" <<'PYEOF' && ok "V9 resolves --current from PI_SESSION_ID" || no "V9 resolves --current from PI_SESSION_ID"
import json, sys
p = json.load(open(sys.argv[1]))
assert p["scope"]["session_ids"] == ["aabbccdd-1111-2222-3333-444444444444"], p["scope"]
PYEOF
else
	no "V9 resolves --current from PI_SESSION_ID"
fi

# --- V17 malformed lines are counted, not dropped silently ---
BAD="${PROJ}/2026-11-15T12-00-00-000Z_badc0de0-0000-0000-0000-000000000000.jsonl"
{
	printf '%s\n' '{"type":"session","version":3,"id":"badc0de0-0000-0000-0000-000000000000","timestamp":"2026-11-15T12:00:00.000Z","cwd":"/repo/bad"}'
	printf '%s\n' '{ this is not json'
	printf '%s\n' '{"type":"message","id":"m1","parentId":null,"timestamp":"2026-11-15T12:00:01.000Z","message":{"role":"user","content":"survive the corrupt line"}}'
	printf '%s\n' '{"type":"message","id":"m2","parentId":"m1","timestamp":"2026-11-15T12:00:02.000Z","message":{"role":"assistant","content":[{"type":"toolCall","id":"c1","name":"read","arguments":{"path":"/repo/bad/app.py"}},{"type":"toolCall","id":"c2","name":"bash","arguments":{"command":"ls"}},{"type":"toolCall","id":"c3","name":"bash","arguments":{"command":"pwd"}}]}}'
	printf '%s\n' 'garbage without braces'
	printf '%s\n' '{"type":"message","id":"m3","parentId":"m2","timestamp":"2026-11-15T12:00:03.000Z","message":{"role":"toolResult","toolCallId":"c2","toolName":"bash","isError":true,"content":[{"type":"text","text":"boom"}]}}'
} >"${BAD}"

bash "${DEBRIEF}" prepare --all-time --harness pi \
	--cache-dir "${work}/cache3" --out-dir "${work}/b3" >/dev/null 2>&1
BADMETA="${work}/cache3/meta/pi__badc0de0-0000-0000-0000-000000000000.json"
if [ -f "${BADMETA}" ]; then
	python3 - "${BADMETA}" "${work}/b3" <<'PYEOF' && ok "V17 skips malformed lines, keeps the valid prompt, and reports the count" || no "V17 skips malformed lines, keeps the valid prompt, and reports the count"
import json, sys, os, glob
m = json.load(open(sys.argv[1]))
assert m["prompts"] == 1, m["prompts"]
found = None
for f in glob.glob(os.path.join(sys.argv[2], "batch-*.json")):
    for d in json.load(open(f))["digests"]:
        if d["session_id"].startswith("badc0de0"):
            found = d
assert found is not None, "digest missing"
assert found["malformed_lines"] == 2, found["malformed_lines"]
PYEOF
else
	no "V17 skips malformed lines, keeps the valid prompt, and reports the count"
fi

# --- V18 a missing session root yields zero sessions, not a crash ---
if HOME="${work}/empty-home" bash "${DEBRIEF}" prepare --all-time --harness pi \
	--cache-dir "${work}/cache4" --out-dir "${work}/b4" >"${work}/empty.json" 2>/dev/null; then
	python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["sessions_discovered"]==0, p' \
		"${work}/empty.json" && ok "V18 a missing Pi session root yields zero sessions and never crashes" ||
		no "V18 a missing Pi session root yields zero sessions and never crashes"
else
	no "V18 a missing Pi session root yields zero sessions and never crashes"
fi

# --- V23a an absolute sessionDir setting is discovered ---
ALT="${work}/alt-sessions/--repo-alt--"
mkdir -p "${ALT}" "${HOME}/.pi/agent"
cat >"${HOME}/.pi/agent/settings.json" <<'EOF'
{"sessionDir": "%ALT%"}
EOF
sed -i.bak "s|%ALT%|${work}/alt-sessions|" "${HOME}/.pi/agent/settings.json"
rm -f "${HOME}/.pi/agent/settings.json.bak"
ALT_ID="feedface-0000-1111-2222-333344445555"
cat >"${ALT}/2026-11-16T09-00-00-000Z_${ALT_ID}.jsonl" <<'EOF'
{"type":"session","version":3,"id":"feedface-0000-1111-2222-333344445555","timestamp":"2026-11-16T09:00:00.000Z","cwd":"/repo/alt"}
{"type":"message","id":"a1","parentId":null,"timestamp":"2026-11-16T09:00:01.000Z","message":{"role":"user","content":"session lives outside the default root"}}
EOF

bash "${DEBRIEF}" prepare --all-time --harness pi \
	--cache-dir "${work}/cache5" --out-dir "${work}/b5" >"${work}/alt.json" 2>/dev/null
if [ -f "${work}/cache5/meta/pi__${ALT_ID}.json" ]; then
	ok "V23 supports an absolute sessionDir setting for the session root"
else
	no "V23 supports an absolute sessionDir setting for the session root"
fi

# --- V23b a relative sessionDir resolves against the invoking cwd ---
REL_PROJ="${work}/relproj"
mkdir -p "${REL_PROJ}/.pi/sessions"
REL_ID="cafebabe-1111-2222-3333-444455556666"
cat >"${REL_PROJ}/.pi/sessions/2026-11-17T08-00-00-000Z_${REL_ID}.jsonl" <<'EOF'
{"type":"session","version":3,"id":"cafebabe-1111-2222-3333-444455556666","timestamp":"2026-11-17T08:00:00.000Z","cwd":"/repo/relproj"}
{"type":"message","id":"r1","parentId":null,"timestamp":"2026-11-17T08:00:01.000Z","message":{"role":"user","content":"project-local store"}}
EOF
cat >"${HOME}/.pi/agent/settings.json" <<'EOF'
{"sessionDir": ".pi/sessions"}
EOF

( cd "${REL_PROJ}" && bash "${DEBRIEF}" prepare --all-time --harness pi \
	--cache-dir "${work}/cache6" --out-dir "${work}/b6" >/dev/null 2>&1 )
if [ -f "${work}/cache6/meta/pi__${REL_ID}.json" ]; then
	ok "V23 resolves a relative sessionDir against the cwd so project-local stores are found"
else
	no "V23 resolves a relative sessionDir against the cwd so project-local stores are found"
fi
rm -f "${HOME}/.pi/agent/settings.json"

# --- V20 telemetry sink contract: harness tag and category sanitization ---
TEL="${work}/tel"
mkdir -p "${TEL}"
printf '%s' "{\"session_id\":\"${SID}\",\"tool_input\":{\"skill\":\"debrief\"}}" |
	DEBRIEF_DATA_DIR="${TEL}" DEBRIEF_HARNESS=pi bash "${KIT_DIR}/hooks/skill-loaded.sh"
printf '%s' "{\"session_id\":\"${SID}\",\"category\":\"bash\"}" |
	DEBRIEF_DATA_DIR="${TEL}" DEBRIEF_HARNESS=pi bash "${KIT_DIR}/hooks/stop-failure.sh"
python3 - "${TEL}/skills-usage.jsonl" <<'PYEOF' && ok "V14/V20 telemetry records pi-tagged skill-load and model-failure events" || no "V14/V20 telemetry records pi-tagged skill-load and model-failure events"
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
assert {r["type"] for r in rows} == {"skill-load", "model-failure"}, rows
assert all(r["harness"] == "pi" for r in rows), rows
assert [r for r in rows if r["type"] == "model-failure"][0]["detail"]["category"] == "bash", rows
PYEOF

# --- V13 telemetry opt-out writes nothing ---
TEL2="${work}/tel-optout"
mkdir -p "${TEL2}"
printf '%s' "{\"session_id\":\"${SID}\",\"tool_input\":{\"skill\":\"debrief\"}}" |
	DEBRIEF_DATA_DIR="${TEL2}" DEBRIEF_TELEMETRY_OFF=1 DEBRIEF_HARNESS=pi bash "${KIT_DIR}/hooks/skill-loaded.sh"
if [ -s "${TEL2}/skills-usage.jsonl" ]; then
	no "V13 DEBRIEF_TELEMETRY_OFF suppresses the event"
else
	ok "V13 DEBRIEF_TELEMETRY_OFF suppresses the event"
fi

# --- V22 detection requires the pi directory to exist ---
mkdir -p "${work}/nopi"
DETECT_NONE="$(HOME="${work}/nopi" node -e "
import('${KIT_DIR}/lib/installer.mjs').then(m => process.stdout.write(JSON.stringify(m.detectHarnesses())))")"
mkdir -p "${work}/nopi/.pi/agent/sessions"
DETECT_PI="$(HOME="${work}/nopi" node -e "
import('${KIT_DIR}/lib/installer.mjs').then(m => process.stdout.write(JSON.stringify(m.detectHarnesses())))")"
if [ "${DETECT_NONE}" = "[]" ] && [ "${DETECT_PI}" = '["pi"]' ]; then
	ok "V22 detects Pi only when its agent directory exists"
else
	no "V22 detects Pi only when its agent directory exists"
fi

# --- V10/V12 install then uninstall is a clean round trip ---
IH="${work}/install-home"
mkdir -p "${IH}/.pi/agent/skills/keepme"
printf 'keep me\n' >"${IH}/.pi/agent/skills/keepme/SKILL.md"
HOME="${IH}" node "${CLI}" install --harness pi --with-hooks >"${work}/inst.log" 2>&1 &&
	installed=1 || installed=0
if [ "${installed}" -eq 1 ] &&
	[ -f "${IH}/.pi/agent/skills/debrief/SKILL.md" ] &&
	[ -f "${IH}/.pi/agent/extensions/debrief-telemetry.ts" ] &&
	! grep -q '%%HOOKS_DIR%%' "${IH}/.pi/agent/extensions/debrief-telemetry.ts" &&
	[ -f "${IH}/.pi/agent/skills/keepme/SKILL.md" ]; then
	ok "V10 installs the skill and a rendered extension without clobbering a sibling skill"
else
	no "V10 installs the skill and a rendered extension without clobbering a sibling skill"
fi

HOME="${IH}" node "${CLI}" install --harness claude >/dev/null 2>&1
HOME="${IH}" node "${CLI}" uninstall --harness pi >/dev/null 2>&1
if [ ! -e "${IH}/.pi/agent/skills/debrief" ] &&
	[ ! -e "${IH}/.pi/agent/extensions/debrief-telemetry.ts" ] &&
	[ -f "${IH}/.pi/agent/skills/keepme/SKILL.md" ] &&
	[ -e "${IH}/.claude/skills/debrief" ]; then
	ok "V12 uninstall removes only Pi artifacts and leaves other harnesses intact"
else
	no "V12 uninstall removes only Pi artifacts and leaves other harnesses intact"
fi

# --- V21 a filesystem without symlink support still installs ---
CH="${work}/copy-home"
mkdir -p "${CH}"
cat >"${work}/nosymlink.mjs" <<EOF
import fs from "node:fs";
fs.symlinkSync = () => { const e = new Error("Operation not supported"); e.code = "EPERM"; throw e; };
const { runInstall } = await import("${KIT_DIR}/lib/installer.mjs");
process.exit(runInstall("${KIT_DIR}", ["--harness", "pi", "--copy"]));
EOF
if HOME="${CH}" node "${work}/nosymlink.mjs" >/dev/null 2>&1 &&
	[ -f "${CH}/.pi/agent/skills/debrief/SKILL.md" ]; then
	ok "V21 falls back to a copy when symlink is unsupported"
else
	no "V21 falls back to a copy when symlink is unsupported"
fi

if [ "${failed}" -gt 0 ]; then
	printf 'FAIL debrief-pi: %d of %d checks failed\n' "${failed}" "$((passed + failed))" >&2
	exit 1
fi
printf 'PASS debrief-pi: %d checks green\n' "${passed}"
