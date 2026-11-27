// debrief-telemetry.ts — Pi global telemetry extension (zero external deps).
// Observes SKILL.md reads and failed tool calls, then forwards content-free
// envelopes to debrief's shared bash hooks with DEBRIEF_HARNESS=pi.
// Always fails open and never throws.
import { spawn } from "node:child_process";
import { type ExtensionAPI, isToolCallEventType } from "@earendil-works/pi-coding-agent";

const HOOKS_DIR = "%%HOOKS_DIR%%";
const SIBLING_TIMEOUT_MS = 10_000;
const SKILL_MD_RE = /(?:^|[/\\])([A-Za-z0-9._-]+)[/\\]SKILL\.md$/;

function resolveHooksDir(): string {
  const override = process.env?.DEBRIEF_HOOKS_DIR;
  if (typeof override === "string" && override !== "") return override;
  return HOOKS_DIR;
}

function timeoutMs(): number {
  const raw = Number(process.env?.DEBRIEF_PI_TIMEOUT_MS);
  return Number.isInteger(raw) && raw > 0 ? raw : SIBLING_TIMEOUT_MS;
}

function skillFromPath(raw: string): string {
  const match = raw.match(SKILL_MD_RE);
  if (!match) return "";
  return match[1].replace(/[^A-Za-z0-9._-]/g, "").slice(0, 40);
}

function categoryFor(toolName: string): string {
  if (toolName === "") return "unknown";
  return toolName.replace(/[^a-zA-Z0-9._-]/g, "").slice(0, 32) || "unknown";
}

function runHook(name: string, payload: unknown): void {
  const hooksDir = resolveHooksDir();
  if (hooksDir === "") return;

  let child: ReturnType<typeof spawn>;
  try {
    child = spawn("/bin/bash", [`${hooksDir}/${name}`], {
      env: { ...process.env, DEBRIEF_HARNESS: "pi" },
      stdio: ["pipe", "ignore", "ignore"],
    });
  } catch {
    return;
  }

  let settled = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const finish = (): void => {
    if (settled) return;
    settled = true;
    if (timer !== undefined) clearTimeout(timer);
    if (child.stdin && !child.stdin.destroyed) child.stdin.destroy();
  };

  timer = setTimeout(() => {
    try {
      child.kill("SIGKILL");
    } catch {
    }
    finish();
  }, timeoutMs());
  if (typeof timer.unref === "function") timer.unref();

  child.on("error", finish);
  child.on("exit", finish);
  child.on("close", finish);

  try {
    child.stdin?.on("error", finish);
    child.stdin?.end(JSON.stringify(payload));
  } catch {
    finish();
  }
}

export default function (pi: ExtensionAPI): void {
  pi.on("tool_call", async (event, ctx) => {
    try {
      if (!isToolCallEventType("read", event)) return;
      const skill = skillFromPath(event.input.path);
      if (skill === "") return;
      const sid = ctx.sessionManager.getSessionId();
      if (typeof sid !== "string" || sid === "") return;
      runHook("skill-loaded.sh", { session_id: sid, tool_input: { skill } });
    } catch {
    }
  });

  pi.on("tool_execution_end", async (event, ctx) => {
    try {
      if (event.isError !== true) return;
      const sid = ctx.sessionManager.getSessionId();
      if (typeof sid !== "string" || sid === "") return;
      runHook("stop-failure.sh", {
        session_id: sid,
        category: categoryFor(event.toolName),
      });
    } catch {
    }
  });
}
