// Behavioral test for hooks/opencode/debrief-telemetry.js (OpenCode V2 plugin).
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..", "..");

test("OpenCode V2 telemetry plugin records skill loads and model failures", async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "debrief-oc-"));
  try {
    process.env.DEBRIEF_DATA_DIR = work;
    process.env.DEBRIEF_HOOKS_DIR = path.join(ROOT, "hooks");
    delete process.env.DEBRIEF_TELEMETRY_OFF;

    const mod = await import(
      path.join(ROOT, "hooks", "opencode", "debrief-telemetry.js")
    );
    const plugin = mod.default;
    assert.equal(plugin.id, "debrief-telemetry");

    let toolAfterFn = null;
    const events = [
      {
        type: "session.execution.failed",
        data: { sessionID: "oc_sess_12345", error: { status: 429, message: "secret-body" } },
      },
    ];
    const ctx = {
      tool: {
        async hook(name, fn) {
          assert.equal(name, "execute.after");
          toolAfterFn = fn;
          return { async dispose() {} };
        },
      },
      event: {
        subscribe() {
          return (async function* () {
            for (const ev of events) yield ev;
          })();
        },
      },
    };

    const cleanup = await plugin.setup(ctx);
    await toolAfterFn({
      status: "completed",
      sessionID: "oc_sess_12345",
      tool: "skill",
      input: { name: "debrief" },
    });
    await toolAfterFn({
      status: "completed",
      sessionID: "oc_sess_12345",
      tool: "read",
      input: { filePath: "/repo/skills/code-review/SKILL.md" },
    });
    await cleanup();

    const logPath = path.join(work, "skills-usage.jsonl");
    assert.ok(fs.existsSync(logPath), "expected skills-usage.jsonl");
    const lines = fs
      .readFileSync(logPath, "utf8")
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    assert.equal(lines.length, 3);
    assert.ok(lines.every((e) => e.harness === "opencode"));
    const skills = lines
      .filter((e) => e.type === "skill-load")
      .map((e) => e.detail.skill);
    assert.deepEqual(skills.sort(), ["code-review", "debrief"]);
    const failEv = lines.find((e) => e.type === "model-failure");
    assert.equal(String(failEv.detail.category), "429");
    assert.ok(!JSON.stringify(lines).includes("secret-body"));
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }
});
