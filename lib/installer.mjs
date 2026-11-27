// lib/installer.mjs — Universal per-harness installer, uninstaller, and doctor
// for @linuxdynasty/debrief (zero external dependencies).
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const ALL_HARNESSES = [
  "claude",
  "codex",
  "opencode",
  "agy",
  "muse",
  "cursor",
];

function homeDir() {
  return process.env.HOME || os.homedir();
}

function xdgDataHome() {
  return process.env.XDG_DATA_HOME || path.join(homeDir(), ".local", "share");
}

function xdgConfigHome() {
  return process.env.XDG_CONFIG_HOME || path.join(homeDir(), ".config");
}

export function debriefDataDir() {
  const override = (process.env.DEBRIEF_DATA_DIR || "").trim();
  if (override) return override.replace(/^~(?=\/|$)/, homeDir());
  const app = (process.env.DEBRIEF_APP_NAME || "debrief").trim() || "debrief";
  return path.join(xdgDataHome(), app);
}

export function skillsDirFor(harness) {
  const h = homeDir();
  switch (harness) {
    case "claude":
      return path.join(h, ".claude", "skills");
    case "codex":
      return path.join(h, ".codex", "skills");
    case "opencode":
      return path.join(xdgConfigHome(), "opencode", "skill");
    case "muse":
      return path.join(h, ".agents", "skills");
    case "cursor":
      return path.join(h, ".cursor", "skills");
    case "agy":
      return path.join(h, ".gemini", "config", "skills");
    default:
      throw new Error(`unknown harness: ${harness}`);
  }
}

export function detectHarnesses() {
  const h = homeDir();
  const cfg = xdgConfigHome();
  const probes = {
    claude: [path.join(h, ".claude")],
    codex: [path.join(h, ".codex")],
    opencode: [path.join(cfg, "opencode"), path.join(xdgDataHome(), "opencode")],
    agy: [path.join(h, ".gemini", "config"), path.join(h, ".gemini", "antigravity-cli")],
    muse: [path.join(cfg, "muse"), path.join(h, ".agents")],
    cursor: [path.join(h, ".cursor")],
  };
  return ALL_HARNESSES.filter((name) =>
    probes[name].some((p) => fs.existsSync(p)),
  );
}

function parseHarnessesArg(raw) {
  const tokens = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (tokens.length === 0) {
    throw new Error("--harness requires at least one harness name");
  }
  const invalid = tokens.filter(
    (t) => t !== "all" && !ALL_HARNESSES.includes(t),
  );
  if (invalid.length > 0) {
    throw new Error(
      `unknown harness(es): ${invalid.join(", ")} (valid: ${ALL_HARNESSES.join(", ")}, all)`,
    );
  }
  if (tokens.includes("all")) return [...ALL_HARNESSES];
  return [...new Set(tokens)];
}

function isTransientNpxRoot(pkgRoot) {
  const norm = pkgRoot.replace(/\\/g, "/");
  return norm.includes("/_npx/") || norm.includes("/npm-cache/");
}

function copyTree(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name === "__pycache__" || entry.name === ".DS_Store") continue;
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      copyTree(s, d);
    } else if (entry.isFile()) {
      fs.copyFileSync(s, d);
      fs.chmodSync(d, fs.statSync(s).mode & 0o777);
    }
  }
}

function linkLocalBin(runtimeRoot, dryRun) {
  const localBin = path.join(homeDir(), ".local", "bin");
  const binLink = path.join(localBin, "debrief");
  const target = path.join(runtimeRoot, "bin", "debrief.mjs");
  if (!fs.existsSync(target)) return;
  if (dryRun) {
    process.stdout.write(`[dry-run] link CLI: ${binLink} -> ${target}\n`);
    return;
  }
  try {
    fs.mkdirSync(localBin, { recursive: true });
    try {
      fs.unlinkSync(binLink);
    } catch {
      // ok
    }
    fs.symlinkSync(target, binLink);
    process.stdout.write(`linked CLI: ${binLink} -> ${target}\n`);
  } catch {
    // non-fatal if ~/.local/bin is unwritable
  }
}

