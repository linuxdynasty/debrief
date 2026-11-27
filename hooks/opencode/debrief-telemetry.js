// debrief-telemetry.js — OpenCode V2 global telemetry plugin (zero external deps).
// Observes completed skill loads (`tool.hook("execute.after")`) and dead turns
// (`session.execution.failed` / `session.error`) and forwards content-free
// telemetry envelopes to debrief's shared bash hooks with DEBRIEF_HARNESS=opencode.
// Always fails open and never throws.
import { spawn } from "node:child_process";

const HOOKS_DIR = "%%HOOKS_DIR%%";
const SIBLING_TIMEOUT_MS = 10_000;

function resolveHooksDir() {
  const override =
    typeof process !== "undefined" ? process.env?.DEBRIEF_HOOKS_DIR : undefined;
  if (typeof override === "string" && override !== "") return override;
  return HOOKS_DIR;
}

function timeoutMs() {
  const raw = Number(process.env?.DEBRIEF_OPENCODE_TIMEOUT_MS);
  return Number.isInteger(raw) && raw > 0 ? raw : SIBLING_TIMEOUT_MS;
}

function asText(v) {
  return typeof v === "string" ? v : "";
}

function extractSkillName(event) {
  const tool = asText(event?.tool).toLowerCase();
  const input =
    event?.input && typeof event.input === "object" ? event.input : {};
  if (tool === "skill" || tool === "read_skill") {
    const raw =
      asText(input.name) ||
      asText(input.skill) ||
      asText(input.skill_name) ||
      asText(input.id);
    return raw.trim();
  }
  if (tool === "read" || tool === "read_file" || tool === "view_file") {
    const fp =
      asText(input.filePath) || asText(input.file_path) || asText(input.path);
    const match = fp.match(/(?:^|[/\\])([A-Za-z0-9._-]+)[/\\]SKILL\.md$/);
    return match ? match[1] : "";
  }
  return "";
}

function runHook(hooksDir, name, payload) {
  return new Promise((resolve) => {
    let done = false;
    let timer;
    const finish = (ok) => {
      if (done) return;
      done = true;
      if (timer !== undefined) clearTimeout(timer);
      resolve(ok);
    };
    let child;
    try {
      child = spawn("/bin/bash", [`${hooksDir}/${name}`], {
        stdio: ["pipe", "ignore", "ignore"],
        env: { ...process.env, DEBRIEF_HARNESS: "opencode" },
        detached: true,
      });
    } catch {
      finish(false);
      return;
    }
    timer = setTimeout(() => {
      try {
        if (typeof child.pid === "number" && child.pid > 0) {
          process.kill(-child.pid, "SIGKILL");
        } else {
          child.kill("SIGKILL");
        }
      } catch {
        try {
          child.kill("SIGKILL");
        } catch {
          // already exited
        }
      }
      finish(false);
    }, timeoutMs());
    if (typeof timer.unref === "function") timer.unref();
    child.on("error", () => finish(false));
    child.stdin.on("error", () => finish(false));
    child.on("close", (code) => finish(code === 0));
    try {
      child.stdin.write(JSON.stringify(payload));
      child.stdin.end();
    } catch {
      finish(false);
    }
  });
}

async function handleToolAfter(event) {
  try {
    if (!event || event.status !== "completed") return "ignored";
    const sessionID = asText(event.sessionID);
    if (!sessionID) return "ignored";
    const skill = extractSkillName(event);
    if (!skill) return "ignored";
    const ok = await runHook(resolveHooksDir(), "skill-loaded.sh", {
      hook_event_name: "PostToolUse",
      tool_name: "Skill",
      session_id: sessionID,
      tool_input: { skill },
    });
    return ok ? "recorded" : "silent";
  } catch {
    return "silent";
  }
}

async function handleSessionEvent(event) {
  try {
    if (!event || typeof event !== "object") return "ignored";
    if (
      event.type !== "session.execution.failed" &&
      event.type !== "session.error"
    ) {
      return "ignored";
    }
    const data =
      (event.data && typeof event.data === "object" && event.data) ||
      (event.properties && typeof event.properties === "object" && event.properties) ||
      {};
    const sessionID = asText(data.sessionID);
    if (!sessionID) return "ignored";
    const err = data.error && typeof data.error === "object" ? data.error : {};
    const status =
      typeof err.status === "number" ? String(err.status) : asText(err.status);
    const category =
      status || asText(err.type) || asText(err.name) || "unknown";
    const ok = await runHook(resolveHooksDir(), "stop-failure.sh", {
      hook_event_name: "StopFailure",
      session_id: sessionID,
      failure_category: category,
    });
    return ok ? "recorded" : "silent";
  } catch {
    return "silent";
  }
}

export default {
  id: "debrief-telemetry",
  async setup(context) {
    const handles = [];
    const controller = new AbortController();

    if (typeof context?.tool?.hook === "function") {
      try {
        handles.push(
          await context.tool.hook("execute.after", async (event) => {
            await handleToolAfter(event);
          }),
        );
      } catch {
        // fail open
      }
    }

    let eventLoop = null;
    if (typeof context?.event?.subscribe === "function") {
      eventLoop = (async () => {
        try {
          const stream = context.event.subscribe({
            types: ["session.execution.failed", "session.error"],
            signal: controller.signal,
          });
          if (stream && typeof stream[Symbol.asyncIterator] === "function") {
            for await (const ev of stream) {
              await handleSessionEvent(ev);
            }
          }
        } catch {
          // fail open
        }
      })();
    }

    return async () => {
      await new Promise((r) => setTimeout(r, 15));
      controller.abort();
      for (const h of handles) {
        try {
          if (h && typeof h.dispose === "function") await h.dispose();
        } catch {
          // fail open
        }
      }
      if (eventLoop) {
        try {
          await eventLoop;
        } catch {
          // fail open
        }
      }
    };
  },
};
