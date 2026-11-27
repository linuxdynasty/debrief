#!/usr/bin/env bash
# telemetry-events.sh — sourced by debrief telemetry hooks, never run on its own.
#
# Appends one local-only, content-free JSONL event per call to
# $DEBRIEF_DATA_DIR/skills-usage.jsonl (default $XDG_DATA_HOME/debrief/skills-usage.jsonl),
# rotated at 5 MiB keeping one .1 spare.
#
# Fail-open contract: every failure path returns 0 silently.
# Opt-out: set DEBRIEF_TELEMETRY_OFF=1.
#
# debrief_event <type> <session_id> [key=value ...]
#   type:       skill-load | model-failure
#   session_id: any session string; sanitized then truncated to 12 chars.
#   key=value:  safe scalar detail fields (skill=..., category=...).

DEBRIEF_TELEMETRY_MAX_BYTES=5242880

debrief_event() { # type session_id [key=value ...]
	[ $# -ge 2 ] || return 0
	local ev_type="$1" raw_sid="$2"
	shift 2
	[ "${DEBRIEF_TELEMETRY_OFF:-0}" = "1" ] && return 0
	command -v python3 >/dev/null 2>&1 || return 0
	[ -n "${ev_type}" ] && [ -n "${raw_sid}" ] || return 0
	local harness="${DEBRIEF_HARNESS:-${KIT_HARNESS:-claude}}"
	local data_dir="${DEBRIEF_DATA_DIR:-${XDG_DATA_HOME:-${HOME:-}/.local/share}/${DEBRIEF_APP_NAME:-debrief}}"
	DEBRIEF_EV_TYPE="${ev_type}" DEBRIEF_EV_SID="${raw_sid}" \
	DEBRIEF_EV_DETAIL="$(printf '%s\n' "$@")" \
	DEBRIEF_EV_HARNESS="${harness}" \
	DEBRIEF_EV_DIR="${data_dir}" \
	DEBRIEF_EV_MAX="${DEBRIEF_TELEMETRY_MAX_BYTES}" python3 -B -c '
import datetime
import json
import os
import re

try:
    logdir = os.path.expanduser(os.environ.get("DEBRIEF_EV_DIR") or "")
    if not logdir:
        raise SystemExit(0)
    os.makedirs(logdir, exist_ok=True)
    log = os.path.join(logdir, "skills-usage.jsonl")
    try:
        if os.path.getsize(log) > int(os.environ.get("DEBRIEF_EV_MAX") or 5242880):
            try:
                os.replace(log, log + ".1")
            except OSError:
                pass
    except OSError:
        pass
    detail = {}
    for line in (os.environ.get("DEBRIEF_EV_DETAIL") or "").splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", key):
            continue
        words = value.split()
        if key == "skills":
            items = [re.sub(r"[^A-Za-z0-9._-]", "", w)[:40] for w in words]
            items = [w for w in items if w]
            if items:
                detail[key] = items
        elif len(words) == 1 and re.fullmatch(r"[0-9]+", words[0]):
            detail[key] = int(words[0])
        elif len(words) == 1:
            clean = re.sub(r"[^A-Za-z0-9._-]", "", words[0])[:64]
            if clean:
                detail[key] = clean
    sid = re.sub(r"[^A-Za-z0-9._-]", "-", os.environ.get("DEBRIEF_EV_SID") or "")[:12]
    if not sid:
        raise SystemExit(0)
    event = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "session": sid,
        "harness": re.sub(r"[^a-z]", "", (os.environ.get("DEBRIEF_EV_HARNESS") or "claude").lower())[:16] or "claude",
        "type": re.sub(r"[^a-z-]", "", os.environ.get("DEBRIEF_EV_TYPE") or "")[:32],
        "detail": detail,
    }
    if not event["type"]:
        raise SystemExit(0)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
except SystemExit:
    pass
except Exception:
    pass
' 2>/dev/null || true
	return 0
}