function stageRuntime(pkgRoot, dryRun) {
  const runtimeRoot = path.join(debriefDataDir(), "runtime");
  if (dryRun) {
    process.stdout.write(`[dry-run] stage runtime -> ${runtimeRoot}\n`);
    return runtimeRoot;
  }
  fs.rmSync(runtimeRoot, { recursive: true, force: true });
  fs.mkdirSync(runtimeRoot, { recursive: true });
  for (const sub of ["bin", "hooks", "lib", "scripts", "skills"]) {
    const src = path.join(pkgRoot, sub);
    if (fs.existsSync(src)) copyTree(src, path.join(runtimeRoot, sub));
  }
  for (const f of ["package.json", "LICENSE"]) {
    const src = path.join(pkgRoot, f);
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(runtimeRoot, f));
  }
  return runtimeRoot;
}

function installSkill(harness, runtimeRoot, dryRun) {
  const src = path.join(runtimeRoot, "skills", "debrief");
  const destDir = skillsDirFor(harness);
  const dest = path.join(destDir, "debrief");
  if (dryRun) {
    process.stdout.write(`[dry-run] link skill (${harness}): ${dest} -> ${src}\n`);
    return;
  }
  fs.mkdirSync(destDir, { recursive: true });
  try {
    const st = fs.lstatSync(dest);
    if (st.isSymbolicLink()) {
      fs.unlinkSync(dest);
    } else {
      fs.rmSync(dest, { recursive: true, force: true });
    }
  } catch {
    // does not exist
  }
  fs.symlinkSync(src, dest);
  process.stdout.write(`installed skill (${harness}): ${dest} -> ${src}\n`);
}

function uninstallSkill(harness, dryRun) {
  const dest = path.join(skillsDirFor(harness), "debrief");
  if (!fs.existsSync(dest)) {
    try {
      fs.lstatSync(dest);
    } catch {
      return;
    }
  }
  if (dryRun) {
    process.stdout.write(`[dry-run] remove skill (${harness}): ${dest}\n`);
    return;
  }
  const st = fs.lstatSync(dest);
  if (st.isSymbolicLink()) {
    fs.unlinkSync(dest);
  } else {
    fs.rmSync(dest, { recursive: true, force: true });
  }
  process.stdout.write(`removed skill (${harness}): ${dest}\n`);
}

