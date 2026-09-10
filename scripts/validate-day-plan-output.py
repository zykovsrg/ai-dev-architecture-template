#!/usr/bin/env python3
"""Reject a day-plan draft that does not contain the complete fixed structure."""

import sys

HEADINGS = [
    "## Текущий календарь",
    "## Конфликты",
    "## Задачи вне календаря",
    "## Просроченные задачи",
    "## Предлагаемый календарь",
    "## Рекомендации",
]


def main() -> None:
    lines = [line.rstrip("\r\n") for line in sys.stdin]
    positions: list[int] = []
    for heading in HEADINGS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise SystemExit(f"ERROR: expected exactly one {heading}")
        positions.append(matches[0])
    if positions != sorted(positions):
        raise SystemExit("ERROR: day-plan headings are out of order")
    for index, position in enumerate(positions):
        end = positions[index + 1] if index + 1 < len(positions) else len(lines)
        if not any(line.strip() for line in lines[position + 1:end]):
            raise SystemExit(f"ERROR: empty day-plan section: {HEADINGS[index]}")
    print("day-plan structure valid")


if __name__ == "__main__":
    main()
