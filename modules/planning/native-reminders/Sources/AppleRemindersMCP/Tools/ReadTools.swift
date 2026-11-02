import Foundation
import Wire

/// Runs a tool after the permission check; problems with the reminders themselves become
/// failed answers the model can read and act on.
func withStore(_ store: RemindersStore, _ body: () async throws -> ToolAnswer) async throws -> ToolAnswer {
    do {
        try await store.ensureAccess()
        return try await body()
    } catch let error as StoreError {
        return ToolAnswer(error.description, failed: true)
    }
}

/// Общий формат get и полного find; порядок дочерних строк сохраняется.
func reminderSubtasks(_ reminders: [ReminderInfo], parent: String) -> JSON? {
    let children = reminders.filter { $0.parentID == parent }
    guard !children.isEmpty else { return nil }
    return .array(children.map { child in
        var row: [String: JSON] = ["id": .string(child.id), "title": .string(child.title)]
        if child.completed { row["completed"] = true }
        return .object(row)
    })
}

/// Индекс детей строится один раз; порядок внутри каждого родителя сохраняется.
func reminderSubtaskSnapshots(_ reminders: [ReminderInfo]) -> [String: JSON] {
    let children = Dictionary(grouping: reminders.filter { $0.parentID != nil }, by: { $0.parentID! })
    return children.compactMapValues { rows in reminderSubtasks(rows, parent: rows[0].parentID!) }
}

/// Единое полное представление для get и подробного снимка списка.
func reminderDetailObject(_ reminder: ReminderInfo, in list: ListInfo, subtasks: JSON?) throws -> [String: JSON] {
    guard case .object(var object) = Output.reminder(reminder, in: list, detail: true) else { throw StoreError("invalid_detail_snapshot") }
    object["subtasks"] = subtasks
    return object
}

func readReminderDetailSnapshot(_ store: RemindersStore, id: String, expected: (ReminderInfo, ListInfo)? = nil) throws -> [String: JSON] {
    let (reminder, list) = try store.detail(id)
    if let (before, source) = expected {
        guard reminder.id == before.id, reminder.listID == source.id, list.id == source.id,
              !reminder.version.isEmpty, reminder.version == before.version,
              Output.reminder(reminder, in: list) == Output.reminder(before, in: source) else { throw StoreError("snapshot_changed") }
    }
    return try reminderDetailObject(reminder, in: list, subtasks: reminderSubtasks(try store.reminders(in: list.id), parent: reminder.id))
}

func detailedReminderSnapshot(_ store: RemindersStore, listID: String) throws -> ToolAnswer {
    let list = try store.resolveList(listID)
    guard list.id == listID else { throw StoreError("snapshot_list_mismatch") }
    let before = try store.reminders(in: list.id)
    guard Set(before.map(\.id)).count == before.count,
          before.allSatisfy({ UUID(uuidString: $0.id) != nil && $0.listID == list.id && !$0.version.isEmpty }) else { throw StoreError("invalid_reminder_snapshot") }
    let ordered = before.sorted { a, b in
        if a.completed != b.completed { return !a.completed }
        if a.completed { return (a.completionDate ?? .distantPast) > (b.completionDate ?? .distantPast) }
        let da = a.due.flatMap(Due.instant) ?? .distantFuture, db = b.due.flatMap(Due.instant) ?? .distantFuture
        return da != db ? da < db : a.title < b.title
    }
    let shown = ordered.prefix(500)
    let children = reminderSubtaskSnapshots(before)
    let details = try store.details(Array(shown), in: list).map {
        try reminderDetailObject($0, in: list, subtasks: children[$0.id])
    }
    let after = try store.reminders(in: list.id)
    let current = try store.resolveList(list.id)
    guard Output.list(current, groups: []) == Output.list(list, groups: []),
          after.map({ Output.reminder($0, in: current) }) == before.map({ Output.reminder($0, in: list) }) else { throw StoreError("snapshot_changed") }
    let currentChildren = reminderSubtaskSnapshots(after)
    for row in details {
        guard let id = row["id"]?.string, row["subtasks"] == currentChildren[id] else { throw StoreError("snapshot_children_changed") }
    }
    var result: [String: JSON] = ["now": .string(Due.now()), "time_zone": .string(TimeZone.current.identifier),
        "detail": true, "count": .int(details.count), "reminders": .array(details.map(JSON.object))]
    if before.count > details.count { result["more"] = .int(before.count - details.count) }
    return ToolAnswer(JSON.object(result).text)
}