function readJsonSafe(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const raw = fs.readFileSync(filePath, "utf8").trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

function writeJsonAtomic(filePath, obj) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.tmp.${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(obj, null, 2)}\n`, "utf8");
  fs.renameSync(tmp, filePath);
}

const DEBRIEF_HOOK_MARKER = "debrief-telemetry-hook";

function isDebriefHookEntry(entry) {
  if (!entry || typeof entry !== "object") return false;
  if (entry._managed_by === DEBRIEF_HOOK_MARKER) return true;
  const hooks = Array.isArray(entry.hooks) ? entry.hooks : [];
  return hooks.some(
    (h) =>
      typeof h?.command === "string" &&
      (h.command.includes(DEBRIEF_HOOK_MARKER) ||
        h.command.includes("/debrief/hooks/") ||
        h.command.includes("/debrief/runtime/hooks/")),
  );
}

function mergeHookList(existing, newEntries) {
  const kept = (Array.isArray(existing) ? existing : []).filter(
    (e) => !isDebriefHookEntry(e),
  );
  return [...kept, ...newEntries];
}

function stripHookList(existing) {
  return (Array.isArray(existing) ? existing : []).filter(
    (e) => !isDebriefHookEntry(e),
  );
}

function installHooksFor(harness, runtimeRoot, dryRun) {
  const hooksDir = path.join(runtimeRoot, "hooks");
  if (harness === "claude") {
    const settingsPath = path.join(homeDir(), ".claude", "settings.json");
    if (dryRun) {
      process.stdout.write(`[dry-run] merge debrief hooks into ${settingsPath}\n`);
      return;
    }
    const doc = readJsonSafe(settingsPath);
    doc.hooks = doc.hooks && typeof doc.hooks === "object" ? doc.hooks : {};
    doc.hooks.PostToolUse = mergeHookList(doc.hooks.PostToolUse, [
      {
        matcher: "Skill",
        hooks: [
          {
            type: "command",
            command: `bash "${hooksDir}/skill-loaded.sh" # ${DEBRIEF_HOOK_MARKER}`,
          },
        ],
      },
    ]);
    doc.hooks.StopFailure = mergeHookList(doc.hooks.StopFailure, [
      {
        hooks: [
          {
            type: "command",
            command: `bash "${hooksDir}/stop-failure.sh" # ${DEBRIEF_HOOK_MARKER}`,
          },
        ],
      },
    ]);
    writeJsonAtomic(settingsPath, doc);
    process.stdout.write(`installed telemetry hooks (claude): ${settingsPath}\n`);
    return;
  }

  if (harness === "codex") {
    const hooksPath = path.join(homeDir(), ".codex", "hooks.json");
    if (dryRun) {
      process.stdout.write(`[dry-run] merge debrief hooks into ${hooksPath}\n`);
      return;
    }
    const doc = readJsonSafe(hooksPath);
    doc.hooks = doc.hooks && typeof doc.hooks === "object" ? doc.hooks : {};
    doc.hooks.PostToolUse = mergeHookList(doc.hooks.PostToolUse, [
      {
        hooks: [
          {
            type: "command",
            command: `bash "${hooksDir}/codex/skill-loaded.sh" # ${DEBRIEF_HOOK_MARKER}`,
            timeout: 5,
          },
        ],
      },
    ]);
    writeJsonAtomic(hooksPath, doc);
    process.stdout.write(`installed telemetry hooks (codex): ${hooksPath}\n`);
    return;
  }

  if (harness === "opencode") {
    const pluginsDir = path.join(xdgConfigHome(), "opencode", "plugins");
    const dest = path.join(pluginsDir, "debrief-telemetry.js");
    if (dryRun) {
      process.stdout.write(`[dry-run] install OpenCode V2 telemetry plugin -> ${dest}\n`);
      return;
    }
    const tpl = fs.readFileSync(
      path.join(hooksDir, "opencode", "debrief-telemetry.js"),
      "utf8",
    );
    const rendered = tpl.replace("%%HOOKS_DIR%%", hooksDir);
    fs.mkdirSync(pluginsDir, { recursive: true });
    fs.writeFileSync(dest, rendered, "utf8");
    process.stdout.write(`installed telemetry plugin (opencode): ${dest}\n`);
    return;
  }

  if (harness === "agy") {
    const hooksPath = path.join(homeDir(), ".gemini", "config", "hooks.json");
    if (dryRun) {
      process.stdout.write(`[dry-run] add 'debrief' block to ${hooksPath}\n`);
      return;
    }
    const doc = readJsonSafe(hooksPath);
    doc.debrief = {
      PostToolUse: [
        {
          matcher: "read_file|view_file",
          hooks: [
            {
              type: "command",
              command: `bash "${hooksDir}/agy/skill-loaded.sh" # ${DEBRIEF_HOOK_MARKER}`,
              timeout: 10,
            },
          ],
        },
      ],
    };
    writeJsonAtomic(hooksPath, doc);
    process.stdout.write(`installed telemetry hooks (agy): ${hooksPath}\n`);
    return;
  }

  if (harness === "muse") {
    const museDir = path.join(xdgConfigHome(), "muse");
    const settingsPath = path.join(museDir, "settings.json");
    const managedPath = path.join(debriefDataDir(), "muse-hooks.json");
    if (dryRun) {
      process.stdout.write(`[dry-run] install Muse managed hooks -> ${managedPath}\n`);
      return;
    }
    const doc = readJsonSafe(settingsPath);
    if (doc.managed_hooks_path && doc.managed_hooks_path !== managedPath) {
      process.stdout.write(
        `note (muse): managed_hooks_path already points to ${doc.managed_hooks_path}; leaving it untouched (transcript mining still covers Muse)\n`,
      );
      return;
    }
    const tpl = fs.readFileSync(path.join(hooksDir, "muse", "hooks.json"), "utf8");
    fs.mkdirSync(path.dirname(managedPath), { recursive: true });
    fs.writeFileSync(
      managedPath,
      tpl.replaceAll("%%HOOKS_DIR%%", hooksDir),
      "utf8",
    );
    if (!doc.schema_version) doc.schema_version = 1;
    doc.managed_hooks_path = managedPath;
    writeJsonAtomic(settingsPath, doc);
    process.stdout.write(`installed telemetry hooks (muse): ${managedPath}\n`);
  }
}

