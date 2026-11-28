#!/usr/bin/env bash
# scripts/tests/test-debrief-fixture.sh — Guard the synthetic demo fixture.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB="${ROOT}/scripts/lib"
GEN="${LIB}/debrief_demo_fixture.py"
FIXTURES="${ROOT}/scripts/fixtures"
EXAMPLE="${ROOT}/examples/demo-sample-report.html"

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "ok - $1"; }
no() { FAIL=$((FAIL + 1)); echo "not ok - $1"; }

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

# 1. Deterministic: two runs must produce byte-identical JSON.
python3 -B "${GEN}" --out-dir "${work}/a" >/dev/null || no "fixture generator runs"
python3 -B "${GEN}" --out-dir "${work}/b" >/dev/null || no "fixture generator runs twice"
if diff -rq "${work}/a" "${work}/b" >/dev/null 2>&1; then
	ok "fixture is deterministic across runs"
else
	no "fixture is deterministic across runs"
fi

# 2. Committed fixture files match a fresh generation.
if diff -q "${work}/a/demo-aggregate.json" "${FIXTURES}/demo-aggregate.json" >/dev/null 2>&1 &&
	diff -q "${work}/a/demo-synthesis.json" "${FIXTURES}/demo-synthesis.json" >/dev/null 2>&1; then
	ok "committed fixture matches the generator"
else
	no "committed fixture matches the generator (run ${GEN} --out-dir scripts/fixtures)"
fi

# 3. The fixture renders, and the render carries the disclosure structure.
python3 -B "${GEN}" --out-dir "${work}/c" --html "${work}/demo.html" >/dev/null || no "fixture renders to HTML"
if python3 -B - "${work}/demo.html" "${EXAMPLE}" <<'PYEOF'
import re
import sys

html = open(sys.argv[1], encoding="utf-8").read()

# Group disclosure drives the whole navigation model.
groups = re.findall(r'<details class="group" id="(g-[a-z]+)"', html)
assert len(groups) >= 5, f"expected at least five disclosure groups, got {groups}"
assert groups[0] == "g-summary", f"summary must come first, got {groups}"

# Every in-page link must resolve to an element in the document.
ids = set(re.findall(r'\sid="([^"]+)"', html))
hrefs = set(re.findall(r'href="#([^"]+)"', html))
missing = sorted(h for h in hrefs if h not in ids)
assert not missing, f"dangling in-page links: {missing}"

# Nav links must target groups, not sections, so the target is never collapsed.
nav = re.search(r'<nav class="site-nav".*?</nav>', html, re.S).group(0)
nav_targets = set(re.findall(r'href="#(g-[a-z]+)"', nav))
assert nav_targets == set(groups), f"nav targets {nav_targets} != groups {set(groups)}"

# The stale masthead band must stay gone.
assert "--light-field" not in html, "masthead band token is still referenced"

# Row hover needs a token that both themes define and clearance for its edge.
assert html.count("--row-hover:") >= 2, "row hover token must be defined for light and dark"
assert "tbody tr:hover" in html, "table rows need a hover rule"
assert "th:first-child, td:first-child { padding-left: var(--s3); }" in html, "hover edge must not touch first-cell text"

# Disclosure must not shift the page, and nav selection must have one owner.
assert "scrollbar-gutter: stable" in html, "disclosure must reserve the scrollbar gutter"
assert "function setCurrentGroup(id)" in html, "nav needs a single current-group setter"
assert "setCurrentGroup(a.getAttribute('href').slice(1))" in html, "nav clicks must update the selected outline"

# Component spacing must start at zero and not be cancelled by inline margins.
assert re.search(r'\*,\s*\*::before,\s*\*::after\s*\{\s*box-sizing: border-box;\s*margin: 0;\s*padding: 0;\s*\}', html), "missing the universal margin and padding reset, including pseudo-elements"
assert "ul, ol { padding-inline-start: var(--s4); }" in html, "list indentation must be restored after the reset"
assert not re.search(r'class="chart-card"[^>]*style="[^"]*margin:0', html), "inline chart-card margins reset the shared vertical rhythm"
assert re.search(r'details\.note \{\s*position: relative;\s*display: inline-block;\s*margin: var\(--s3\) 0 var\(--s4\);', html), "notes need top and bottom separation"
assert "function watchNoteTooltips()" in html, "method notes need hover, click, and dismissal behavior"
assert 'html[data-tooltips="true"] details.note.tooltip-hover > p' in html, "method notes need a hover tooltip"
assert "summary.setAttribute('aria-describedby', content.id)" in html, "tooltip content must be associated with its trigger"

out = sys.argv[2]
if out:
    import hashlib
    fresh = hashlib.sha256(html.encode("utf-8")).hexdigest()
    try:
        committed = hashlib.sha256(open(out, encoding="utf-8").read().encode("utf-8")).hexdigest()
    except OSError:
        committed = ""
    if fresh != committed:
        print(f"examples/demo-sample-report.html is stale: regenerate with "
              f"python3 scripts/lib/debrief_demo_fixture.py --html examples/demo-sample-report.html", file=sys.stderr)
        sys.exit(2)
PYEOF
then
	ok "fixture render has groups, resolving anchors, and no stale band token"
else
	no "fixture render structure OR the committed example is stale"
fi

# 4. No absolute paths or external URLs leak into the synthetic fixture.
if python3 -B - "${FIXTURES}/demo-aggregate.json" "${FIXTURES}/demo-synthesis.json" <<'PYEOF'
import json, sys

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)

for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    for value in strings(document):
        assert not value.startswith(("/", "file:", "http:", "https:")), value
PYEOF
then
	ok "fixture contains no absolute paths or external URLs"
else
	no "fixture contains no absolute paths or external URLs"
fi

echo "PASS test-debrief-fixture: ${PASS} checks green, ${FAIL} failed"
[ "${FAIL}" -eq 0 ]
