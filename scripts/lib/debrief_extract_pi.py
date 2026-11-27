#!/usr/bin/env python3
"""Pi coding agent session extractor (Stage 1 rich meta + Stage 2 digest).

Pi stores sessions as JSONL trees under ~/.pi/agent/sessions/--<path>--/.
Every line carries a `type`; entries link by id/parentId.
"""
import json
import os
import re
from collections import Counter, defaultdict

from debrief_common import (
    META_SCHEMA_VERSION,
    canon_skill,
    categorize_error,
    classify_interjection,
    epoch_to_iso,
    epoch_to_utc_hour,
    lang_from_path,
    safe_int,
    truncate_text,
    ts_to_epoch,
)

_SESSION_FILE_RE = re.compile(
    r"^(?P<ts>[0-9T:.-]+Z)_(?P<id>[0-9a-zA-Z._-]+)\.jsonl$"
)
_SKILL_MD_RE = re.compile(r"(?:^|[/\\])([A-Za-z0-9._-]+)[/\\]SKILL\.md$")
_SLASH_SKILL_RE = re.compile(r"(?:^|\s)/skill:([A-Za-z0-9._-]+)")
_GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b")
_GIT_PUSH_RE = re.compile(r"\bgit\s+push\b")
_TOOL_PATH_KEYS = ("path", "file_path", "filePath")


def _config_dir():
    override = (os.environ.get("PI_CODING_AGENT_DIR") or "").strip()
    return os.path.abspath(os.path.expanduser(override)) if override else os.path.expanduser("~/.pi/agent")


def _settings_session_dir():
    """Read the `sessionDir` setting; Pi resolves relative values against the session cwd."""
    path = os.path.join(_config_dir(), "settings.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    value = data.get("sessionDir")
    return value.strip() if isinstance(value, str) and value.strip() else ""


def default_roots():
    """Resolve Pi session roots from Pi's own configuration, in Pi's precedence order.

    Pi accepts --session-dir, then PI_CODING_AGENT_SESSION_DIR, then the sessionDir
    setting, then <config>/sessions. A relative sessionDir is project-local, so it
    resolves against the process cwd. The CLI flag cannot be observed here; pass
    --transcript-root for a store outside these roots.
    """
    candidates = []
    env_dir = (os.environ.get("PI_CODING_AGENT_SESSION_DIR") or "").strip()
    if env_dir:
        candidates.append(env_dir)
    else:
        setting = _settings_session_dir()
        if setting:
            candidates.append(setting)
    candidates.append(os.path.join(_config_dir(), "sessions"))
    candidates.append(os.path.expanduser("~/.pi/agent/sessions"))

    roots, seen = [], set()
    for raw in candidates:
        resolved = os.path.abspath(os.path.expanduser(raw))
        if resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)
    return roots


def session_id_from_path(path):
    base = os.path.basename(path)
    m = _SESSION_FILE_RE.match(base)
    if m:
        return m.group("id")
    return base[: -len(".jsonl")] if base.endswith(".jsonl") else base


def discover(roots, since_epoch):
    """Yield (path, mtime) for Pi *.jsonl session files newer than since_epoch."""
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith(".jsonl"):
                    continue
                full = os.path.join(dirpath, name)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                if since_epoch and mtime < since_epoch:
                    continue
                out.append((full, mtime))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def _iter_records(path, skipped):
    """Yield parsed entries; count unparseable lines in `skipped` rather than dropping them."""
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                skipped[0] += 1
                continue
            if isinstance(rec, dict):
                yield rec