function uninstallHooksFor(harness, dryRun) {
  if (harness === "claude") {
    const settingsPath = path.join(homeDir(), ".claude", "settings.json");
    if (!fs.existsSync(settingsPath)) return;
    const doc = readJsonSafe(settingsPath);
    if (!doc.hooks || typeof doc.hooks !== "object") return;
    if (dryRun) {
      process.stdout.write(`[dry-run] strip debrief hooks from ${settingsPath}\n`);
      return;
    }
    for (const ev of ["PostToolUse", "StopFailure"]) {
      if (Array.isArray(doc.hooks[ev])) {
        doc.hooks[ev] = stripHookList(doc.hooks[ev]);
        if (doc.hooks[ev].length === 0) delete doc.hooks[ev];
      }
    }
    writeJsonAtomic(settingsPath, doc);
    process.stdout.write(`removed telemetry hooks (claude): ${settingsPath}\n`);
    return;
  }

  if (harness === "codex") {
    const hooksPath = path.join(homeDir(), ".codex", "hooks.json");
    if (!fs.existsSync(hooksPath)) return;
    const doc = readJsonSafe(hooksPath);
    if (!doc.hooks || typeof doc.hooks !== "object") return;
    if (dryRun) {
      process.stdout.write(`[dry-run] strip debrief hooks from ${hooksPath}\n`);
      return;
    }
    if (Array.isArray(doc.hooks.PostToolUse)) {
      doc.hooks.PostToolUse = stripHookList(doc.hooks.PostToolUse);
      if (doc.hooks.PostToolUse.length === 0) delete doc.hooks.PostToolUse;
    }
    writeJsonAtomic(hooksPath, doc);
    process.stdout.write(`removed telemetry hooks (codex): ${hooksPath}\n`);
    return;
  }

  if (harness === "opencode") {
    const dest = path.join(
      xdgConfigHome(),
      "opencode",
      "plugins",
      "debrief-telemetry.js",
    );
    if (!fs.existsSync(dest)) return;
    if (dryRun) {
      process.stdout.write(`[dry-run] remove ${dest}\n`);
      return;
    }
    fs.unlinkSync(dest);
    process.stdout.write(`removed telemetry plugin (opencode): ${dest}\n`);
    return;
  }

  if (harness === "agy") {
    const hooksPath = path.join(homeDir(), ".gemini", "config", "hooks.json");
    if (!fs.existsSync(hooksPath)) return;
    const doc = readJsonSafe(hooksPath);
    if (!("debrief" in doc)) return;
    if (dryRun) {
      process.stdout.write(`[dry-run] remove 'debrief' block from ${hooksPath}\n`);
      return;
    }
    delete doc.debrief;
    writeJsonAtomic(hooksPath, doc);
    process.stdout.write(`removed telemetry hooks (agy): ${hooksPath}\n`);
    return;
  }

  if (harness === "muse") {
    const settingsPath = path.join(xdgConfigHome(), "muse", "settings.json");
    const managedPath = path.join(debriefDataDir(), "muse-hooks.json");
    if (fs.existsSync(settingsPath)) {
      const doc = readJsonSafe(settingsPath);
      if (doc.managed_hooks_path === managedPath) {
        if (dryRun) {
          process.stdout.write(`[dry-run] clear managed_hooks_path in ${settingsPath}\n`);
        } else {
          delete doc.managed_hooks_path;
          writeJsonAtomic(settingsPath, doc);
          process.stdout.write(`removed telemetry hooks (muse): ${settingsPath}\n`);
        }
      }
    }
    if (!dryRun && fs.existsSync(managedPath)) fs.unlinkSync(managedPath);
  }
}

