#!/usr/bin/env python3
"""Compare the first and last calendar snapshot of a day and record drift.

`diff` prints calendar observations for one day; with `--write` it appends new
ones to `ai/workflow-observations.md` when the learning module is installed.
`summary` groups recent calendar observations into repeat candidates for the
weekly review (three in 28 days, or two in 7 days).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path

SNAPSHOT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{4})--captured-(\d+)--.*\.txt$")
OBSERVATION = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \| [^|]+ \| calendar \| ([^:]+): (.+?) (?:\d{2}:\d{2}-\d{2}:\d{2}|\d+ →)")
MIN_DURATION_CHANGE = 15
JOURNAL = Path("ai/workflow-observations.md")


def parse_day(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a real YYYY-MM-DD date: {value}")


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def snapshots(hub: Path, day: dt.date) -> list[Path]:
    directory = hub / "ai/tmp/calendar-snapshots"
    if not directory.is_dir():
        return []
    found = []
    for path in directory.iterdir():
        match = SNAPSHOT_NAME.match(path.name)
        if match and match.group(1) == day.isoformat() and path.is_file() and not path.is_symlink():
            found.append(((match.group(2), int(match.group(3))), path))
    return [path for _, path in sorted(found)]


def read_events(path: Path) -> dict[str, tuple[str, str]]:
    events = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) != 4:
            continue
        start, end, title, _calendar = parts
        if start == "00:00" and end in ("00:00", "23:59"):
            continue  # all-day events carry no time to drift
        events.setdefault(title, (start, end))
    return events


def drift(day: dt.date, plan: dict, fact: dict) -> list[str]:
    prefix = f"- {day.isoformat()} | evening-review | calendar | "
    lines = []
    for title, (start, end) in plan.items():
        if title not in fact:
            lines.append(f"{prefix}отмена: {title} {start}-{end}")
            continue
        new_start, new_end = fact[title]
        if new_start != start:
            lines.append(f"{prefix}сдвиг: {title} {start}-{end} → {new_start}-{new_end}")
            continue
        before = minutes(end) - minutes(start)
        after = minutes(new_end) - minutes(new_start)
        if abs(after - before) >= MIN_DURATION_CHANGE:
            lines.append(f"{prefix}длительность: {title} {before} → {after} мин")
    for title, (start, end) in fact.items():
        if title not in plan:
            lines.append(f"{prefix}добавлено: {title} {start}-{end}")
    return lines


def append_new(journal: Path, lines: list[str]) -> int:
    existing = set(journal.read_text(encoding="utf-8").splitlines())
    new = [line for line in lines if line not in existing]
    if new:
        text = journal.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        journal.write_text(text + "\n".join(new) + "\n", encoding="utf-8")
    return len(new)


def command_diff(args) -> int:
    found = snapshots(args.hub, args.day)
    if len(found) < 2:
        print(f"{args.day}: недостаточно снимков для сравнения ({len(found)})")
        return 0
    lines = drift(args.day, read_events(found[0]), read_events(found[-1]))
    if not lines:
        print(f"{args.day}: расхождений нет")
        return 0
    print("\n".join(lines))
    if args.write:
        journal = args.hub / JOURNAL
        if not journal.is_file():
            print("модуль learning выключен: журнал не записан")
            return 0
        print(f"записано новых наблюдений: {append_new(journal, lines)}")
    return 0


def project_key(title: str) -> str:
    parts = title.split("/")
    return "/".join(parts[:-1]) if len(parts) > 1 else title


def command_summary(args) -> int:
    journal = args.hub / JOURNAL
    if not journal.is_file():
        print("модуль learning выключен")
        return 0
    groups = defaultdict(list)
    for line in journal.read_text(encoding="utf-8").splitlines():
        match = OBSERVATION.match(line)
        if not match:
            continue
        day = dt.date.fromisoformat(match.group(1))
        if 0 <= (args.until - day).days < 28:
            groups[(match.group(2), project_key(match.group(3)))].append(day)
    candidates = []
    for (kind, key), days in sorted(groups.items()):
        week = [d for d in days if (args.until - d).days < 7]
        if len(days) >= 3 or len(week) >= 2:
            candidates.append(f"{kind} | {key} | {len(days)}")
    print("\n".join(candidates) if candidates else "повторов нет")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("--day", required=True, type=parse_day)
    diff.add_argument("--write", action="store_true")
    summary = commands.add_parser("summary")
    summary.add_argument("--until", required=True, type=parse_day)
    args = parser.parse_args()
    return command_diff(args) if args.command == "diff" else command_summary(args)


if __name__ == "__main__":
    sys.exit(main())
