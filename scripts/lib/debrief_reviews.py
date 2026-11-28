#!/usr/bin/env python3
"""Offline PR-review escape aggregation and session/skill joins for /debrief."""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debrief_common import canon_skill, read_json, safe_int  # noqa: E402
from debrief_github import normalize_pr_node, parse_iso_epoch  # noqa: E402

CATEGORY_HINTS = {
    "evidence-overclaim": "tighten pre-push claim re-measurement and forbid unbacked PR proof statements",
    "false-green-proof": "add mutation/negative-leg checks and verify assertions hit the real production path",
    "runtime-proof-gap": "separate CI-pending review timing from true missing local proof; attach run evidence",
    "missing-proof": "require executed focused/live proof receipts before opening or re-pushing a PR",
    "generated-drift-risk": "add a sync/drift guard test or regenerate committed artifacts before push",
    "contract-mismatch": "diff published contracts/schemas/docs against touched implementation paths before push",
    "missing-coverage": "add direct coverage for every new branch and guard before handoff",
    "rollback-risk": "verify backward-compatible deploy/rollback guards when changing schema or DDL",
    "wrong-aggregation": "pin multi-label/partition aggregation semantics with adversarial unit fixtures",
    "scope-smuggling": "re-verify diff file list against PR description at final HEAD",
    "wording-loophole": "review rule/doc changes for silent skip or fail-open loopholes",
}


def _match_pr_sessions(pr, metas_by_branch, metas_by_commit):
    """Join a PR record to local Stage 1 sessions by branch name or commit prefix."""
    matched = {}
    br = str(pr.get("branch") or "").strip()
    if br and br not in ("main", "master", "HEAD"):
        for m in metas_by_branch.get(br, []):
            matched[(m["harness"], m["id"])] = m
    for sha in pr.get("commits") or []:
        short = str(sha or "")[:8]
        if len(short) >= 7:
            for m in metas_by_commit.get(short, []):
                matched[(m["harness"], m["id"])] = m
    return list(matched.values())


