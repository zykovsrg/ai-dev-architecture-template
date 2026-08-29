import EventKit
import Foundation

func printJSON(_ value: Any) {
    guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) else { exit(1) }
    print(String(data: data, encoding: .utf8)!)
}

let operation = CommandLine.arguments.dropFirst().first ?? ""
let store = EKEventStore()
if operation == "status" {
    let status = EKEventStore.authorizationStatus(for: .event)
    let value: String
    switch status {
    case .fullAccess: value = "granted"
    case .notDetermined: value = "not_determined"
    default: value = "denied"
    }
    printJSON(["permission": value])
    exit(0)
}
let input = FileHandle.standardInput.readDataToEndOfFile()
let payload = (try? JSONSerialization.jsonObject(with: input) as? [String: Any]) ?? [:]
let semaphore = DispatchSemaphore(value: 0)
var allowed = false
store.requestFullAccessToEvents { granted, _ in allowed = granted; semaphore.signal() }
semaphore.wait()
guard allowed else { printJSON(["error": "calendar_access_denied"]); exit(1) }
let iso = ISO8601DateFormatter()
func calendar(_ id: String) -> EKCalendar? { store.calendar(withIdentifier: id) }
if operation == "calendars" {
    let zone = TimeZone.current.identifier
    printJSON(store.calendars(for: .event).map { ["id": $0.calendarIdentifier, "name": $0.title, "timezone": zone, "writable": $0.allowsContentModifications] })
    exit(0)
}
if operation == "events",
   let ids = payload["calendar_ids"] as? [String],
   let startText = payload["start"] as? String, let endText = payload["end"] as? String,
   let start = iso.date(from: startText), let end = iso.date(from: endText) {
    let calendars = ids.compactMap(calendar)
    guard calendars.count == ids.count else { printJSON(["error": "calendar_not_found"]); exit(1) }
    let events = store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: calendars))
    let zone = TimeZone.current.identifier
    printJSON(events.map { ["id": $0.calendarItemIdentifier, "calendar_id": $0.calendar.calendarIdentifier, "title": $0.title ?? "", "start": iso.string(from: $0.startDate), "end": iso.string(from: $0.endDate), "timezone": $0.timeZone?.identifier ?? zone] })
    exit(0)
}
if operation == "event", let eventID = payload["event_id"] as? String {
    guard let event = store.calendarItem(withIdentifier: eventID) as? EKEvent else { printJSON(NSNull()); exit(0) }
    printJSON(["id": event.calendarItemIdentifier, "calendar_id": event.calendar.calendarIdentifier, "title": event.title ?? "", "start": iso.string(from: event.startDate), "end": iso.string(from: event.endDate), "timezone": event.timeZone?.identifier ?? TimeZone.current.identifier])
    exit(0)
}
if operation == "create",
   let calendarID = payload["calendar_id"] as? String, let target = calendar(calendarID),
   let title = payload["title"] as? String, let startText = payload["start"] as? String,
   let endText = payload["end"] as? String, let start = iso.date(from: startText), let end = iso.date(from: endText) {
    let event = EKEvent(eventStore: store)
    event.calendar = target; event.title = title; event.startDate = start; event.endDate = end
    do { try store.save(event, span: .thisEvent); printJSON(["id": event.calendarItemIdentifier, "calendar_id": calendarID, "title": title, "start": iso.string(from: start), "end": iso.string(from: end), "timezone": event.timeZone?.identifier ?? TimeZone.current.identifier]) }
    catch { printJSON(["error": "save_failed"]); exit(1) }
    exit(0)
}
if (operation == "update" || operation == "delete"), let eventID = payload["event_id"] as? String,
   let event = store.calendarItem(withIdentifier: eventID) as? EKEvent,
   let calendarID = payload["calendar_id"] as? String, event.calendar.calendarIdentifier == calendarID {
    let span: EKSpan = payload["recurrence_scope"] as? String == "future" ? .futureEvents : .thisEvent
    do {
        if operation == "delete" { try store.remove(event, span: span) }
        else {
            if let title = payload["title"] as? String { event.title = title }
            if let text = payload["start"] as? String, let date = iso.date(from: text) { event.startDate = date }
            if let text = payload["end"] as? String, let date = iso.date(from: text) { event.endDate = date }
            try store.save(event, span: span)
        }
        printJSON(["ok": true]); exit(0)
    } catch { printJSON(["error": "save_failed"]); exit(1) }
}
printJSON(["error": "unsupported_operation"])
exit(1)