export function runInstall(pkgRoot, rawArgs, { uninstall = false } = {}) {
  let harnesses = null;
  let withHooks = false;
  let copyMode = false;
  let dryRun = false;

  for (let i = 0; i < rawArgs.length; i += 1) {
    const a = rawArgs[i];
    if (a === "--all") {
      harnesses = [...ALL_HARNESSES];
    } else if (a === "--harness") {
      const val = rawArgs[++i];
      if (!val) {
        process.stderr.write("debrief: --harness requires a value\n");
        return 2;
      }
      try {
        harnesses = parseHarnessesArg(val);
      } catch (err) {
        process.stderr.write(`debrief: ${err.message}\n`);
        return 2;
      }
    } else if (a.startsWith("--harness=")) {
      try {
        harnesses = parseHarnessesArg(a.slice("--harness=".length));
      } catch (err) {
        process.stderr.write(`debrief: ${err.message}\n`);
        return 2;
      }
    } else if (a === "--with-hooks") {
      withHooks = true;
    } else if (a === "--copy") {
      copyMode = true;
    } else if (a === "--uninstall") {
      uninstall = true;
    } else if (a === "--dry-run") {
      dryRun = true;
    } else {
      process.stderr.write(`debrief: unknown option '${a}'\n`);
      return 2;
    }
  }

  if (!harnesses) {
    harnesses = detectHarnesses();
    if (harnesses.length === 0) harnesses = [...ALL_HARNESSES];
  }

  if (uninstall) {
    for (const h of harnesses) {
      uninstallSkill(h, dryRun);
      uninstallHooksFor(h, dryRun);
    }
    process.stdout.write(
      `debrief uninstalled for: ${harnesses.join(", ")}\n`,
    );
    return 0;
  }

  const stage = copyMode || isTransientNpxRoot(pkgRoot);
  const runtimeRoot = stage ? stageRuntime(pkgRoot, dryRun) : pkgRoot;
  linkLocalBin(runtimeRoot, dryRun);

  for (const h of harnesses) {
    installSkill(h, runtimeRoot, dryRun);
    if (withHooks) installHooksFor(h, runtimeRoot, dryRun);
  }
  process.stdout.write(
    `debrief installed (${stage ? "staged copy" : "linked"} from ${runtimeRoot}) for: ${harnesses.join(", ")}${withHooks ? " (with telemetry hooks)" : ""}\n`,
  );
  return 0;
}

export function runDoctor(pkgRoot) {
  const py = spawnSync("python3", ["--version"], { encoding: "utf8" });
  const pyVer =
    py.status === 0
      ? (py.stdout || py.stderr || "").trim()
      : "MISSING (python3 is required)";
  const dataDir = debriefDataDir();
  const detected = detectHarnesses();

  process.stdout.write(`debrief doctor\n`);
  process.stdout.write(`  package root : ${pkgRoot}\n`);
  process.stdout.write(`  python3      : ${pyVer}\n`);
  process.stdout.write(`  data dir     : ${dataDir}\n`);
  process.stdout.write(
    `  detected     : ${detected.length ? detected.join(", ") : "(none)"}\n`,
  );
  process.stdout.write(`  harnesses:\n`);
  for (const h of ALL_HARNESSES) {
    const skillPath = path.join(skillsDirFor(h), "debrief", "SKILL.md");
    const hasSkill = fs.existsSync(skillPath);
    const present = detected.includes(h) ? "detected" : "not detected";
    process.stdout.write(
      `    - ${h.padEnd(9)} ${present.padEnd(13)} skill=${hasSkill ? "installed" : "missing"}\n`,
    );
  }
  const cacheMeta = path.join(dataDir, "debrief-cache", "meta");
  const snapDir = path.join(dataDir, "debrief-reports", "snapshots");
  const metaCount = fs.existsSync(cacheMeta)
    ? fs.readdirSync(cacheMeta).filter((f) => f.endsWith(".json")).length
    : 0;
  const snapCount = fs.existsSync(snapDir)
    ? fs.readdirSync(snapDir).filter((f) => f.startsWith("snap-")).length
    : 0;
  process.stdout.write(
    `  cache        : ${metaCount} cached session metas, ${snapCount} saved snapshots\n`,
  );
  return py.status === 0 ? 0 : 1;
}
