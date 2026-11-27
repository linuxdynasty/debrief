#!/usr/bin/env node
// scripts/check-release-changes.mjs
// Determines whether commits between --base and --head include real product
// changes (code, hooks, skills, installer, non-version package config) rather
// than markdown docs, screenshots/images, CI files, or version-only bumps.
import { execFileSync } from "node:child_process";

const IMAGE_RE = /\.(png|jpe?g|gif|svg|webp|ico)$/i;
const VERSION_ONLY_FILES = new Set([
  "package.json",
  ".claude-plugin/plugin.json",
]);

function git(args, cwd) {
  return execFileSync("git", args, { cwd, encoding: "utf8" }).trim();
}

function canonicalJsonWithoutVersion(raw) {
  const sortVal = (v) => {
    if (Array.isArray(v)) return v.map(sortVal);
    if (v && typeof v === "object") {
      return Object.fromEntries(
        Object.keys(v)
          .sort()
          .map((k) => [k, sortVal(v[k])]),
      );
    }
    return v;
  };
  const obj = JSON.parse(raw);
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    delete obj.version;
  }
  return JSON.stringify(sortVal(obj));
}

function isVersionOnlyJsonChange(baseRef, headRef, filePath, cwd) {
  try {
    const a = git(["show", `${baseRef}:${filePath}`], cwd);
    const b = git(["show", `${headRef}:${filePath}`], cwd);
    return canonicalJsonWithoutVersion(a) === canonicalJsonWithoutVersion(b);
  } catch {
    return false;
  }
}

function isIgnoredPath(filePath, baseRef, headRef, cwd) {
  if (
    filePath === "README.md" ||
    filePath === "LICENSE" ||
    filePath === "CHANGELOG.md"
  ) {
    return true;
  }
  if (
    filePath.startsWith("docs/") ||
    filePath.startsWith("examples/") ||
    filePath.startsWith(".github/")
  ) {
    return true;
  }
  if (IMAGE_RE.test(filePath)) return true;
  if (filePath.endsWith(".md") && !filePath.startsWith("skills/")) return true;
  if (VERSION_ONLY_FILES.has(filePath)) {
    return isVersionOnlyJsonChange(baseRef, headRef, filePath, cwd);
  }
  return false;
}

function parseArgs(argv) {
  let base = "";
  let head = "HEAD";
  let cwd = process.cwd();
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--base") base = argv[++i] || "";
    else if (argv[i] === "--head") head = argv[++i] || "HEAD";
    else if (argv[i] === "--cwd") cwd = argv[++i] || process.cwd();
    else {
      process.stderr.write(`unknown option: ${argv[i]}\n`);
      process.exit(2);
    }
  }
  return { base, head, cwd };
}

const { base, head, cwd } = parseArgs(process.argv.slice(2));
if (!base) {
  process.stdout.write(
    `${JSON.stringify({ substantive: true, base: null, head, realChanges: ["<initial-release>"], ignoredChanges: [] })}\n`,
  );
  process.exit(0);
}

const raw = git(["diff", "--no-renames", "--name-only", `${base}..${head}`], cwd);
const files = raw ? raw.split(/\r?\n/).filter(Boolean) : [];
const realChanges = [];
const ignoredChanges = [];
for (const f of files) {
  if (isIgnoredPath(f, base, head, cwd)) ignoredChanges.push(f);
  else realChanges.push(f);
}

process.stdout.write(
  `${JSON.stringify({
    substantive: realChanges.length > 0,
    base,
    head,
    realChanges,
    ignoredChanges,
  })}\n`,
);
