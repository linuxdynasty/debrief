#!/usr/bin/env python3
"""GitHub PR review & papercut sync + universal reviewer parser for /debrief.

Works universally with any GitHub PR reviewer (human reviewers, reviewd,
ChatGPT/Codex connector, Claude, Cursor Bugbot, Copilot, CodeRabbit).
Stores only content-free structured metadata in $DEBRIEF_DATA_DIR/debrief-cache/github/.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debrief_common import (  # noqa: E402
    atomic_write_json,
    default_cache_dir,
    resolve_since,
    safe_int,
)

GITHUB_REMOTE_RE = re.compile(
    r"(?:github\.com[:/])([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
REVIEWD_TAG_RE = re.compile(r"<!--\s*reviewd:head=([0-9a-f]{7,40})\s*-->", re.I)
STRUCTURED_SEV_CAT_RE = re.compile(
    r"\*\*(P[0-3])\*\*\s*[·|:-]\s*([a-z0-9][a-z0-9_-]{1,40})", re.I
)
BADGE_SEV_RE = re.compile(
    r"(?:img\.shields\.io/badge/|\b)(P[0-3])(?:\s*Badge|\b|\]|\*\*)", re.I
)
WORD_SEV_RE = re.compile(r"\b(critical|blocker|blocking|high|medium|warning|low|nit)\b", re.I)
REPEAT_RE = re.compile(r"\b(repeat(?:ed)?|still unfixed|prior round|from prior)\b", re.I)

TIMING_NOISE_PHRASES = (
    "ci pending",
    "live lanes pending",
    "sandbox has no database",
    "no database in review sandbox",
    "blocked offline",
    "pending in ci",
    "ci shards pending",
    "pending on this head",
    "no observed live",
    "not yet observed",
    "needs eshu_postgres_test_dsn",
    "no pg_ctl",
    "ci not green on this head",
    "unrunnable in this sandbox",
    "ci still pending",
    "all ci checks pending",
    "checks are neutral or pending",
    "no test or run evidence observed on this head",
)

PR_GRAPHQL_QUERY = """
query($owner: String!, $name: String!, $cursor: String, $first: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: $first, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number state headRefName createdAt updatedAt mergedAt
        author { login }
        commits(last: 20) { nodes { commit { oid } } }
        reviews(last: 30) {
          nodes { author { login } state submittedAt commit { oid } body }
        }
        reviewThreads(first: 100) {
          nodes {
            id isResolved isOutdated path line originalLine
            comments(first: 15) {
              nodes {
                author { login } createdAt
                commit { oid } originalCommit { oid } body
              }
            }
          }
        }
      }
    }
  }
}
"""


def parse_iso_epoch(ts):
    if not ts or not isinstance(ts, str):
        return 0.0
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def resolve_github_slug(repo_path):
    """Return 'owner/name' for a git checkout whose origin is on GitHub, else ''."""
    if not repo_path or not os.path.isdir(repo_path):
        return ""
    try:
        out = subprocess.check_output(
            ["git", "-C", repo_path, "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip()
    except Exception:
        return ""
    m = GITHUB_REMOTE_RE.search(out)
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def github_cache_dir(cache_dir=None):
    return os.path.join(cache_dir or default_cache_dir(), "github")


def cache_paths_for_slug(slug, cache_dir=None):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "__", slug.replace("/", "__"))
    gdir = github_cache_dir(cache_dir)
    return (
        os.path.join(gdir, f"{safe}.reviews.json"),
        os.path.join(gdir, f"{safe}.papercuts.json"),
    )


def discover_cached_github_files(repo_paths, cache_dir=None):
    """Find cached review and papercut files matching --repo checkouts (offline)."""
    reviews, papercuts = [], []
    seen = set()
    for rp in repo_paths or []:
        slug = resolve_github_slug(rp)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        rev_p, pc_p = cache_paths_for_slug(slug, cache_dir)
        if os.path.isfile(rev_p):
            reviews.append(rev_p)
        if os.path.isfile(pc_p):
            papercuts.append(pc_p)
    return reviews, papercuts


def detect_reviewer_source(author_login, body):
    """Classify reviewer origin across reviewd, major AI bots, and humans."""
    txt = str(body or "")
    low_a = str(author_login or "").lower()
    if REVIEWD_TAG_RE.search(txt):
        return "reviewd"
    if "chatgpt-codex" in low_a or "codex" in low_a or "chatgpt" in low_a:
        return "chatgpt-codex"
    if "claude" in low_a or "anthropic" in low_a:
        return "claude"
    if "cursor" in low_a or "bugbot" in low_a:
        return "cursor-bugbot"
    if "copilot" in low_a:
        return "copilot"
    if "coderabbit" in low_a:
        return "coderabbit"
    if "greptile" in low_a:
        return "greptile"
    if low_a.endswith("[bot]") or low_a.endswith("-bot"):
        return low_a.replace("[bot]", "") or "bot"
    return "human"


def parse_finding_meta(body, author_login="", reviewer_source="", path=""):
    """Extract content-free severity, category, timing-noise, and repeat flags."""
    txt = str(body or "")
    low = txt.lower()
    src = reviewer_source or detect_reviewer_source(author_login, txt)
    sev, cat = "ungraded", "general"

    m = STRUCTURED_SEV_CAT_RE.search(txt)
    if m:
        sev, cat = m.group(1).upper(), m.group(2).lower()
    else:
        bm = BADGE_SEV_RE.search(txt)
        if bm:
            sev = bm.group(1).upper()
        else:
            wm = WORD_SEV_RE.search(txt[:400])
            if wm:
                w = wm.group(1).lower()
                if w in ("critical", "blocker", "blocking", "high"):
                    sev = "P1"
                elif w in ("medium", "warning"):
                    sev = "P2"
                elif w in ("low", "nit"):
                    sev = "P3"
        if any(k in low for k in ("ci pending", "not yet observed", "sandbox has no database", "blocked offline")):
            cat = "runtime-proof-gap"
        elif any(k in low for k in ("overclaim", "overstates", "contradicts", "pr description", "pr body", "claim")):
            cat = "evidence-overclaim"
        elif any(k in low for k in ("false-green", "false green", "vacuous", "mask", "untested", "skip")):
            cat = "false-green-proof"
        elif any(k in low for k in ("drift", "stale", "out of sync", "regenerate")):
            cat = "generated-drift-risk"
        elif any(k in low for k in ("schema", "openapi", "contract", "signature")):
            cat = "contract-mismatch"
        elif any(k in low for k in ("test", "coverage", "assertion")):
            cat = "missing-coverage"
        elif any(k in low for k in ("race", "deadlock", "lock", "concurrency")):
            cat = "concurrency"
        elif any(k in low for k in ("security", "injection", "secret", "auth")):
            cat = "security"

    is_advisory = "advisory" in low[:260] or "non-blocking" in low[:260]
    is_timing_noise = cat in ("runtime-proof-gap", "missing-proof") and any(p in low for p in TIMING_NOISE_PHRASES)
    return {
        "reviewer_source": src,
        "severity": sev,
        "category": cat,
        "is_advisory": is_advisory,
        "is_timing_noise": is_timing_noise,
        "explicit_repeat": bool(REPEAT_RE.search(txt[:360])),
        "path": str(path or ""),
    }


def normalize_pr_node(node, repo_slug=""):
    """Convert a raw GitHub GraphQL PR node into a content-free structured record."""
    commits = [
        ((cn or {}).get("commit") or {}).get("oid") or ""
        for cn in (node.get("commits") or {}).get("nodes") or []
    ]
    commits = [c for c in commits if c]

    reviews_out, review_src_by_sha = [], {}
    for rn in (node.get("reviews") or {}).get("nodes") or []:
        if not isinstance(rn, dict):
            continue
        body = str(rn.get("body") or "").strip()
        if not body:
            continue
        author = ((rn.get("author") or {}).get("login") or "").strip()
        sha = ((rn.get("commit") or {}).get("oid") or "").strip()
        src = detect_reviewer_source(author, body)
        if sha:
            review_src_by_sha[sha] = src
        counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        cm = re.search(
            r"\*\*P0\*\*\s*(\d+)\s*·\s*\*\*P1\*\*\s*(\d+)\s*·\s*\*\*P2\*\*\s*(\d+)\s*·\s*\*\*P3\*\*\s*(\d+)",
            body,
        )
        if cm:
            counts = {f"P{i}": int(cm.group(i + 1)) for i in range(4)}
        reviews_out.append({
            "reviewer_source": src,
            "state": str(rn.get("state") or ""),
            "submitted_at": str(rn.get("submittedAt") or ""),
            "commit": sha[:12],
            "counts": counts,
            "mentions_repeat": bool(REPEAT_RE.search(body[:450])),
        })

    seen_key_commits = defaultdict(set)
    threads_out = []
    for tn in (node.get("reviewThreads") or {}).get("nodes") or []:
        if not isinstance(tn, dict):
            continue
        comments = (tn.get("comments") or {}).get("nodes") or []
        if not comments:
            continue
        c0 = comments[0] or {}
        author = ((c0.get("author") or {}).get("login") or "").strip()
        orig_sha = (
            ((c0.get("originalCommit") or {}).get("oid") or "")
            or ((c0.get("commit") or {}).get("oid") or "")
        )
        inferred_src = review_src_by_sha.get(orig_sha, "")
        meta = parse_finding_meta(
            str(c0.get("body") or ""),
            author_login=author,
            reviewer_source=inferred_src if inferred_src == "reviewd" else "",
            path=tn.get("path") or "",
        )
        if meta["reviewer_source"] == "human" and inferred_src and inferred_src != "human":
            meta["reviewer_source"] = inferred_src
        key = (meta["path"], meta["category"] if meta["category"] != "general" else meta["severity"])
        implicit_repeat = bool(orig_sha and seen_key_commits[key] and orig_sha not in seen_key_commits[key])
        if orig_sha:
            seen_key_commits[key].add(orig_sha)
        threads_out.append({
            "reviewer_source": meta["reviewer_source"],
            "severity": meta["severity"],
            "category": meta["category"],
            "is_advisory": meta["is_advisory"],
            "is_timing_noise": meta["is_timing_noise"],
            "is_repeat": meta["explicit_repeat"] or implicit_repeat,
            "path": meta["path"],
            "line": safe_int(tn.get("line") or tn.get("originalLine"), 0),
            "commit": orig_sha[:12],
            "created_at": str(c0.get("createdAt") or ""),
            "reply_count": max(0, len(comments) - 1),
            "is_resolved": bool(tn.get("isResolved")),
            "is_outdated": bool(tn.get("isOutdated")),
        })

    return {
        "repo": repo_slug,
        "number": safe_int(node.get("number"), 0),
        "state": str(node.get("state") or ""),
        "branch": str(node.get("headRefName") or ""),
        "created_at": str(node.get("createdAt") or ""),
        "updated_at": str(node.get("updatedAt") or ""),
        "merged_at": str(node.get("mergedAt") or ""),
        "commits": [c[:12] for c in commits],
        "reviews": reviews_out,
        "threads": threads_out,
    }


def _check_gh_ready():
    if not shutil.which("gh"):
        return False, "gh CLI not found on PATH"
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        return (True, "") if res.returncode == 0 else (False, "gh is not authenticated")
    except Exception as exc:
        return False, f"gh auth check failed: {exc}"


def sync_github_repo(repo_slug, days=30, limit=100, cache_dir=None, out_reviews="", out_papercuts=""):
    """Fetch PR reviews + papercut issues via gh and cache structured JSON locally."""
    owner, _, name = repo_slug.partition("/")
    if not owner or not name:
        raise ValueError(f"invalid GitHub repo slug: {repo_slug!r}")
    since_str, since_ep = resolve_since(days=days)

    prs, cursor = [], None
    page_size = min(40, max(1, limit))
    while len(prs) < limit:
        cmd = [
            "gh", "api", "graphql",
            "-f", f"query={PR_GRAPHQL_QUERY}",
            "-f", f"owner={owner}", "-f", f"name={name}",
            "-F", f"first={min(page_size, limit - len(prs))}",
        ]
        if cursor:
            cmd += ["-f", f"cursor={cursor}"]
        raw = subprocess.check_output(cmd, stderr=subprocess.PIPE, text=True, timeout=60)
        data = json.loads(raw)
        if data.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
        conn = ((data.get("data") or {}).get("repository") or {}).get("pullRequests") or {}
        nodes = conn.get("nodes") or []
        if not nodes:
            break
        stop_old = False
        for node in nodes:
            if not isinstance(node, dict):
                continue
            upd_ep = parse_iso_epoch(node.get("updatedAt") or node.get("createdAt"))
            if since_ep and upd_ep and upd_ep < since_ep:
                stop_old = True
                break
            prs.append(normalize_pr_node(node, repo_slug=repo_slug))
        pi = conn.get("pageInfo") or {}
        if stop_old or not pi.get("hasNextPage") or not pi.get("endCursor"):
            break
        cursor = pi["endCursor"]

    papercut_issues = []
    try:
        pc_raw = subprocess.check_output(
            [
                "gh", "issue", "list", "-R", repo_slug,
                "--label", "papercut", "--state", "all", "--limit", "200",
                "--json", "number,title,body,state,stateReason",
            ],
            stderr=subprocess.PIPE, text=True, timeout=30,
        )
        parsed = json.loads(pc_raw)
        if isinstance(parsed, list):
            papercut_issues = parsed
    except Exception:
        papercut_issues = []

    default_rev, default_pc = cache_paths_for_slug(repo_slug, cache_dir)
    rev_path, pc_path = out_reviews or default_rev, out_papercuts or default_pc
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    atomic_write_json(rev_path, {
        "schema_version": 1, "repo": repo_slug, "synced_at": now_iso,
        "since": since_str, "days": days, "prs": prs,
    })
    atomic_write_json(pc_path, {
        "schema_version": 1, "repo": repo_slug, "synced_at": now_iso,
        "issues": papercut_issues,
    })
    return {
        "repo": repo_slug, "prs_synced": len(prs), "papercuts_synced": len(papercut_issues),
        "reviews_path": rev_path, "papercuts_path": pc_path,
    }


def cmd_sync_github(args):
    """CLI handler for ``debrief sync-github``."""
    best_effort = bool(getattr(args, "best_effort", False))
    slugs = [r.strip() for r in (getattr(args, "gh_repo", None) or []) if r and r.strip()]
    for rp in getattr(args, "repo", None) or []:
        slug = resolve_github_slug(rp.strip()) if rp and rp.strip() else ""
        if slug:
            slugs.append(slug)
    if not slugs:
        slug = resolve_github_slug(os.getcwd())
        if slug:
            slugs.append(slug)
    slugs = list(dict.fromkeys(slugs))

    if not slugs:
        sys.stdout.write(json.dumps({"skipped": True, "reason": "no GitHub repo resolved"}, indent=2) + "\n")
        if best_effort:
            return
        raise SystemExit(2)

    ok, reason = _check_gh_ready()
    if not ok:
        sys.stdout.write(json.dumps({"skipped": True, "reason": reason, "repos": slugs}, indent=2) + "\n")
        if best_effort:
            return
        raise SystemExit(1)

    days = getattr(args, "days", 30) or 30
    limit = getattr(args, "limit", 100) or 100
    cache_dir = getattr(args, "cache_dir", "") or None
    out_rev = getattr(args, "out_reviews", "") or ""
    out_pc = getattr(args, "out_papercuts", "") or ""
    results, errors = [], []
    for slug in slugs:
        try:
            results.append(sync_github_repo(
                slug, days=days, limit=limit, cache_dir=cache_dir,
                out_reviews=out_rev if len(slugs) == 1 else "",
                out_papercuts=out_pc if len(slugs) == 1 else "",
            ))
        except Exception as exc:
            errors.append({"repo": slug, "error": str(exc)})
            if not best_effort:
                sys.stderr.write(f"debrief sync-github: {slug}: {exc}\n")
                raise SystemExit(1)
    sys.stdout.write(json.dumps({"skipped": False, "synced": results, "errors": errors}, indent=2) + "\n")
