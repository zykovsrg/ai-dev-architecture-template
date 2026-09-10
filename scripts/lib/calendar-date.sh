#!/usr/bin/env bash

valid_calendar_date() {
  local value="$1" normalized
  [[ "$value" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || return 1
  normalized="$(TZ=UTC date -j -f '%Y-%m-%d %H:%M:%S' "$value 12:00:00" '+%F' 2>/dev/null)" || return 1
  [ "$normalized" = "$value" ]
}
