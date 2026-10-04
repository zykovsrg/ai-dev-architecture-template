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