func readTools(_ store: RemindersStore) -> [Tool] {
    [
        Tool("list_lists", title: "List reminder lists",
             summary: """
                 Lists the Reminders lists (counts, group, color, icon, sections, sort order, type, and the \
                 people on shared lists), the groups, the smart lists with their filters, and the templates.
                 """,
             input: Schema.object([:]), effect: .reads) { _ in
            try await withStore(store) {
                let groups = try store.groups()
                let lists = try store.lists()
                // Metadata never needs a global default; create still requires an explicit list.
                let defaultID = lists.count == 1 ? lists[0].id : nil
                var result: [String: JSON] = [
                    "guarded_list_creation": .bool(true),
                    "guarded_list_rename": .bool(true),
                    "detailed_reminder_snapshot": .bool(true),
                    "lists": .array(try lists.map { list in
                        let reminders = try store.reminders(in: list.id)
                        return Output.list(list, groups: groups, counts: (reminders.filter { !$0.completed }.count, reminders.count), isDefault: list.id == defaultID)
                    }),
                ]
                if !groups.isEmpty {
                    result["groups"] = .array(groups.map { group in
                        ["id": .string(group.id), "name": .string(group.name), "account_id": group.accountID.map(JSON.string) ?? .null, "lists": .array(lists.filter { $0.groupID == group.id }.map { .string($0.name) })]
                    })
                }
                let smartLists = try store.smartLists()
                if !smartLists.isEmpty { result["smart_lists"] = .array(smartLists.map { Output.smartList($0, lists: lists) }) }
                let templates = try store.templates()
                if !templates.isEmpty { result["templates"] = .array(templates.map { ["id": .string($0.id), "name": .string($0.name)] }) }
                return ToolAnswer(JSON.object(result).text)
            }
        },

        Tool("find_reminders", title: "Find reminders",
             summary: """
                 Finds reminders across lists, open ones first by due date. Filters combine. due_before is \
                 exclusive: due_before tomorrow gives everything due today or overdue. Each reminder appears \
                 once, with smart_lists naming the smart lists that show it.
                 """,
             input: Schema.object([
                 "list": Schema.text("List name or id; default all lists"),
                 "smart_list": Schema.text("Only what this smart list shows (name or id), as Reminders computes it"),
                 "section": Schema.text("Only this section"),
                 "query": Schema.text("Text in the title or notes"),
                 "include_completed": Schema.flag("Default false"),
                 "flagged": Schema.flag("Only flagged"),
                 "urgent": Schema.flag("Only urgent"),
                 "repeating": Schema.flag("Only repeating"),
                 "has_location": Schema.flag("Only reminders with a place or car alert"),
                 "assigned_to": Schema.text("Only reminders assigned to this person (name, or me)"),
                 "tag": Schema.text("Only this tag (without #)"),
                 "due_before": Schema.text("2026-10-21 or 2026-10-21T09:00, exclusive"),
                 "due_after": Schema.text("2026-10-21 or 2026-10-21T09:00, inclusive"),
                 "limit": Schema.whole("Default 100, at most 500"),
                 "detail": Schema.flag("Exact full snapshot: explicit list UUID, include_completed true, limit 500 only"),
             ]), effect: .reads) { fields in
            let input = Input(fields)
            if let value = fields["detail"], value.bool == nil { throw BadInput("detail must be boolean") }
            let detail = try input.flag("detail") ?? false
            if detail {
                guard Set(fields.keys) == ["list", "include_completed", "limit", "detail"],
                      let id = try input.text("list"), UUID(uuidString: id) != nil,
                      fields["include_completed"] == .bool(true), fields["limit"] == .int(500) else { throw BadInput("detail requires exact list UUID, include_completed true and limit 500 without filters") }
                return try await withStore(store) { try detailedReminderSnapshot(store, listID: id) }
            }
            let listName = try input.text("list"), smartListName = try input.text("smart_list")
            let section = try input.text("section"), query = try input.text("query")
            let includeCompleted = try input.flag("include_completed") ?? false
            let flagged = try input.flag("flagged") ?? false, urgent = try input.flag("urgent") ?? false
            let repeating = try input.flag("repeating") ?? false, located = try input.flag("has_location") ?? false
            let assignedTo = try input.text("assigned_to")
            let tag = try input.text("tag").map { $0.hasPrefix("#") ? String($0.dropFirst()) : $0 }
            let before = try input.due("due_before").flatMap(Due.instant), after = try input.due("due_after").flatMap(Due.instant)
            let limit = try input.number("limit", 1...500) ?? 100
            return try await withStore(store) {
                let lists = try listName.map { [try store.resolveList($0)] } ?? store.lists()
                let smartLists = try store.smartLists()
                let onlySmartList = try smartListName.map(store.resolveSmartList)
                // Smart list id → what it shows. Without a smart_list filter, a failed fetch only
                // costs the smart_lists field.
                var shownBy: [String: Set<String>] = [:]
                var note: String?
                if !smartLists.isEmpty {
                    do {
                        shownBy = try store.smartListContents(includingCompleted: includeCompleted)
                    } catch let error as StoreError where onlySmartList == nil {
                        note = "Which smart lists show each reminder is unavailable: \(error.description)"
                    }
                }
                let onlyIDs = onlySmartList.map { shownBy[$0.id] ?? [] }
                var matches: [(ReminderInfo, ListInfo)] = []
                for list in lists {
                    let sectionIDs = section.map { name in Set(list.sections.filter { $0.name == name || $0.id == name }.map(\.id)) }
                    if let sectionIDs, sectionIDs.isEmpty { continue }
                    let assignee = assignedTo.map { wanted in
                        list.sharees.first { $0.name.localizedCaseInsensitiveCompare(wanted) == .orderedSame || $0.id.caseInsensitiveCompare(wanted) == .orderedSame
                            || (wanted.lowercased() == "me" && $0.me) }?.id ?? "-"
                    }
                    for r in try store.reminders(in: list.id) {
                        if r.completed && !includeCompleted { continue }
                        if let onlyIDs, !onlyIDs.contains(r.id) { continue }
                        if flagged && !r.flagged { continue }
                        if urgent && !r.urgent { continue }
                        if repeating && r.repeatRule == nil { continue }
                        if located && r.trigger == nil { continue }
                        if let assignee, r.assigneeID?.caseInsensitiveCompare(assignee) != .orderedSame { continue }
                        if let sectionIDs, !(r.sectionID.map(sectionIDs.contains) ?? false) { continue }
                        if let tag, !r.tags.contains(where: { $0.caseInsensitiveCompare(tag) == .orderedSame }) { continue }
                        if let query, !(r.title.localizedCaseInsensitiveContains(query) || (r.notes?.localizedCaseInsensitiveContains(query) ?? false)) { continue }
                        let due = r.due.flatMap(Due.instant)
                        if let before, !(due.map { $0 < before } ?? false) { continue }
                        if let after, !(due.map { $0 >= after } ?? false) { continue }
                        matches.append((r, list))
                    }
                }
                matches.sort { a, b in
                    if a.0.completed != b.0.completed { return !a.0.completed }
                    if a.0.completed { return (a.0.completionDate ?? .distantPast) > (b.0.completionDate ?? .distantPast) }
                    let da = a.0.due.flatMap(Due.instant) ?? .distantFuture, db = b.0.due.flatMap(Due.instant) ?? .distantFuture
                    return da != db ? da < db : a.0.title < b.0.title
                }
                let shown = matches.prefix(limit)
                var result: [String: JSON] = [
                    "now": .string(Due.now()), "time_zone": .string(TimeZone.current.identifier),
                    "count": .int(shown.count),
                    "reminders": .array(shown.map { r, list in
                        Output.reminder(r, in: list, smartLists: smartLists.filter { shownBy[$0.id]?.contains(r.id) ?? false }.map(\.name))
                    }),
                ]
                if matches.count > shown.count { result["more"] = .int(matches.count - shown.count) }
                if let note { result["note"] = .string(note) }
                return ToolAnswer(JSON.object(result).text)
            }
        },

        Tool("get_reminder", title: "Read a reminder",
             summary: "Reads one reminder in full: alarms, early alerts, images, subtasks, and its current version.",
             input: Schema.object(["id": Schema.text("Reminder id")], required: ["id"]), effect: .reads) { fields in
            let id = try Input(fields).requiredText("id")
            return try await withStore(store) {
                return ToolAnswer(JSON.object(try readReminderDetailSnapshot(store, id: id)).text)
            }
        },

        Tool("read_image", title: "Look at an image on a reminder",
             summary: "Returns an image attached to a reminder (ids from get_reminder). Needs Full Disk Access for the app.",
             input: Schema.object(["reminder_id": Schema.text("Reminder id"), "image_id": Schema.text("Image id")], required: ["reminder_id", "image_id"]),
             effect: .reads) { fields in
            let input = Input(fields)
            let reminderID = try input.requiredText("reminder_id"), imageID = try input.requiredText("image_id")
            return try await withStore(store) {
                let (data, image) = try store.imageData(reminder: reminderID, image: imageID)
                let mime = image.type.contains("png") ? "image/png" : image.type.contains("heic") ? "image/heic" : image.type.contains("gif") ? "image/gif" : "image/jpeg"
                return ToolAnswer(content: [.text("\(image.width)×\(image.height), \(data.count) bytes"), .image(data, mimeType: mime)])
            }
        },

        Tool("list_tags", title: "List tags",
             summary: "Lists every tag in use, with how many open and how many reminders in all have it.",
             input: Schema.object([:]), effect: .reads) { _ in
            try await withStore(store) {
                ToolAnswer(JSON.array(try store.tags().map { ["tag": .string($0.name), "open": .int($0.open), "total": .int($0.total)] }).text)
            }
        },

        Tool("list_deleted", title: "List recently deleted reminders",
             summary: "Lists reminders in Recently Deleted that restore_reminder can bring back, newest first.",
             input: Schema.object([:]), effect: .reads) { _ in
            try await withStore(store) {
                let (items, complete) = try store.deleted()
                var result: [String: JSON] = [
                    "deleted": .array(items.map { item in
                        var row: [String: JSON] = ["id": .string(item.id), "title": .string(item.title)]
                        if let at = item.deletedAt { row["deleted_at"] = .string(Output.stamp.string(from: at)) }
                        if let list = item.fromList { row["from_list"] = .string(list) }
                        if let parent = item.parentID { row["parent_id"] = .string(parent) }
                        if item.completed { row["completed"] = true }
                        return .object(row)
                    }),
                ]
                if !complete {
                    result["note"] = "Only reminders deleted through this server are listed. With Full Disk Access for Apple Reminders MCP, this lists everything in Recently Deleted."
                }
                return ToolAnswer(JSON.object(result).text)
            }
        },
    ]
}
