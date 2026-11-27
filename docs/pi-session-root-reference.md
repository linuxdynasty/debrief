# Pi session root and discovery reference

This reference documents how debrief locates Pi sessions, which files count as
Pi sessions, and what the telemetry extension observes. It is part of the
debrief multi-harness pipeline.

## Session root resolution order

`debrief_extract_pi.py` resolves Pi session roots in this order. The first
candidate that resolves is used. Later candidates are added only as fallbacks.

| Order | Source | Value when unset |
|---|---|---|
| 1 | `PI_CODING_AGENT_SESSION_DIR` environment variable | skipped |
| 2 | `sessionDir` key in `<config>/settings.json` | skipped (only read when order 1 is unset) |
| 3 | `<config>/sessions` | always appended |
| 4 | `~/.pi/agent/sessions` | always appended |

`<config>` is `PI_CODING_AGENT_DIR` when set, otherwise `~/.pi/agent`.

A relative value in order 1 or order 2 resolves against the process working
directory, which makes a relative `sessionDir` store project-local.

Pi's own `--session-dir` flag is not observable from inside debrief. A store
that only that flag exposes is reached with debrief's `--transcript-root` flag,
which `sessions` and `prepare` accept and `aggregate` does not.

## Discovery markers

A file under a root is treated as a Pi session only when both conditions hold:

- The filename ends in `.jsonl`.
- At least one record in the first five non-empty lines matches one of these
  markers:
  - `type` is `session` and the record contains at least one of `version`,
    `cwd`, or `id`.
  - `type` is one of `model_change`, `thinking_level_change`, `branch_summary`,
    or `context_edit`.

Files that end in `.jsonl` but carry none of these markers are rejected. This
excludes foreign transcripts and Pi observer telemetry such as `obs-*.jsonl`.

## Session file naming

Session files use the form `<timestamp>_<id>.jsonl`, for example
`2026-09-24T120000.000Z_01a0d127-600b-7dc0-81d2-ba6becca3958.jsonl`.

`session_id_from_path` takes the `<id>` segment as the session ID. When the name
does not match the timestamp pattern, it strips the `.jsonl` suffix instead.

## Telemetry extension

The extension is `hooks/pi/debrief-telemetry.ts` in the source tree. The
installer copies it to `~/.pi/agent/extensions/debrief-telemetry.ts`.

| Event | Condition | Hook called | Payload |
|---|---|---|---|
| `tool_call` | read of a path ending in `SKILL.md` | `skill-loaded.sh` | `{"session_id", "tool_input": {"skill"}}` |
| `tool_execution_end` | `isError` is `true` | `stop-failure.sh` | `{"session_id", "category"}` |

Both hooks run with `DEBRIEF_HARNESS=pi` in the environment.

The extension fails open. It never throws. It kills a hook that runs past its
timeout, which defaults to 10000 ms and is overridden by
`DEBRIEF_PI_TIMEOUT_MS`. The hooks directory is resolved at install time and is
overridden by `DEBRIEF_HOOKS_DIR`.

## Configuration variables

| Variable | Default | Purpose |
|---|---|---|
| `PI_CODING_AGENT_DIR` | `~/.pi/agent` | Pi configuration directory |
| `PI_CODING_AGENT_SESSION_DIR` | *(none)* | Session directory override, first in resolution order |
| `DEBRIEF_DATA_DIR` | `$XDG_DATA_HOME/debrief` | Root for cache, reports, snapshots, and `skills-usage.jsonl` |
| `DEBRIEF_TELEMETRY_OFF` | `0` | Set to `1` to disable hook telemetry emission |
| `DEBRIEF_HOOKS_DIR` | *(install-time)* | Overrides the hooks directory the extension calls |
| `DEBRIEF_PI_TIMEOUT_MS` | `10000` | Overrides the extension hook timeout, in milliseconds |

## Related

- [How to debrief your Pi sessions](how-to-debrief-your-pi-sessions.md)
- The `/debrief` skill at `skills/debrief/SKILL.md`
