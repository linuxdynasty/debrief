# How to debrief your Pi sessions

This guide shows you how to install debrief for Pi and produce an operational
debrief report over your Pi sessions. You should already be able to use the Pi
coding agent and run commands in a terminal.

## 1. Install debrief for Pi

Run this to install the `/debrief` skill and the telemetry extension:

```bash
npx @linuxdynasty/debrief install --harness pi --with-hooks
```

Confirm by running `debrief doctor` and checking that `pi` is listed as a
detected harness.

If debrief reports a `PermissionError` that mentions `~/.local/share`, the
default data directory is not writable on your machine. Set a writable one
before running debrief:

```bash
export DEBRIEF_DATA_DIR="$HOME/.debrief"
```

Add that line to your shell profile so later sessions keep using it.

## 2. Run a debrief from inside Pi

Start a new Pi session and run:

```text
/debrief
```

Confirm by checking that the reply ends with a `file://` link to the generated
HTML report.

To scope the report, add the flags the skill accepts:

```text
/debrief for pi all time
/debrief for pi since 2026-09-01
/debrief for the current session
```

## 3. Run a debrief from the CLI over a custom transcript root

Use this path when your Pi sessions live somewhere debrief does not find by
default, such as an archive directory. The root resolution order is documented
in the [session root reference](pi-session-root-reference.md).

Discover the sessions first:

```bash
debrief sessions --harness pi --all-time --transcript-root ~/workspace/archive/2026/2026-09
```

Extract them and emit facet batches:

```bash
debrief prepare --harness pi --all-time \
  --transcript-root ~/workspace/archive/2026/2026-09
```

Write the semantic facets for each batch the prepare step emits. If you are
driving debrief from inside an agent, dispatch one fast model per batch and
submit each result with `cache-write`. If you are writing facets by hand, submit
the file the same way:

```bash
debrief cache-write batch-01-facets.json
```

Aggregate the results. `aggregate` does not accept `--transcript-root`, so pass
the session IDs from the prepare manifest through `--sessions-file` instead:

```bash
debrief aggregate --harness pi --all-time \
  --sessions-file session-ids.txt --out aggregate.json
```

Render the report:

```bash
debrief render --aggregate aggregate.json --synthesis synthesis.json
```

Confirm by opening the printed `file://` path and checking that the Wins,
Friction, and Horizon sections contain text rather than empty placeholders.

## 4. Verify the telemetry extension loaded

The extension writes to `skills-usage.jsonl` when a skill is read inside Pi. It
only runs after Pi starts, so restart Pi first.

Read a skill inside Pi, then run:

```bash
tail -5 "$DEBRIEF_DATA_DIR/skills-usage.jsonl"
```

Confirm by finding a line whose JSON contains `"harness": "pi"`.

You have a working debrief over your Pi sessions. See the
[session root reference](pi-session-root-reference.md) for the full list of
configuration variables and discovery rules.
