#!/usr/bin/env python3
"""Shared strict helpers for canonical task-record dates."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def read_due(lines):
    values = []
    for line in lines:
        match = re.fullmatch(r"\s*(?:Due|due):\s*(.*?)\s*", line)
        if match:
            value = match.group(1)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("invalid_due")
            date.fromisoformat(value)
            values.append(value)
    if len(set(values)) > 1:
        raise ValueError("conflicting_due")
    return values[0] if values else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("read", nargs="?")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    try:
        due = read_due(args.file.read_text(encoding="utf-8").splitlines())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"due": due}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
