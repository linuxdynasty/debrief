#!/usr/bin/env node
// bin/debrief.mjs — Zero-dependency CLI for @linuxdynasty/debrief.
// Supports both the multi-harness debrief pipeline and universal per-harness installation.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runDoctor, runInstall } from "../lib/installer.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PKG_ROOT = path.resolve(__dirname, "..");

const PIPELINE_CMDS = new Set([
  "sessions",
  "prepare",
  "cache-write",
  "aggregate",
  "diff",
  "render",
  "summary",
]);

function readVersion() {
  try {
    const pkg = JSON.parse(
      fs.readFileSync(path.join(PKG_ROOT, "package.json"), "utf8"),
    );
    return pkg.version || "0.0.0";
  } catch {
    return "0.0.0";
  }
}

function printHelp() {
  const v = readVersion();
  process.stdout.write(`debrief v${v} — Multi-harness operational debrief for AI coding agents

Usage:
  debrief install [options]      Install /debrief skill (and optional telemetry hooks) into harnesses
  debrief uninstall [options]    Remove debrief skill and telemetry hooks from harnesses
  debrief doctor                 Check detected harnesses, installed skills/hooks, and data paths

Pipeline commands:
  debrief sessions [opts]        List discoverable sessions across harnesses
  debrief prepare [opts]         Extract Stage 1 metadata & queue Stage 2 facet batches
  debrief cache-write [opts]     Validate & store Stage 2 facet JSON records
  debrief aggregate [opts]       Merge sessions, hooks, git change-points, Pareto fronts & diff
  debrief diff [opts]            Compare two snapshots or snapshot vs aggregate
  debrief render [opts]          Render offline interactive HTML report + human-legible summary (--json for paths)
  debrief summary [opts]         Print a human-legible terminal summary from aggregate (+ synthesis) JSON

Install options:
  --harness <list|all>           Harnesses: claude, codex, opencode, agy, muse, cursor (default: auto-detect)
  --all                          Install into all 6 supported harnesses
  --with-hooks                   Also install lightweight content-free skill-load & stop-failure hooks
  --copy                         Stage runtime into ~/.local/share/debrief/runtime (auto-enabled under npx)
  --dry-run                      Preview changes without writing files

Examples:
  npx @linuxdynasty/debrief install --with-hooks
  npx @linuxdynasty/debrief install --harness claude,codex,opencode --with-hooks
  npx @linuxdynasty/debrief doctor
  npx @linuxdynasty/debrief sessions --days 14 --limit 20
  npx @linuxdynasty/debrief aggregate --days 30 --compare-prev --out agg.json
`);
}

function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  if (!cmd || cmd === "-h" || cmd === "--help" || cmd === "help") {
    printHelp();
    process.exit(0);
  }
  if (cmd === "-v" || cmd === "--version" || cmd === "version") {
    process.stdout.write(`${readVersion()}\n`);
    process.exit(0);
  }
  if (cmd === "install") {
    process.exit(runInstall(PKG_ROOT, args.slice(1), { uninstall: false }));
  }
  if (cmd === "uninstall") {
    process.exit(runInstall(PKG_ROOT, args.slice(1), { uninstall: true }));
  }
  if (cmd === "doctor") {
    process.exit(runDoctor(PKG_ROOT));
  }
  if (PIPELINE_CMDS.has(cmd)) {
    const script = path.join(PKG_ROOT, "scripts", "debrief.sh");
    const res = spawnSync("bash", [script, cmd, ...args.slice(1)], {
      stdio: "inherit",
    });
    if (res.error) {
      process.stderr.write(`debrief: failed to execute ${script}: ${res.error.message}\n`);
      process.exit(1);
    }
    process.exit(typeof res.status === "number" ? res.status : 1);
  }

  process.stderr.write(`debrief: unknown command '${cmd}'\nRun 'debrief --help' for usage.\n`);
  process.exit(2);
}

main();
