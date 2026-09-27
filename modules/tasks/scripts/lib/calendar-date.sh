#!/usr/bin/env bash

valid_calendar_date() {
  local value="$1"
  [[ "$value" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || return 1
  python3 - "$value" <<'PY' >/dev/null 2>&1
import datetime
import sys
try:
    parsed = datetime.date.fromisoformat(sys.argv[1])
except ValueError:
    raise SystemExit(1)
raise SystemExit(0 if parsed.isoformat() == sys.argv[1] else 1)
PY
}
