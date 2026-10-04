#!/usr/bin/env python3
"""Hub rule catalog: validate model cases, score rules, merge, render, report.

Writes only ai/learning/rules.json, ai/learning/scan-ledger.json,
ai/learned-rules.md and ai/learned-rules/<project-id>.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_collect import load_ledger, mark_processed, registry, save_json  # noqa: E402

CATALOG = "ai/learning/rules.json"
THRESHOLD = 0.7
GLOBAL_LIMIT = 10
EFFECTS = ("confirm", "contradict", "explicit")
KINDS = ("preference", "agent-habit")
PERSONAL = [
    re.compile(r"\+?\d[\d\s()-]{6,}\d"),
    re.compile(r"[\w.+-]+@[\w-]+\.\w+"),
    re.compile(r"\d[\d\s]*\s?(₽|руб|\$|€|eur|usd)", re.I),
    re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+"),
]


def empty_catalog():
    return {"format": 1, "next_id": 1, "rules": []}


def _base(sessions):
    if sessions >= 11:
        return 0.85
    if sessions >= 6:
        return 0.7
    if sessions >= 3:
        return 0.5
    return 0.3 if sessions else 0.0


def confidence(rule, today):
    positive = [c for c in rule["cases"] if c["effect"] in ("confirm", "explicit")]
    value = _base(len({c["session"] for c in positive}))
    if any(c["effect"] == "explicit" for c in positive):
        value = max(value, THRESHOLD)
    value -= 0.1 * len({c["session"] for c in rule["cases"] if c["effect"] == "contradict"})
    if positive:
        last = max(date.fromisoformat(c["date"]) for c in positive)
        weeks = (today - last).days // 7
        value -= 0.02 * max(0, weeks - 4)
    return round(min(0.9, max(0.0, value)), 2)


def scope(rule, today):
    if rule.get("explicit_scope") == "global":
        return "global"
    projects = {c["project"] for c in rule["cases"] if c["effect"] != "contradict"}
    return "global" if len(projects) >= 2 and confidence(rule, today) >= THRESHOLD else "project"


def looks_personal(text):
    return any(p.search(text) for p in PERSONAL)


def _find(catalog, rid):
    for rule in catalog["rules"]:
        if rule["id"] == rid:
            return rule
    return None


def _state(rule, today):
    return (confidence(rule, today) >= THRESHOLD, scope(rule, today))


def apply_batch(catalog, ledger, batch, cases, registry_ids, today, now):
    work = copy.deepcopy(catalog)
    sessions = {(s["tool"], s["id"]): s for s in batch["sessions"]}
    before = {r["id"]: _state(r, today) for r in work["rules"]}
    new_ids = []
    for index, item in enumerate(cases):
        where = f"case {index}"
        key = (item.get("tool"), item.get("session"))
        if key not in sessions:
            raise ValueError(f"{where}: session not in batch")
        if item.get("effect") not in EFFECTS:
            raise ValueError(f"{where}: bad effect")
        entry = sessions[key]
        if entry["project"] != "hub" and entry["project"] not in registry_ids:
            raise ValueError(f"{where}: unregistered project")
        note = str(item.get("note", ""))
        if not note or len(note) > 200 or looks_personal(note):
            raise ValueError(f"{where}: bad note")
        if item.get("rule") == "new":
            text = str(item.get("text", ""))
            if not text or len(text) > 200 or looks_personal(text) or item.get("kind") not in KINDS:
                raise ValueError(f"{where}: bad new rule")
            rule = {"id": f"R-{work['next_id']}", "text": text, "kind": item["kind"], "status": "active",
                    "merged_into": None, "explicit_scope": None, "created": today.isoformat(),
                    "cases": [], "history": [{"date": today.isoformat(), "event": "added", "detail": text}]}
            work["next_id"] += 1
            work["rules"].append(rule)
            new_ids.append(rule["id"])
        else:
            rule = _find(work, item.get("rule"))
            if rule is None or rule["status"] != "active":
                raise ValueError(f"{where}: unknown rule")
        if item["effect"] == "explicit":
            if item.get("scope") not in ("global", "project"):
                raise ValueError(f"{where}: explicit case needs scope")
            if rule["explicit_scope"] != "global":
                rule["explicit_scope"] = item["scope"]
        rule["cases"].append({"effect": item["effect"], "project": entry["project"], "tool": entry["tool"],
                              "session": entry["id"], "date": entry["date"], "note": note})
    for rule in work["rules"]:
        old = before.get(rule["id"])
        new = _state(rule, today)
        if old and old[0] != new[0]:
            rule["history"].append({"date": today.isoformat(), "event": "confidence",
                                    "detail": "injected" if new[0] else "not injected"})
        if new[1] == "global" and (old is None or old[1] != "global"):
            rule["history"].append({"date": today.isoformat(), "event": "global", "detail": ""})
    for tool in ("claude", "codex"):
        mark_processed(ledger, tool, [s["id"] for s in batch["sessions"] if s["tool"] == tool], now)
    catalog.clear()
    catalog.update(work)
    return new_ids


def _injected(catalog, today):
    return [r for r in catalog["rules"] if r["status"] == "active" and confidence(r, today) >= THRESHOLD]


def _line(rule, today):
    return f"- {rule['id']}: {rule['text']} (уверенность {confidence(rule, today):.2f})"


HEADER = ("# Learned rules\n\nGenerated by scripts/session_rules.py. Do not edit by hand; "
          "change rules through the learning catalog.\n\n")


def render(catalog, today):
    glob, per_project = [], {}
    for rule in _injected(catalog, today):
        projects = {c["project"] for c in rule["cases"] if c["effect"] != "contradict"}
        if scope(rule, today) == "global" or projects == {"hub"}:
            glob.append(rule)
        else:
            for pid in projects - {"hub"}:
                per_project.setdefault(pid, []).append(rule)
    order = lambda r: (-confidence(r, today), int(r["id"].split("-")[1]) if r["id"].split("-")[1].isdigit() else 0)
    glob.sort(key=order)
    out = {"ai/learned-rules.md": HEADER + ("\n".join(_line(r, today) for r in glob[:GLOBAL_LIMIT]) or "- Нет правил.") + "\n"}
    for pid, rules in per_project.items():
        rules.sort(key=order)
        out[f"ai/learned-rules/{pid}.md"] = HEADER + "\n".join(_line(r, today) for r in rules) + "\n"
    return out


def merge(catalog, source, target, today):
    src, dst = _find(catalog, source), _find(catalog, target)
    if not src or not dst or src is dst or src["status"] != "active" or dst["status"] != "active":
        raise ValueError("merge needs two different active rules")
    moved = [dict(c, merged_from=source) for c in src["cases"]]
    dst["cases"].extend(moved)
    src["status"], src["merged_into"] = "merged", target
    stamp = today.isoformat()
    src["history"].append({"date": stamp, "event": "merged", "detail": f"into {target}"})
    dst["history"].append({"date": stamp, "event": "merged", "detail": f"from {source}"})


def unmerge(catalog, source, today):
    src = _find(catalog, source)
    if not src or src["status"] != "merged":
        raise ValueError("rule is not merged")
    dst = _find(catalog, src["merged_into"])
    dst["cases"] = [c for c in dst["cases"] if c.get("merged_from") != source]
    src["status"], src["merged_into"] = "active", None
    stamp = today.isoformat()
    src["history"].append({"date": stamp, "event": "unmerged", "detail": f"from {dst['id']}"})
    dst["history"].append({"date": stamp, "event": "unmerged", "detail": f"{source} restored"})


def report(catalog, since):
    events = []
    for rule in catalog["rules"]:
        for item in rule["history"]:
            if date.fromisoformat(item["date"]) >= since:
                events.append(dict(item, rule=rule["id"], text=rule["text"]))
    return sorted(events, key=lambda e: (e["date"], e["rule"]))


def relevant(catalog, project, today, limit=60):
    active = [r for r in catalog["rules"] if r["status"] == "active"]
    def rank(r):
        near = any(c["project"] == project for c in r["cases"]) or scope(r, today) == "global"
        return (0 if near else 1, -confidence(r, today))
    active.sort(key=rank)
    return [{"id": r["id"], "text": r["text"], "kind": r["kind"]} for r in active[:limit]]


def load_catalog(hub):
    path = hub / CATALOG
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty_catalog()


def write_render(hub, catalog, today):
    for rel, text in render(catalog, today).items():
        path = hub / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    folder = hub / "ai/learned-rules"
    current = set(render(catalog, today))
    if folder.is_dir():
        for stale in folder.glob("*.md"):
            if f"ai/learned-rules/{stale.name}" not in current:
                stale.write_text(HEADER + "- Нет правил.\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--today", default=date.today().isoformat())
    sub = parser.add_subparsers(dest="cmd", required=True)
    rel = sub.add_parser("relevant")
    rel.add_argument("--project", required=True)
    app = sub.add_parser("apply")
    app.add_argument("--batch", required=True, type=Path)
    app.add_argument("--cases", required=True, type=Path)
    mer = sub.add_parser("merge")
    mer.add_argument("--from", dest="source", required=True)
    mer.add_argument("--into", required=True)
    unm = sub.add_parser("unmerge")
    unm.add_argument("--rule", required=True)
    sub.add_parser("render")
    rep = sub.add_parser("report")
    rep.add_argument("--since")
    done = sub.add_parser("weekly-done")
    done.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    hub, today = args.hub.resolve(), date.fromisoformat(args.today)
    catalog, ledger = load_catalog(hub), load_ledger(hub)
    if args.cmd == "relevant":
        print(json.dumps(relevant(catalog, args.project, today), ensure_ascii=False))
        return
    if args.cmd == "report":
        since = args.since or ledger.get("last_weekly_review") or ledger.get("cutover") or today.isoformat()
        print(json.dumps({"since": since, "events": report(catalog, date.fromisoformat(since))}, ensure_ascii=False))
        return
    if args.cmd == "weekly-done":
        ledger["last_weekly_review"] = args.date
        save_json(hub / "ai/learning/scan-ledger.json", ledger)
        return
    if args.cmd == "apply":
        batch = json.loads(args.batch.read_text(encoding="utf-8"))
        cases = json.loads(args.cases.read_text(encoding="utf-8"))
        ids = {pid for pid, e in registry(hub).items() if e.get("status") == "active"}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            new = apply_batch(catalog, ledger, batch, cases, ids, today, now)
        except ValueError as error:
            raise SystemExit(f"ERROR: {error}")
        save_json(hub / CATALOG, catalog)
        save_json(hub / "ai/learning/scan-ledger.json", ledger)
        print(json.dumps({"new_rules": new, "cases": len(cases)}))
    elif args.cmd == "merge":
        merge(catalog, args.source, args.into, today)
        save_json(hub / CATALOG, catalog)
    elif args.cmd == "unmerge":
        unmerge(catalog, args.rule, today)
        save_json(hub / CATALOG, catalog)
    write_render(hub, catalog, today)


if __name__ == "__main__":
    main()
