import EventKit
import Foundation

// Every operation prints exactly one JSON envelope and exits 0.
// A non-zero exit means the bridge itself failed, not the request.

func emit(_ value: Any) -> Never {
    guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
          let text = String(data: data, encoding: .utf8) else { exit(2) }
    print(text)
    exit(0)
}

func ok(_ data: Any) -> Never { emit(["ok": true, "data": data]) }
func fail(_ code: String) -> Never { emit(["ok": false, "error": code]) }

let withFractions = ISO8601DateFormatter()
withFractions.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
let plain = ISO8601DateFormatter()

func parseDate(_ text: String) -> Date? {
    withFractions.date(from: text) ?? plain.date(from: text)
}

func isoText(_ date: Date) -> String { plain.string(from: date) }

// EventKit stores the end of an all-day event inclusively: a single day ends on
// that same day. The policy layer speaks the iCal convention, where the end is
// exclusive and a single day ends on the next one. Convert on every crossing,
// and do it in calendar days: a DST change makes a day shorter or longer than
// 86400 seconds, which would move the boundary onto the wrong date.
let dayCalendar = Calendar.current

func shiftDay(_ date: Date, _ days: Int) -> Date? {
    dayCalendar.date(byAdding: .day, value: days, to: date)
}

func inclusiveEnd(_ end: Date) -> Date? { shiftDay(end, -1) }

// EventKit does not keep the inclusive end at midnight: it stores the last
// instant of the closing day (23:59:59). Normalise to that day's start before
// stepping forward, or the exclusive end would come back one second short.
func exclusiveEnd(_ end: Date) -> Date? { shiftDay(dayCalendar.startOfDay(for: end), 1) }

let operation = CommandLine.arguments.dropFirst().first ?? ""

// macOS attributes a Calendar decision to the responsible process, which for a
// spawned bridge is the MCP client, not this bundle. Re-spawn ourselves once
// with the disclaim attribute set: the child becomes responsible for itself, so
// the grant stored against this bundle identifier is the one that applies.
// Standard streams are inherited, so the payload protocol is unchanged.
//
// The disclaim attribute has no public symbol; it is resolved at run time and
// the bridge still works without it, falling back to the client's own Calendar
// permission.
typealias SetDisclaim = @convention(c) (UnsafeMutablePointer<posix_spawnattr_t?>, Int32) -> Int32

if ProcessInfo.processInfo.environment["HUB_BRIDGE_DISCLAIMED"] == nil,
   let symbol = dlsym(UnsafeMutableRawPointer(bitPattern: -2), "responsibility_spawnattrs_setdisclaim") {
    let setDisclaim = unsafeBitCast(symbol, to: SetDisclaim.self)
    var attributes: posix_spawnattr_t?
    posix_spawnattr_init(&attributes)
    defer { posix_spawnattr_destroy(&attributes) }
    guard setDisclaim(&attributes, 1) == 0 else { exit(2) }

    let executable = CommandLine.arguments[0]
    var arguments = CommandLine.arguments.map { strdup($0) }
    arguments.append(nil)
    var environment = ProcessInfo.processInfo.environment
    environment["HUB_BRIDGE_DISCLAIMED"] = "1"
    var environmentEntries = environment.map { strdup("\($0.key)=\($0.value)") }
    environmentEntries.append(nil)

    var childPID: pid_t = 0
    let spawned = posix_spawn(&childPID, executable, nil, &attributes, &arguments, &environmentEntries)
    guard spawned == 0 else { exit(2) }
    var childStatus: Int32 = 0
    waitpid(childPID, &childStatus, 0)
    exit((childStatus & 0x7f) == 0 ? (childStatus >> 8) & 0xff : 2)
}

let store = EKEventStore()

// `status` must never trigger the macOS access prompt.
if operation == "status" {
    let value: String
    switch EKEventStore.authorizationStatus(for: .event) {
    case .fullAccess: value = "granted"
    case .notDetermined: value = "not_determined"
    default: value = "denied"
    }
    ok(["permission": value])
}

// `request` exists only for the one-time grant run started through
// LaunchServices, so this bundle — not the client that spawns it later — is the
// process macOS attributes the Calendar prompt to. It reads no payload.
if operation == "request" {
    let grantSemaphore = DispatchSemaphore(value: 0)
    var grantResult = false
    store.requestFullAccessToEvents { granted, _ in grantResult = granted; grantSemaphore.signal() }
    grantSemaphore.wait()
    ok(["granted": grantResult])
}

let knownOperations: Set<String> = ["calendars", "events", "event", "create", "update", "delete"]
guard knownOperations.contains(operation) else { fail("UNSUPPORTED_OPERATION") }

let input = FileHandle.standardInput.readDataToEndOfFile()
guard let payload = (try? JSONSerialization.jsonObject(with: input)) as? [String: Any] else {
    fail("INVALID_PAYLOAD")
}

let semaphore = DispatchSemaphore(value: 0)
var allowed = false
store.requestFullAccessToEvents { granted, _ in allowed = granted; semaphore.signal() }
semaphore.wait()
guard allowed else { fail("CALENDAR_ACCESS_DENIED") }

let localZone = TimeZone.current.identifier