def review_escape_stats(paths, metas=None, since_epoch=0.0):
    """Aggregate offline PR-review snapshots and join to local sessions/skills."""
    valid_paths = [p for p in (paths or []) if p and os.path.isfile(p)]
    if not valid_paths:
        return None

    prs, sources, seen_pr_keys = [], [], set()
    for path in valid_paths:
        raw = read_json(path)
        if not raw:
            continue
        sources.append(path)
        items = raw.get("prs") if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        repo_hint = raw.get("repo", "") if isinstance(raw, dict) else ""
        for pr in items or []:
            if not isinstance(pr, dict):
                continue
            if "reviewThreads" in pr or "headRefName" in pr:
                pr = normalize_pr_node(pr, repo_slug=pr.get("repo") or repo_hint)
            upd = parse_iso_epoch(pr.get("updated_at") or pr.get("created_at"))
            if since_epoch and upd and upd < since_epoch:
                continue
            key = (pr.get("repo") or repo_hint, safe_int(pr.get("number"), 0))
            if key in seen_pr_keys:
                continue
            seen_pr_keys.add(key)
            prs.append(pr)

    if not prs and not sources:
        return None

    metas_by_branch = defaultdict(list)
    metas_by_commit = defaultdict(list)
    for m in (metas or {}).values():
        br = str(m.get("branch") or "").strip()
        if br and br not in ("main", "master", "HEAD"):
            metas_by_branch[br].append(m)
        cm = str(m.get("commit") or "").strip()
        if len(cm) >= 7:
            metas_by_commit[cm[:8]].append(m)

    prs_reviewed = prs_real_escape = prs_multi_round = prs_repeat_p1 = 0
    prs_repeat_p1_real = prs_repeat_p1_timing = 0
    real_p0 = real_p1 = real_p2 = real_ungraded = timing_p1 = 0
    repeat_p1_real = repeat_p1_timing = 0
    threads_total = threads_unanswered = threads_unresolved_merged = 0
    joined_prs = unjoined_prs = 0

    by_reviewer = Counter()
    by_cat = defaultdict(lambda: {"p0": 0, "p1": 0, "p2": 0, "ungraded": 0, "repeat": 0, "prs": set()})
    by_timing_cat = Counter()
    by_harness = defaultdict(lambda: {"prs": 0, "real_escape_prs": 0, "real_p1": 0, "real_p2": 0, "repeat_p1_prs": 0})
    by_skill = defaultdict(lambda: {"prs": 0, "real_p1": 0, "real_p2": 0, "timing_p1": 0, "categories": Counter()})
    top_repeat = []

    for pr in prs:
        revs = pr.get("reviews") or []
        threads = pr.get("threads") or []
        if not revs and not threads:
            continue
        prs_reviewed += 1
        if len(revs) >= 2:
            prs_multi_round += 1
        for r in revs:
            by_reviewer[r.get("reviewer_source") or "human"] += 1

        pr_real_p0 = pr_real_p1 = pr_real_p2 = pr_timing_p1 = 0
        pr_rep_real = pr_rep_timing = 0
        pr_real_cats = Counter()

        for t in threads:
            threads_total += 1
            if safe_int(t.get("reply_count"), 0) == 0:
                threads_unanswered += 1
            if str(pr.get("state") or "").upper() == "MERGED" and not t.get("is_resolved"):
                threads_unresolved_merged += 1
            sev = str(t.get("severity") or "ungraded").upper()
            cat = str(t.get("category") or "general").lower()
            is_noise = bool(t.get("is_timing_noise"))
            is_rep = bool(t.get("is_repeat"))
            is_adv = bool(t.get("is_advisory"))
            if not revs:
                by_reviewer[t.get("reviewer_source") or "human"] += 1

            if is_noise:
                timing_p1 += 1
                pr_timing_p1 += 1
                by_timing_cat[cat] += 1
                if is_rep:
                    repeat_p1_timing += 1
                    pr_rep_timing += 1
                continue

            if sev == "P0":
                real_p0 += 1
                pr_real_p0 += 1
                by_cat[cat]["p0"] += 1
                by_cat[cat]["prs"].add(pr["number"])
                pr_real_cats[cat] += 1
                if is_rep:
                    repeat_p1_real += 1
                    pr_rep_real += 1
                    by_cat[cat]["repeat"] += 1
            elif sev == "P1":
                real_p1 += 1
                pr_real_p1 += 1
                by_cat[cat]["p1"] += 1
                by_cat[cat]["prs"].add(pr["number"])
                pr_real_cats[cat] += 1
                if is_rep:
                    repeat_p1_real += 1
                    pr_rep_real += 1
                    by_cat[cat]["repeat"] += 1
            elif sev == "P2" and not is_adv:
                real_p2 += 1
                pr_real_p2 += 1
                by_cat[cat]["p2"] += 1
                by_cat[cat]["prs"].add(pr["number"])
                pr_real_cats[cat] += 1
                if is_rep:
                    by_cat[cat]["repeat"] += 1
            elif sev == "UNGRADED":
                real_ungraded += 1
                by_cat[cat]["ungraded"] += 1
                by_cat[cat]["prs"].add(pr["number"])
                if is_rep:
                    by_cat[cat]["repeat"] += 1

        rev_p1_rounds = sum(1 for r in revs if safe_int((r.get("counts") or {}).get("P1"), 0) > 0)
        has_rep_p1 = (pr_rep_real + pr_rep_timing) > 0 or rev_p1_rounds >= 2
        if pr_real_p0 + pr_real_p1 + pr_real_p2 > 0:
            prs_real_escape += 1
        if has_rep_p1:
            prs_repeat_p1 += 1
            if pr_rep_real > 0:
                prs_repeat_p1_real += 1
            elif pr_rep_timing > 0:
                prs_repeat_p1_timing += 1
            top_repeat.append({
                "repo": pr.get("repo") or "",
                "number": pr["number"],
                "state": pr.get("state") or "",
                "review_rounds": len(revs),
                "real_p1": pr_real_p1,
                "timing_p1": pr_timing_p1,
                "repeat_real": pr_rep_real,
                "repeat_timing": pr_rep_timing,
                "categories": [c for c, _ in pr_real_cats.most_common(3)],
            })

        matched = _match_pr_sessions(pr, metas_by_branch, metas_by_commit)
        if matched:
            joined_prs += 1
            harnesses_seen, skills_seen = set(), set()
            for m in matched:
                harnesses_seen.add(str(m.get("harness") or "unknown"))
                for sk in (m.get("skill_loads") or m.get("skills") or []):
                    csk = canon_skill(sk)
                    if csk:
                        skills_seen.add(csk)
            for h in harnesses_seen:
                bh = by_harness[h]
                bh["prs"] += 1
                if pr_real_p0 + pr_real_p1 + pr_real_p2 > 0:
                    bh["real_escape_prs"] += 1
                bh["real_p1"] += pr_real_p1
                bh["real_p2"] += pr_real_p2
                if has_rep_p1:
                    bh["repeat_p1_prs"] += 1
            for sk in skills_seen:
                bs = by_skill[sk]
                bs["prs"] += 1
                bs["real_p1"] += pr_real_p1
                bs["real_p2"] += pr_real_p2
                bs["timing_p1"] += pr_timing_p1
                bs["categories"].update(pr_real_cats)
        else:
            unjoined_prs += 1

    cat_rows = []
    for cat, d in sorted(
        by_cat.items(),
        key=lambda kv: (-(kv[1]["p0"] * 5 + kv[1]["p1"] * 3 + kv[1]["p2"]), -kv[1]["ungraded"], kv[0]),
    ):
        cat_rows.append({
            "category": cat,
            "p0": d["p0"], "p1": d["p1"], "p2": d["p2"],
            "ungraded": d["ungraded"], "repeat": d["repeat"],
            "prs": sorted(d["prs"])[:8],
            "hint": CATEGORY_HINTS.get(cat, "add a pre-push check or skill rule targeting this defect class"),
        })

    per_skill_out = {
        sk: {
            "prs": d["prs"], "real_p1": d["real_p1"], "real_p2": d["real_p2"],
            "timing_p1": d["timing_p1"], "top_categories": dict(d["categories"].most_common(4)),
        }
        for sk, d in sorted(by_skill.items())
    }

    top_repeat.sort(key=lambda r: (-(r["repeat_real"] * 3 + r["repeat_timing"] + r["review_rounds"]), -r["number"]))
    return {
        "sources": sources,
        "prs_total": len(prs),
        "prs_reviewed": prs_reviewed,
        "prs_with_real_escapes": prs_real_escape,
        "escape_rate_pct": round(100.0 * prs_real_escape / prs_reviewed, 1) if prs_reviewed else None,
        "prs_multi_round": prs_multi_round,
        "prs_with_repeat_p1": prs_repeat_p1,
        "prs_with_repeat_p1_real": prs_repeat_p1_real,
        "prs_with_repeat_p1_timing": prs_repeat_p1_timing,
        "repeat_p1_rate_pct": round(100.0 * prs_repeat_p1 / prs_multi_round, 1) if prs_multi_round else None,
        "real_p0": real_p0, "real_p1": real_p1, "real_p2": real_p2, "real_ungraded": real_ungraded,
        "timing_noise_p1": timing_p1,
        "repeat_p1_real": repeat_p1_real, "repeat_p1_timing": repeat_p1_timing,
        "threads_total": threads_total, "threads_unanswered": threads_unanswered,
        "unanswered_pct": round(100.0 * threads_unanswered / threads_total, 1) if threads_total else None,
        "threads_unresolved_on_merged": threads_unresolved_merged,
        "joined_prs": joined_prs, "unjoined_prs": unjoined_prs,
        "by_reviewer_source": dict(by_reviewer.most_common()),
        "by_category": cat_rows[:15],
        "by_timing_noise_category": dict(by_timing_cat.most_common()),
        "by_harness": dict(sorted(by_harness.items())),
        "per_skill": per_skill_out,
        "top_repeat_prs": top_repeat[:10],
    }
