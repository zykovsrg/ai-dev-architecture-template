#!/usr/bin/env python3
"""Reject a day-plan draft that does not contain the complete fixed structure."""

import argparse
import sys

HEADINGS = [
    "## Текущий календарь",
    "## Синхронизация",
    "## Просроченные задачи",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reminders', action='store_true')
    args = parser.parse_args()
    headings = ['## Календарь', '## Напоминания'] if args.reminders else HEADINGS
    lines = [line.rstrip("\r\n") for line in sys.stdin]
    actual = [line for line in lines if line.startswith("## ")]
    if actual != headings:
        raise SystemExit("ERROR: expected exactly the required day-plan headings in order")
    positions: list[int] = []
    for heading in headings:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise SystemExit(f"ERROR: expected exactly one {heading}")
        positions.append(matches[0])
    if positions != sorted(positions):
        raise SystemExit("ERROR: day-plan headings are out of order")
    for index, position in enumerate(positions):
        end = positions[index + 1] if index + 1 < len(positions) else len(lines)
        if not any(line.strip() for line in lines[position + 1:end]):
            raise SystemExit(f"ERROR: empty day-plan section: {headings[index]}")
    print("day-plan structure valid")


if __name__ == "__main__":
    main()