func describe(_ event: EKEvent) -> [String: Any] {
    [
        "id": event.calendarItemIdentifier,
        "calendar_id": event.calendar.calendarIdentifier,
        "title": event.title ?? "",
        "start": isoText(event.startDate),
        "end": isoText(event.isAllDay ? (exclusiveEnd(event.endDate) ?? event.endDate) : event.endDate),
        "timezone": event.timeZone?.identifier ?? localZone,
        "all_day": event.isAllDay,
    ]
}

// EventKit gives every occurrence of a series the same calendarItemIdentifier,
// so an identifier alone resolves to the series. When the caller names the
// occurrence start, search a day-wide window and pick the instance that begins
// exactly then; that instance is what EKSpan.thisEvent then acts on.
func resolveEvent(_ eventID: String, _ occurrenceStart: Date?) -> EKEvent? {
    guard let occurrenceStart else {
        return store.calendarItem(withIdentifier: eventID) as? EKEvent
    }
    let window = store.predicateForEvents(
        withStart: occurrenceStart.addingTimeInterval(-86400),
        end: occurrenceStart.addingTimeInterval(86400),
        calendars: nil
    )
    return store.events(matching: window).first {
        $0.calendarItemIdentifier == eventID
            && abs($0.startDate.timeIntervalSince(occurrenceStart)) < 1
    }
}

func occurrenceStart(_ payload: [String: Any]) -> Date?? {
    guard let text = payload["occurrence_start"] as? String else { return .some(nil) }
    guard let date = parseDate(text) else { return nil }
    return .some(date)
}

if operation == "calendars" {
    ok(store.calendars(for: .event).map {
        ["id": $0.calendarIdentifier, "name": $0.title, "timezone": localZone,
         "writable": $0.allowsContentModifications]
    })
}

if operation == "events" {
    guard let ids = payload["calendar_ids"] as? [String],
          let startText = payload["start"] as? String, let endText = payload["end"] as? String,
          let start = parseDate(startText), let end = parseDate(endText) else { fail("INVALID_PAYLOAD") }
    let calendars = ids.compactMap { store.calendar(withIdentifier: $0) }
    guard calendars.count == ids.count else { fail("CALENDAR_NOT_FOUND") }
    let matched = store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: calendars))
    ok(matched.map(describe))
}

if operation == "event" {
    guard let eventID = payload["event_id"] as? String,
          let requested = occurrenceStart(payload) else { fail("INVALID_PAYLOAD") }
    guard let event = resolveEvent(eventID, requested) else { ok(NSNull()) }
    ok(describe(event))
}

if operation == "create" {
    guard let calendarID = payload["calendar_id"] as? String,
          let title = payload["title"] as? String,
          let startText = payload["start"] as? String, let endText = payload["end"] as? String,
          let start = parseDate(startText), let end = parseDate(endText) else { fail("INVALID_PAYLOAD") }
    guard let target = store.calendar(withIdentifier: calendarID) else { fail("CALENDAR_NOT_FOUND") }
    let event = EKEvent(eventStore: store)
    event.calendar = target
    event.title = title
    // isAllDay reinterprets the dates EventKit already holds, so it is set
    // before them and never after.
    event.isAllDay = (payload["all_day"] as? Bool) ?? false
    event.startDate = start
    if event.isAllDay {
        guard let inclusive = inclusiveEnd(end), inclusive >= start else { fail("INVALID_PAYLOAD") }
        event.endDate = inclusive
    } else {
        event.endDate = end
    }
    do { try store.save(event, span: .thisEvent) } catch { fail("SAVE_FAILED") }
    ok(describe(event))
}

// update and delete resolve the event first, so a missing event and a calendar
// mismatch report their own codes instead of looking like a bad operation.
guard let eventID = payload["event_id"] as? String,
      let calendarID = payload["calendar_id"] as? String,
      let requestedOccurrence = occurrenceStart(payload) else { fail("INVALID_PAYLOAD") }
guard let event = resolveEvent(eventID, requestedOccurrence) else { fail("EVENT_NOT_FOUND") }
guard event.calendar.calendarIdentifier == calendarID else { fail("CALENDAR_MISMATCH") }

let span: EKSpan = (payload["recurrence_scope"] as? String) == "future" ? .futureEvents : .thisEvent

if operation == "delete" {
    let removed = describe(event)
    do { try store.remove(event, span: span) } catch { fail("SAVE_FAILED") }
    ok(removed)
}

if let title = payload["title"] as? String { event.title = title }
// An absent all_day key means "leave the event as it is".
if let allDay = payload["all_day"] as? Bool { event.isAllDay = allDay }
if let text = payload["start"] as? String {
    guard let date = parseDate(text) else { fail("INVALID_PAYLOAD") }
    event.startDate = date
}
if let text = payload["end"] as? String {
    guard let date = parseDate(text) else { fail("INVALID_PAYLOAD") }
    guard let stored = event.isAllDay ? inclusiveEnd(date) : date else { fail("INVALID_PAYLOAD") }
    guard stored >= event.startDate else { fail("INVALID_PAYLOAD") }
    event.endDate = stored
}
do { try store.save(event, span: span) } catch { fail("SAVE_FAILED") }
ok(describe(event))