def _text_of(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    return ""


def _usage_tuple(usage):
    if not isinstance(usage, dict):
        return 0, 0, 0, 0
    return (
        max(0, safe_int(usage.get("input"), 0)),
        max(0, safe_int(usage.get("output"), 0)),
        max(0, safe_int(usage.get("cacheRead"), 0)),
        max(0, safe_int(usage.get("cacheWrite"), 0)),
    )


def _args_of(block):
    args = block.get("arguments")
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _tool_path(args):
    for key in _TOOL_PATH_KEYS:
        val = args.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def _skill_from_path(raw_path):
    m = _SKILL_MD_RE.search(str(raw_path or ""))
    return canon_skill(m.group(1)) if m else ""


def extract_session(path, mtime=0.0):
    """Return (meta_dict, digest_dict) for one Pi session JSONL file."""
    skipped = [0]
    sess_id = None
    parent_session = None
    project = ""
    last_model = ""
    changed_model = ""
    first_ep = last_ep = last_assistant_ep = None

    prompts = assistants = 0
    tools, errors, error_cats, languages = Counter(), Counter(), Counter(), Counter()
    session_models, msg_hours, interjection_reasons = Counter(), Counter(), Counter()
    skill_loads, first_skill_turn = set(), {}
    touched_seen, touched_files = set(), []
    user_prompts, assistant_tail, error_samples = [], [], []
    gaps = []
    git_commits = git_pushes = 0

    tokens = [0, 0, 0, 0]
    post_tokens = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    post_err = defaultdict(float)

    for rec in _iter_records(path, skipped):
        ep = ts_to_epoch(rec.get("timestamp"))
        if ep is not None:
            first_ep = ep if first_ep is None else min(first_ep, ep)
            last_ep = ep if last_ep is None else max(last_ep, ep)

        etype = rec.get("type") or ""

        if etype == "session":
            sid = rec.get("id")
            if isinstance(sid, str) and sid and not sess_id:
                sess_id = sid
            cwd = rec.get("cwd")
            if isinstance(cwd, str) and cwd and not project:
                project = cwd[:240]
            parent = rec.get("parentSession")
            if isinstance(parent, str) and parent and not parent_session:
                parent_session = session_id_from_path(parent)
        elif etype == "model_change":
            provider = rec.get("provider")
            model_id = rec.get("modelId")
            if isinstance(model_id, str) and model_id:
                last_model = model_id[:60]
                session_models[last_model] += 1
                changed_model = (
                    f"{provider}/{last_model}"[:80] if provider else last_model
                )
        elif etype == "message":
            msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
            role = msg.get("role") or ""
            if role == "user":
                text = _text_of(msg.get("content"))
                if not text:
                    continue
                prompts += 1
                hour = epoch_to_utc_hour(ep)
                if hour is not None:
                    msg_hours[str(hour)] += 1
                if last_assistant_ep is not None and ep is not None and ep > last_assistant_ep:
                    gaps.append(round(ep - last_assistant_ep, 2))
                    last_assistant_ep = None
                short = truncate_text(text, 260)
                if prompts >= 2 and short:
                    interjection_reasons[classify_interjection(short)] += 1
                if short and len(user_prompts) < 8:
                    user_prompts.append(short)
                for match in _SLASH_SKILL_RE.finditer(text):
                    name = canon_skill(match.group(1))
                    if name:
                        skill_loads.add(name)
                        first_skill_turn.setdefault(name, max(1, assistants))
            elif role == "assistant":
                agents_model = msg.get("model")
                if isinstance(agents_model, str) and agents_model and not last_model:
                    last_model = agents_model[:60]
                    session_models[last_model] += 1
                assistants += 1
                if ep is not None:
                    last_assistant_ep = ep
                usage = _usage_tuple(msg.get("usage"))
                for idx, val in enumerate(usage):
                    tokens[idx] += val
                if skill_loads and (usage[0] or usage[1]):
                    share = 1.0 / float(len(skill_loads))
                    for name in skill_loads:
                        for idx, val in enumerate(usage):
                            post_tokens[name][idx] += val * share
                short = truncate_text(_text_of(msg.get("content")), 280)
                if short:
                    assistant_tail.append(short)
                    if len(assistant_tail) > 3:
                        assistant_tail.pop(0)
                for block in msg.get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "toolCall":
                        continue
                    tool_name = str(block.get("name") or "unknown")
                    tools[tool_name] += 1
                    args = _args_of(block)
                    tool_path = _tool_path(args)
                    if tool_path:
                        skill = _skill_from_path(tool_path)
                        if skill:
                            skill_loads.add(skill)
                            first_skill_turn.setdefault(skill, max(1, assistants))
                        lang = lang_from_path(tool_path)
                        if lang:
                            languages[lang] += 1
                        if tool_path not in touched_seen and len(touched_files) < 15:
                            touched_seen.add(tool_path)
                            touched_files.append(tool_path[-120:])
                    command = args.get("command")
                    if isinstance(command, str):
                        if _GIT_COMMIT_RE.search(command):
                            git_commits += 1
                        if _GIT_PUSH_RE.search(command):
                            git_pushes += 1
            elif role == "toolResult":
                if msg.get("isError") is not True:
                    continue
                tool_name = str(msg.get("toolName") or "unknown")
                text = _text_of(msg.get("content"))
                errors[tool_name] += 1
                error_cats[categorize_error(tool_name, text)] += 1
                if skill_loads:
                    share = 1.0 / float(len(skill_loads))
                    for name in skill_loads:
                        post_err[name] += share
                if len(error_samples) < 8:
                    error_samples.append(f"{tool_name}: {truncate_text(text, 140)}")
        elif etype == "usage":
            for idx, val in enumerate(_usage_tuple(rec.get("usage"))):
                tokens[idx] += val

    if not sess_id:
        sess_id = session_id_from_path(path)
    if not project:
        project = os.path.basename(os.path.dirname(path))
    session_model = changed_model or last_model

    duration = (
        round((last_ep - first_ep) / 60.0, 2)
        if (first_ep and last_ep and last_ep >= first_ep)
        else 0.0
    )
    turns_after_skill_load = {
        name: max(1, assistants - turn + 1)
        for name, turn in sorted(first_skill_turn.items())
    }
    meta = {
        "meta_version": META_SCHEMA_VERSION,
        "id": sess_id,
        "harness": "pi",
        "source_path": path,
        "source_mtime": mtime,
        "project": project,
        "workspaces": [project] if project else [],
        "branch": "",
        "commit": "",
        "first_ts": epoch_to_iso(first_ep),
        "last_ts": epoch_to_iso(last_ep),
        "first_epoch": first_ep,
        "last_epoch": last_ep,
        "duration_minutes": duration,
        "prompts": prompts,
        "assistant_messages": assistants,
        "tools": dict(tools),
        "tool_calls": sum(tools.values()),
        "errors": dict(errors),
        "error_categories": dict(error_cats),
        "languages": dict(languages),
        "skill_loads": sorted(skill_loads),
        "subagents": 0,
        "subagent_roles": {},
        "session_models": dict(session_models),
        "max_depth": 1 if parent_session else 0,
        "parent_session": parent_session,
        "child_sessions": [],
        "response_gaps": gaps,
        "message_hours": dict(msg_hours),
        "hook_blocks": {},
        "git_commits": git_commits,
        "git_pushes": git_pushes,
        "tokens_in": tokens[0],
        "tokens_out": tokens[1],
        "tokens_cache_read": tokens[2],
        "tokens_cache_write": tokens[3],
        "model": session_model,
        "turns_after_skill_load": turns_after_skill_load,
        "post_load_attribution": {
            name: {
                "tokens_in": round(post_tokens[name][0], 2),
                "tokens_out": round(post_tokens[name][1], 2),
                "tokens_cache_read": round(post_tokens[name][2], 2),
                "tokens_cache_write": round(post_tokens[name][3], 2),
                "errors": round(post_err[name], 2),
            }
            for name in sorted(skill_loads)
        } if skill_loads else {},
        "interjection_reasons": dict(interjection_reasons),
    }
    digest = {
        "session_id": sess_id,
        "harness": "pi",
        "source_mtime": mtime,
        "project": project,
        "branch": "",
        "duration_minutes": duration,
        "prompts_count": prompts,
        "tool_calls": meta["tool_calls"],
        "top_tools": dict(tools.most_common(6)),
        "languages": dict(languages.most_common(6)),
        "skill_loads": meta["skill_loads"],
        "error_categories": dict(error_cats),
        "user_prompts": user_prompts[:6],
        "subagent_runs": [],
        "error_samples": error_samples[:8],
        "touched_files": touched_files[:12],
        "final_assistant_notes": assistant_tail[-2:],
        "malformed_lines": skipped[0],
    }
    return meta, digest
