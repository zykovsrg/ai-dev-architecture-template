# Calendar Timezone Serialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local EventKit bridge return ISO 8601 timestamps with each event's timezone.

**Architecture:** Correct serialization only at the EventKit boundary. The bridge formats event bounds in the event timezone, falling back to the local timezone. The existing shell check verifies the wiring and compiles the bridge.

**Tech Stack:** Swift, Foundation, EventKit, Bash, macOS `swiftc`, `shasum`.

## Global Constraints

- Do not change EventKit access, event selection, or write behavior.
- Preserve all-day inclusive-to-exclusive conversion.
- Keep the bridge checksum manifest valid.
- `Europe/Kirov` must serialize with `+03:00`.

---

### Task 1: Serialize event bounds in their timezone

**Files:**
- Modify: `calendar-policy/bridge/hub_eventkit_bridge.swift:16-19,123-131`
- Modify: `scripts/apple-calendar-bridge-test.sh:18-31`
- Modify: `calendar-policy/bridge/SHA256SUMS`

**Interfaces:**
- Consumes: `EKEvent.startDate`, `EKEvent.endDate`, `EKEvent.timeZone`.
- Produces: event JSON whose ISO 8601 offsets match its `timezone` field.

- [ ] **Step 1: Write the failing regression guard**

Add after the all-day assertions in `scripts/apple-calendar-bridge-test.sh`:

```bash
grep -Fq 'func isoText(_ date: Date, timezone: TimeZone)' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge does not format event times in their timezone"
grep -Fq 'formatter.timeZone = timezone' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge timestamp formatter ignores the event timezone"
grep -Fq 'let eventZone = event.timeZone ?? TimeZone.current' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge has no local-timezone fallback"
grep -Fq '"start": isoText(event.startDate, timezone: eventZone)' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge start timestamp is not timezone-aware"
grep -Fq '"end": isoText(event.isAllDay ? (exclusiveEnd(event.endDate) ?? event.endDate) : event.endDate, timezone: eventZone)' "$BRIDGE/hub_eventkit_bridge.swift" || fail "bridge end timestamp is not timezone-aware"
```

- [ ] **Step 2: Run the guard and verify it fails**

```bash
bash scripts/apple-calendar-bridge-test.sh
```

Expected: `FAIL: bridge does not format event times in their timezone`.

- [ ] **Step 3: Implement the minimal serializer correction**

Replace the helper with:

```swift
func isoText(_ date: Date, timezone: TimeZone) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    formatter.timeZone = timezone
    return formatter.string(from: date)
}
```

At the start of `describe(_ event: EKEvent)`, add:

```swift
let eventZone = event.timeZone ?? TimeZone.current
```

Use it for the event response:

```swift
"start": isoText(event.startDate, timezone: eventZone),
"end": isoText(event.isAllDay ? (exclusiveEnd(event.endDate) ?? event.endDate) : event.endDate, timezone: eventZone),
"timezone": eventZone.identifier,
```

- [ ] **Step 4: Update the checksum**

```bash
(cd calendar-policy/bridge && shasum -a 256 hub_eventkit_bridge.swift | sed 's#  hub_eventkit_bridge.swift#  ./hub_eventkit_bridge.swift#' > SHA256SUMS)
```

- [ ] **Step 5: Verify the fix and build**

```bash
bash scripts/apple-calendar-bridge-test.sh
```

Expected: `PASS: local EventKit bridge is present and buildable.`

- [ ] **Step 6: Run the policy suite**

```bash
bash scripts/apple-calendar-policy-test.sh
```

Expected: all pytest checks pass.

- [ ] **Step 7: Commit the focused fix**

```bash
git add calendar-policy/bridge/hub_eventkit_bridge.swift calendar-policy/bridge/SHA256SUMS scripts/apple-calendar-bridge-test.sh
git commit -m "fix: preserve event timezone in calendar bridge"
```

### Task 2: Verify the installed bridge remains protected

**Files:**
- Test: `scripts/calendar-policy-install-test.sh`

**Interfaces:**
- Consumes: the checksum-valid bridge from Task 1.
- Produces: a verified installable policy bundle.

- [ ] **Step 1: Run the install integrity test**

```bash
bash scripts/calendar-policy-install-test.sh
```

Expected: the temporary install succeeds and the tampered copy is rejected.

- [ ] **Step 2: Inspect the final diff**

```bash
git diff --check HEAD~1..HEAD
git status --short
```

Expected: no whitespace errors and no generated bridge bundle.
