import EventKit
import ImageIO
import Foundation
import Launcher
import ReminderKitShim

/// Fail closed: an explicit, nonempty file of exact list names is mandatory.
func loadHubAllowedLists() throws -> Set<String> {
    struct Configuration: Decodable { let names: [String] }
    guard let path = ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_LISTS_FILE"],
          path.hasPrefix("/") else { throw StoreError("An absolute HUB_REMINDERS_ALLOWED_LISTS_FILE is required.") }
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard data.count <= 65536 else { throw StoreError("Allowed lists file is too large.") }
    let names = try JSONDecoder().decode(Configuration.self, from: data).names
    guard !names.isEmpty, names.allSatisfy({ !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }),
          Set(names).count == names.count else { throw StoreError("Allowed lists must contain unique, nonempty exact names.") }
    return Set(names)
}

/// Отсутствие отдельной настройки сохраняет прежний доступ к спискам без групп.
/// Дополнительное UUID-разрешение обязательно только для снятия группы.
func loadHubAllowedGroupIdentities() throws -> [String: String] {
    guard let path = ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE"] else { return [:] }
    guard path.hasPrefix("/") else { throw StoreError("An absolute group identities path is required.") }
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard data.count <= 65536 else { throw StoreError("Group identities file is too large.") }
    // JSONSerialization удаляет повторные ключи; проверяем их до разбора объекта.
    guard let text = String(data: data, encoding: .utf8) else { throw StoreError("Group identities require UTF-8.") }
    let chars = Array(text)
    var index = 0, keys = Set<String>()
    while index < chars.count {
        if chars[index] != "\"" { index += 1; continue }
        let start = index
        index += 1
        var escaped = false
        while index < chars.count {
            let char = chars[index]
            index += 1
            if escaped { escaped = false; continue }
            if char == "\\" { escaped = true; continue }
            if char == "\"" { break }
        }
        var next = index
        while next < chars.count && chars[next].isWhitespace { next += 1 }
        if next < chars.count && chars[next] == ":" {
            let token = String(chars[start..<index])
            let decoded = try JSONSerialization.jsonObject(with: Data("[\(token)]".utf8)) as? [String]
            guard let key = decoded?.first, keys.insert(key).inserted else { throw StoreError("Duplicate group identity keys.") }
        }
    }
    guard let config = try JSONSerialization.jsonObject(with: data) as? [String: Any],
          Set(config.keys) == ["groups"], let groups = config["groups"] as? [String: String], !groups.isEmpty,
          Set(groups.values).count == groups.count else { throw StoreError("Group identities require unique names and exact groups mapping.") }
    var result: [String: String] = [:]
    for (id, name) in groups {
        guard let uuid = UUID(uuidString: id), !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              result[uuid.uuidString] == nil else { throw StoreError("Group identities require unique UUIDs and nonempty names.") }
        result[uuid.uuidString] = name
    }
    return result
}

func loadHubAllowedGroups() throws -> Set<String> {
    guard let path = ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_GROUPS_FILE"] else { return [] }
    guard path.hasPrefix("/") else { throw StoreError("An absolute HUB_REMINDERS_ALLOWED_GROUPS_FILE is required.") }
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    guard data.count <= 65536 else { throw StoreError("Allowed groups file is too large.") }
    guard let config = try JSONSerialization.jsonObject(with: data) as? [String: Any],
          Set(config.keys) == ["names"], let names = config["names"] as? [String],
          !names.isEmpty, names.allSatisfy({ !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }),
          Set(names).count == names.count else { throw StoreError("Allowed groups require unique nonempty exact names.") }
    return Set(names)
}

/// Everything the tools need, on top of RKBridge: the permission check, the write guard,
/// version checks, the rules Reminders enforces in its own UI, and Recently Deleted. Calls into
/// ReminderKit are serialized, because the MCP transport runs requests concurrently and
/// ReminderKit's store is not documented as thread-safe.
final class RemindersStore: @unchecked Sendable {
    /// Снимок разрешённых имён при запуске; отсутствие списка запрещает запись.
    let writeGuard: Set<String>?
    let groupWriteGuard: Set<String>
    let deletionLog: DeletionLog
    private let lock = NSLock()
    private var bridge: RKBridge?

    init(writeGuard: Set<String>?, deletionLog: DeletionLog = DeletionLog()) {
        self.writeGuard = writeGuard ?? []
        self.groupWriteGuard = (try? loadHubAllowedGroups()) ?? []
        self.deletionLog = deletionLog
    }

    // MARK: Permission

    static let permissionHelp = """
        Apple Reminders MCP has no access to Reminders. Ask the user to allow it in System Settings → \
        Privacy & Security → Reminders (turn on "Apple Reminders MCP" with full access), or to open \
        Apple Reminders MCP in Applications once and click Allow.
        """

    static let sandboxHelp = """
        Apple Reminders MCP ran inside a sandbox (Codex runs commands in one), where macOS keeps it from \
        Reminders. Run the same command again outside the sandbox, which the user may have to approve.
        """

    /// Asks for access the first time (the system dialog appears on the Mac) and fails with
    /// instructions when it was refused, or when a sandbox keeps the permission out of reach.
    func ensureAccess() async throws {
        switch EKEventStore.authorizationStatus(for: .reminder) {
        case .fullAccess:
            return
        case _ where launcher_is_sandboxed() != 0:
            throw StoreError(Self.sandboxHelp)
        case .notDetermined:
            let granted = (try? await EKEventStore().requestFullAccessToReminders()) ?? false
            if !granted { throw StoreError(Self.permissionHelp) }
        default:
            throw StoreError(Self.permissionHelp)
        }
    }

    private func withBridge<T>(_ body: (RKBridge) throws -> T) throws -> T {
        lock.lock()
        defer { lock.unlock() }
        if bridge == nil {
            do { bridge = try RKBridge.open() } catch { throw StoreError("ReminderKit is unavailable: \(error.localizedDescription)") }
        }
        do {
            return try body(bridge!)
        } catch let error as StoreError {
            throw error
        } catch {
            throw StoreError(error.localizedDescription)
        }
    }

    // MARK: Reading

    func lists() throws -> [ListInfo] {
        let allowed = try loadHubAllowedLists()
        let selected = try withBridge { try $0.lists().map(ListInfo.init).filter { allowed.contains($0.name) } }
        guard Set(selected.map(\.name)).count == selected.count else { throw StoreError("Duplicate allowed list names; refusing access.") }
        return selected
    }

    func groups() throws -> [GroupInfo] {
        let allowed = try loadHubAllowedGroups()
        if allowed.isEmpty { return [] }
        let selected = try withBridge { try $0.groups().map { GroupInfo(id: $0["id"] as? String ?? "", name: $0["name"] as? String ?? "", accountID: $0["accountId"] as? String) }.filter { allowed.contains($0.name) } }
        guard Set(selected.map(\.name)).count == selected.count else { throw StoreError("Duplicate allowed group names; refusing access.") }
        return selected
    }

    func defaultListID() throws -> String {
        let selected = try lists()
        guard selected.count == 1 else { throw StoreError("Specify an allowed list explicitly.") }
        return selected[0].id
    }

    func reminders(in listID: String) throws -> [ReminderInfo] {
        // Та же проверка разрешённых списков, что в lists(), без чтения разделов и участников
        // каждого списка: иначе перечень из N списков читает метаданные N² раз.
        _ = try loadHubAllowedLists()
        guard try withBridge({ try $0.allowedListIDs() }).contains(listID) else {
            throw StoreError("Reads are limited to explicitly allowed lists.")
        }
        return try withBridge { try $0.reminders(inList: listID).map(ReminderInfo.init) }
    }

    /// A list by id or exact name; a name shared by several lists needs the id.
    func resolveList(_ nameOrID: String) throws -> ListInfo {
        let all = try lists()
        if let list = all.first(where: { $0.id.caseInsensitiveCompare(nameOrID) == .orderedSame }) { return list }
        let named = all.filter { $0.name == nameOrID }
        if named.count == 1 { return named[0] }
        if named.isEmpty {
            throw StoreError("No list named \"\(nameOrID)\". Lists: \(all.map { "\"\($0.name)\"" }.joined(separator: ", ")).")
        }
        throw StoreError("Several lists are named \"\(nameOrID)\"; pass one of these ids: \(named.map(\.id).joined(separator: ", ")).")
    }

    func resolveGroup(_ nameOrID: String) throws -> GroupInfo {
        let all = try groups()
        if let group = all.first(where: { $0.id.caseInsensitiveCompare(nameOrID) == .orderedSame }) { return group }
        let named = all.filter { $0.name == nameOrID }
        if named.count == 1 { return named[0] }
        if named.isEmpty {
            throw StoreError("No group named \"\(nameOrID)\". Groups: \(all.isEmpty ? "none" : all.map { "\"\($0.name)\"" }.joined(separator: ", ")).")
        }
        throw StoreError("Several groups are named \"\(nameOrID)\"; pass one of these ids: \(named.map(\.id).joined(separator: ", ")).")
    }

    func resolveSection(_ nameOrID: String, in list: ListInfo) throws -> SectionInfo {
        if let section = list.sections.first(where: { $0.id.caseInsensitiveCompare(nameOrID) == .orderedSame || $0.name == nameOrID }) {
            return section
        }
        let names = list.sections.map { "\"\($0.name)\"" }.joined(separator: ", ")
        throw StoreError("The list \"\(list.name)\" has no section \"\(nameOrID)\". Sections: \(names.isEmpty ? "none" : names).")
    }

    func reminder(_ id: String) throws -> (ReminderInfo, ListInfo) {
        for list in try lists() {
            if let found = try reminders(in: list.id).first(where: { $0.id.caseInsensitiveCompare(id) == .orderedSame }) {
                return (found, list)
            }
        }
        throw StoreError("No reminder with id \(id). It may have been deleted (see list_deleted); otherwise find it again with find_reminders.")
    }

    // MARK: Checks

    private func checkWritable(_ name: String) throws {
        let allowed = try loadHubAllowedLists()
        if writeGuard?.contains(name) != true || !allowed.contains(name) {
            throw StoreError("Writes are limited to \((writeGuard ?? []).sorted().map { "\"\($0)\"" }.joined(separator: ", ")) (HUB_REMINDERS_ALLOWED_LISTS_FILE).")
        }
    }

    private func checkWritableGroups(_ name: String) throws {
        let allowed = try loadHubAllowedGroups()
        guard groupWriteGuard.contains(name), allowed.contains(name) else {
            throw StoreError("Group writes require separate explicit permission.")
        }
    }

    private func checkWritable(_ list: ListInfo) throws { try checkWritable(list.name) }

    private func checkVersion(_ reminder: ReminderInfo, _ version: String) throws {
        guard reminder.version == version else {
            throw StoreError("\"\(reminder.title)\" changed since it was read (version \(reminder.version), not \(version)). Read it again with get_reminder and retry.")
        }
    }

    /// Reminders allows one level of subtasks within a list.
    private func checkParent(_ parentID: String, child: String?, listID: String) throws -> ReminderInfo {
        let (parent, parentList) = try reminder(parentID)
        if parent.id == child { throw StoreError("A reminder cannot be its own parent.") }
        if parent.parentID != nil { throw StoreError("\"\(parent.title)\" is itself a subtask; Reminders allows one level of subtasks.") }
        if parentList.id != listID { throw StoreError("The parent \"\(parent.title)\" is in the list \"\(parentList.name)\"; a subtask must be in its parent's list.") }
        return parent
    }

    /// Turns the tool-level keys `section` and `repeat` into bridge keys and applies the rules
    /// that involve the reminder's resulting state.
    private func prepare(_ changes: inout [String: Any], list: ListInfo, current: ReminderInfo?) throws {
        if let name = changes.removeValue(forKey: "section") {
            changes["sectionId"] = name is NSNull ? NSNull() : try resolveSection(name as! String, in: list).id
        }
        let newDue: DateComponents? = changes["due"] is NSNull ? nil : (changes["due"] as? NSDateComponents).map { $0 as DateComponents } ?? current?.due
        if let rule = changes["repeat"] as? RepeatRule {
            if newDue == nil { throw StoreError("A repeating reminder needs a due date; pass due as well.") }
            changes["repeat"] = rule.bridgeValue
        } else if changes["due"] is NSNull, current?.repeatRule != nil {
            // Reminders does not keep a rule without a date.
            changes["repeat"] = NSNull()
        }
        // Urgent needs a due time, both when it is turned on and when the due date changes under it.
        let urgent = changes["urgent"] as? Bool ?? current?.urgent ?? false
        if urgent, newDue?.hour == nil {
            if changes["urgent"] as? Bool == true {
                throw StoreError("An urgent reminder needs a due date with a time, e.g. 2026-10-21T09:00.")
            }
            changes["urgent"] = false
        }
        if let alerts = changes["earlyAlerts"] as? [EarlyAlert] {
            if newDue == nil { throw StoreError("Early reminders count back from the due date; pass due as well.") }
            changes["earlyAlerts"] = alerts.map(\.stored)
        }
        if let trigger = changes["location"] as? Trigger { changes["location"] = trigger.bridgeValue }
        if let assignee = changes.removeValue(forKey: "assignee") {
            if assignee is NSNull {
                changes["assigneeId"] = NSNull()
            } else {
                let wanted = assignee as! String
                guard list.shared else { throw StoreError("\"\(list.name)\" is not shared, so its reminders cannot be assigned.") }
                let joined = list.sharees.filter { $0.status == 1 }
                guard let person = joined.first(where: { $0.id.caseInsensitiveCompare(wanted) == .orderedSame })
                    ?? joined.first(where: { $0.name.localizedCaseInsensitiveCompare(wanted) == .orderedSame })
                    ?? (["me", "myself"].contains(wanted.lowercased()) ? joined.first(where: \.me) : nil)
                else {
                    throw StoreError("No one called \"\(wanted)\" has joined \"\(list.name)\". People: \(joined.map { "\"\($0.name)\"\($0.me ? " (me)" : "")" }.joined(separator: ", ")).")
                }
                changes["assigneeId"] = person.id
            }
        }
        if let paths = changes["addImages"] as? [String] {
            changes["addImages"] = try paths.map { path -> [String: Any] in
                let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
                guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                    let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
                    let width = properties[kCGImagePropertyPixelWidth] as? Int, let height = properties[kCGImagePropertyPixelHeight] as? Int
                else { throw StoreError("\(path) is not an image this Mac can read.") }
                return ["path": url.path, "width": width, "height": height]
            }
        }
        if let removing = changes["removeImages"] as? [String], let current {
            if let unknown = removing.first(where: { id in !current.images.contains { $0.id.caseInsensitiveCompare(id) == .orderedSame } }) {
                throw StoreError("\"\(current.title)\" has no image \(unknown); get_reminder lists its images.")
            }
        }
        if let position = changes["position"] as? [String: String], let neighborID = position["after"] ?? position["before"] {
            let (neighbor, neighborList) = try reminder(neighborID)
            let parent = (changes["parentId"] as? String) ?? (changes["parentId"] is NSNull ? nil : current?.parentID)
            if neighborList.id != list.id || neighbor.parentID?.uppercased() != parent?.uppercased() {
                throw StoreError("\"\(neighbor.title)\" is not next to it: a reminder can only be placed among reminders of the same list and level (top level, or subtasks of the same parent).")
            }
            changes["position"] = [position["after"] != nil ? "after" : "before": neighbor.id]
        }
    }

    // MARK: Reminders

    func create(title: String, list nameOrID: String?, changes: [String: Any]) throws -> (ReminderInfo, ListInfo) {
        var changes = changes
        var named = try nameOrID.map(resolveList)
        if let parentID = changes["parentId"] as? String {
            let (parent, parentList) = try reminder(parentID)
            if named == nil { named = parentList }
            _ = try checkParent(parent.id, child: nil, listID: named!.id)
            changes["parentId"] = parent.id
        }
        let list = try named ?? resolveList(defaultListID())
        try checkWritable(list)
        try prepare(&changes, list: list, current: nil)
        let id = try withBridge { try $0.addReminder(toList: list.id, title: title, changes: changes) }
        return try reminder(id)
    }

    /// Returns the updated reminder; for a completed repeating reminder that is the reminder at
    /// its next occurrence, and `completedCopy` says so.
    func update(id: String, version: String, changes: [String: Any]) throws -> (reminder: ReminderInfo, list: ListInfo, completedCopy: Bool) {
        let (current, list) = try reminder(id)
        try checkWritable(list)
        try checkVersion(current, version)
        var changes = changes
        var target = list
        if let destination = changes["listId"] as? String {
            let moved = try resolveList(destination)
            try checkWritable(moved)
            if moved.id == list.id {
                changes.removeValue(forKey: "listId")
            } else {
                if try reminders(in: list.id).contains(where: { $0.parentID == current.id }) {
                    throw StoreError("\"\(current.title)\" has subtasks; move or delete them first, or move them one by one.")
                }
                changes["listId"] = moved.id
                target = moved
            }
        }
        if let parentID = changes["parentId"] as? String {
            _ = try checkParent(parentID, child: current.id, listID: target.id)
            if try reminders(in: list.id).contains(where: { $0.parentID == current.id }) {
                throw StoreError("\"\(current.title)\" has subtasks of its own, so it cannot become a subtask.")
            }
        } else if changes["parentId"] is NSNull, current.parentID == nil {
            changes.removeValue(forKey: "parentId")
        }
        var completedCopy = false
        if changes["completed"] as? Bool == true, current.recurring, !current.completed {
            guard Settings.allowCompletingRecurring else {
                throw StoreError("\"\(current.title)\" repeats, and the user turned off completing repeating reminders in Apple Reminders MCP's settings. Ask the user to check it off in Reminders.")
            }
            changes["completeRecurring"] = true
            completedCopy = true
        }
        try prepare(&changes, list: target, current: current)
        try withBridge { try $0.updateReminder(current.id, changes: changes) }
        let (updated, updatedList) = try reminder(current.id)
        return (updated, updatedList, completedCopy)
    }

    /// Deletes a reminder and its subtasks; returns their titles.
    func delete(id: String, version: String) throws -> [String] {
        let (current, list) = try reminder(id)
        try checkWritable(list)
        try checkVersion(current, version)
        let subtasks = try reminders(in: list.id).filter { $0.parentID == current.id }
        return try softDelete(subtasks + [current], from: list)
    }

    private func softDelete(_ targets: [ReminderInfo], from list: ListInfo) throws -> [String] {
        guard !targets.isEmpty else { return [] }
        let now = Date()
        deletionLog.record(targets.map {
            DeletionLog.Entry(id: $0.id, title: $0.title, listID: list.id, listName: list.name, parentID: $0.parentID, deletedAt: now)
        })
        try withBridge { try $0.deleteReminders(targets.map(\.id)) }
        return targets.map(\.title)
    }

    struct DeletedItem: Sendable {
        let id: String
        let title: String
        let deletedAt: Date?
        let fromList: String?
        let parentID: String?
        let completed: Bool
    }

    /// Restorable reminders in Recently Deleted: everything when the app can read Reminders'
    /// database, otherwise what this server deleted. `complete` says which.
    func deleted() throws -> (items: [DeletedItem], complete: Bool) {
        let logged = deletionLog.entries()
        let database = DeletedDatabase.recentlyDeleted()
        var candidates: [String: (title: String, deletedAt: Date?, parentID: String?)] = [:]
        for row in database ?? [] { candidates[row.id] = (row.title, row.deletedAt, row.parentID) }
        for entry in logged { candidates[entry.id] = (entry.title, entry.deletedAt, entry.parentID) }
        let alive = try withBridge { try $0.deletedReminders(Array(candidates.keys)) }
        // Restored or purged since: drop them from the log.
        let gone = Set(logged.map(\.id)).subtracting(alive.keys)
        if !gone.isEmpty { deletionLog.forget(gone) }
        let byID = Dictionary(logged.map { ($0.id, $0) }, uniquingKeysWith: { _, last in last })
        let items = alive.map { id, info -> DeletedItem in
            let known = candidates[id]
            return DeletedItem(
                id: id, title: info["title"] as? String ?? known?.title ?? "", deletedAt: known?.deletedAt,
                fromList: byID[id]?.listName, parentID: known?.parentID ?? info["parentId"] as? String,
                completed: info["completed"] as? Bool ?? false)
        }
        return (items.sorted { ($0.deletedAt ?? .distantPast) > ($1.deletedAt ?? .distantPast) }, database != nil)
    }

    /// Restores a deleted reminder, with the subtasks deleted along with it, into `list` or the
    /// list it was deleted from (the default list when neither is known or the old one is gone).
    func restore(id: String, list nameOrID: String?) throws -> (restored: [ReminderInfo], list: ListInfo) {
        let (items, _) = try deleted()
        guard let item = items.first(where: { $0.id.caseInsensitiveCompare(id) == .orderedSame }) else {
            throw StoreError("No restorable reminder with id \(id) in Recently Deleted. list_deleted shows what can be restored.")
        }
        let logged = deletionLog.entries().first { $0.id == item.id }
        let target: ListInfo
        if let nameOrID {
            target = try resolveList(nameOrID)
        } else if let logged, let original = try lists().first(where: { $0.id == logged.listID }) {
            target = original
        } else {
            target = try resolveList(defaultListID())
        }
        try checkWritable(target)
        let subtasks = items.filter { $0.parentID == item.id }
        let ids = [item.id] + subtasks.map(\.id)
        try withBridge { try $0.restoreReminders(ids, toList: target.id) }
        deletionLog.forget(Set(ids))
        // Put subtasks back under their parent if the restore left them at the top level.
        for subtask in subtasks {
            if let (restored, _) = try? reminder(subtask.id), restored.parentID == nil {
                try withBridge { try $0.updateReminder(subtask.id, changes: ["parentId": item.id]) }
            }
        }
        return (ids.compactMap { try? reminder($0).0 }, target)
    }

    // MARK: Lists

    /// Перенос допускает только UUID отдельно разрешённой группы.
    private func listChanges(_ changes: [String: Any]) throws -> [String: Any] {
        guard changes.count == 1, Set(changes.keys).isSubset(of: ["group", "groupId"]),
              let groupID = (changes["group"] ?? changes["groupId"]) as? String,
              UUID(uuidString: groupID) != nil else { throw StoreError("Only an explicit group UUID is permitted.") }
        let group = try resolveGroup(groupID)
        try checkWritableGroups(group.name)
        return ["groupId": group.id]
    }

    func createList(_ name: String, changes: [String: Any]) throws -> ListInfo {
        try checkWritable(name)
        if try lists().contains(where: { $0.name == name }) { throw StoreError("A list named \"\(name)\" already exists.") }
        guard changes.isEmpty || (Set(changes.keys) == ["expectedAccountId"] && (changes["expectedAccountId"] as? String).flatMap(UUID.init(uuidString:)) != nil) else { throw StoreError("List creation accepts only an expected account UUID.") }
        let id = try withBridge { try $0.createList(named: name, changes: changes) }
        let created = try resolveList(id)
        if let expected = changes["expectedAccountId"] as? String {
            guard created.accountID.flatMap(UUID.init(uuidString:)) == UUID(uuidString: expected) else { throw StoreError("Created list account readback mismatch.") }
        }
        return created
    }

    /// Разрешён только перенос разрешённого списка по UUID в разрешённую группу.
    func updateList(_ nameOrID: String, changes: [String: Any]) throws -> ListInfo {
        if changes["name"] != nil || changes["expectedName"] != nil || changes["expectedAccountId"] != nil { return try renameList(nameOrID, changes: changes) }
        guard UUID(uuidString: nameOrID) != nil else { throw StoreError("An explicit list UUID is required.") }
        var changes = changes
        let hasExpected = changes.keys.contains("expectedGroupId")
        let expected = changes.removeValue(forKey: "expectedGroupId")
        if hasExpected, !(expected is NSNull), (expected as? String).flatMap(UUID.init(uuidString:)) == nil {
            throw StoreError("Expected source group must be an explicit UUID or null.")
        }
        func checkExpected(_ current: ListInfo, permissions: Bool = true) throws {
            guard hasExpected else { return }
            let matches = expected is NSNull ? current.groupID == nil : current.groupID?.uppercased() == (expected as? String)?.uppercased()
            guard matches else { throw StoreError("Expected source group changed before write.") }
            if let sourceID = current.groupID, permissions {
                let identities = try loadHubAllowedGroupIdentities()
                guard let name = identities[sourceID.uppercased()] else { throw StoreError("Expected source group UUID is not explicitly permitted.") }
                try checkWritableGroups(name)
                let source = try resolveGroup(sourceID)
                guard source.name == name, let account = current.accountID, source.accountID == account else {
                    throw StoreError("Expected source group identity or account changed.")
                }
                try checkWritableGroups(source.name)
            }
        }
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        if changes.count == 1, changes["group"] is NSNull {
            guard let sourceID = list.groupID, UUID(uuidString: sourceID) != nil else {
                throw StoreError("Ungroup requires an existing allowed source group.")
            }
            let identities = try loadHubAllowedGroupIdentities()
            guard let expectedName = identities[sourceID.uppercased()] else { throw StoreError("Ungroup requires an explicitly known source UUID.") }
            try checkWritableGroups(expectedName)
            let source = try resolveGroup(sourceID)
            guard source.name == expectedName else { throw StoreError("Ungroup source identity changed.") }
            try checkWritableGroups(source.name)
            guard let account = list.accountID, UUID(uuidString: account) != nil,
                  source.accountID == account else { throw StoreError("Ungroup requires the same identifiable account.") }
            let current = try resolveList(list.id)
            try checkWritable(current)
            let currentGroup = try resolveGroup(source.id)
            try checkWritableGroups(currentGroup.name)
            guard current.id == list.id, current.groupID == source.id, current.accountID == account,
                  currentGroup.id == source.id, currentGroup.accountID == account else {
                throw StoreError("Ungroup source changed before write.")
            }
            try checkExpected(current)
            let beforeWrite = try resolveList(list.id)
            try checkWritable(beforeWrite)
            try checkExpected(beforeWrite, permissions: false)
            guard beforeWrite.groupID == source.id, beforeWrite.accountID == account else { throw StoreError("Ungroup source changed before mutation.") }
            var prepared: [String: Any] = ["groupId": NSNull()]
            if hasExpected { prepared["expectedGroupId"] = expected }
            try withBridge { try $0.updateList(list.id, changes: prepared) }
            let updated = try resolveList(list.id)
            try checkWritable(updated)
            guard updated.id == list.id, updated.groupID == nil, updated.accountID == account else {
                throw StoreError("Ungroup readback did not confirm the same list and account in the root.")
            }
            return updated
        }
        var prepared = try listChanges(changes)
        if hasExpected {
            let current = try resolveList(list.id)
            try checkWritable(current)
            let destination = try resolveGroup(prepared["groupId"] as! String)
            try checkWritableGroups(destination.name)
            guard let account = current.accountID, UUID(uuidString: account) != nil, destination.accountID == account else {
                throw StoreError("Guarded move requires the same identifiable account.")
            }
            try checkExpected(current)
            let finalSource = try resolveList(list.id)
            try checkWritable(finalSource)
            try checkExpected(finalSource, permissions: false)
            guard finalSource.accountID == account else { throw StoreError("Guarded move account changed before mutation.") }
            prepared["expectedGroupId"] = expected
        }
        try withBridge { try $0.updateList(list.id, changes: prepared) }
        return try resolveList(list.id)
    }

    /// Переименование сохраняет все свойства контейнера, кроме его имени.
    private func renameList(_ id: String, changes: [String: Any]) throws -> ListInfo {
        guard Set(changes.keys) == ["name", "expectedName", "expectedAccountId", "expectedGroupId"],
              UUID(uuidString: id) != nil,
              let oldName = changes["expectedName"] as? String, let newName = changes["name"] as? String, oldName != newName,
              [oldName, newName].allSatisfy({ !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && $0.rangeOfCharacter(from: .newlines) == nil }),
              let account = changes["expectedAccountId"] as? String, UUID(uuidString: account) != nil,
              changes["expectedGroupId"] is NSNull || (changes["expectedGroupId"] as? String).flatMap(UUID.init(uuidString:)) != nil
        else { throw StoreError("Invalid guarded rename fields.") }
        try checkWritable(oldName); try checkWritable(newName)
        let list = try resolveList(id)
        let groupMatches = changes["expectedGroupId"] is NSNull ? list.groupID == nil : list.groupID.flatMap(UUID.init(uuidString:)) == (changes["expectedGroupId"] as? String).flatMap(UUID.init(uuidString:))
        guard UUID(uuidString: list.id) == UUID(uuidString: id), list.name == oldName,
              list.accountID.flatMap(UUID.init(uuidString:)) == UUID(uuidString: account), groupMatches else { throw StoreError("Rename source identity changed.") }
        if try lists().contains(where: { $0.name == newName }) { throw StoreError("Rename destination name already exists.") }
        try withBridge { try $0.updateList(id, changes: changes) }
        let updated = try resolveList(id)
        var expected = Output.list(list, groups: [])
        if case .object(var object) = expected { object["name"] = .string(newName); expected = .object(object) }
        guard Output.list(updated, groups: []) == expected else { throw StoreError("Rename readback changed unexpected list fields.") }
        return updated
    }

    /// Deletes a list. One that still has reminders needs `withReminders`; they go to Recently
    /// Deleted first, so list_deleted and restore_reminder can bring them back to another list.
    func deleteList(_ nameOrID: String, withReminders: Bool) throws -> (list: ListInfo, deleted: Int) {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        if try defaultListID() == list.id { throw StoreError("\"\(list.name)\" is the default list and cannot be deleted.") }
        let reminders = try self.reminders(in: list.id)
        if !reminders.isEmpty && !withReminders {
            throw StoreError("\"\(list.name)\" still has \(reminders.count) reminders (including completed ones). Confirm with the user, then pass confirm_delete_reminders: true; they go to Recently Deleted.")
        }
        _ = try softDelete(reminders, from: list)
        try withBridge { try $0.deleteList(list.id) }
        return (list, reminders.count)
    }

    // MARK: Groups

    func createGroup(_ name: String) throws -> GroupInfo {
        try checkWritableGroups(name)
        if try groups().contains(where: { $0.name == name }) { throw StoreError("A group named \"\(name)\" already exists.") }
        let id = try withBridge { try $0.createGroup(named: name) }
        return try resolveGroup(id)
    }

    func renameGroup(_ nameOrID: String, to name: String) throws -> GroupInfo {
        throw StoreError("Group renaming is disabled.")
    }

    func deleteGroup(_ nameOrID: String) throws -> GroupInfo {
        throw StoreError("Group deletion is disabled.")
    }

    // MARK: Smart lists

    func smartLists() throws -> [SmartListInfo] {
        return []
    }

    func resolveSmartList(_ nameOrID: String) throws -> SmartListInfo {
        let all = try smartLists()
        if let found = all.first(where: { $0.id.caseInsensitiveCompare(nameOrID) == .orderedSame }) { return found }
        let named = all.filter { $0.name == nameOrID }
        if named.count == 1 { return named[0] }
        if named.isEmpty {
            throw StoreError("No smart list named \"\(nameOrID)\". Smart lists: \(all.isEmpty ? "none" : all.map { "\"\($0.name)\"" }.joined(separator: ", ")).")
        }
        throw StoreError("Several smart lists are named \"\(nameOrID)\"; pass one of these ids: \(named.map(\.id).joined(separator: ", ")).")
    }

    /// Smart list id → the ids of the reminders it shows, as Reminders computes them.
    func smartListContents(includingCompleted: Bool) throws -> [String: Set<String>] {
        return [:]
    }

    /// `changes`: filter (stored JSON), color (bridge dictionary), icon.
    func createSmartList(_ name: String, changes: [String: Any]) throws -> SmartListInfo {
        try checkWritable(name)
        if try smartLists().contains(where: { $0.name == name }) { throw StoreError("A smart list named \"\(name)\" already exists.") }
        let id = try withBridge { try $0.createSmartList(named: name, changes: changes) }
        return try resolveSmartList(id)
    }

    /// `changes`: name, filter, color, icon.
    func updateSmartList(_ nameOrID: String, changes: [String: Any]) throws -> SmartListInfo {
        let smartList = try resolveSmartList(nameOrID)
        try checkWritable(smartList.name)
        if let name = changes["name"] as? String, name != smartList.name {
            try checkWritable(name)
            if try smartLists().contains(where: { $0.name == name }) { throw StoreError("A smart list named \"\(name)\" already exists.") }
        }
        try withBridge { try $0.updateSmartList(smartList.id, changes: changes) }
        return try resolveSmartList(smartList.id)
    }

    /// A smart list only shows reminders, so deleting it deletes none.
    func deleteSmartList(_ nameOrID: String) throws -> SmartListInfo {
        let smartList = try resolveSmartList(nameOrID)
        try checkWritable(smartList.name)
        try withBridge { try $0.deleteSmartList(smartList.id) }
        return smartList
    }

    // MARK: Sections

    func createSection(_ name: String, in nameOrID: String) throws -> (SectionInfo, ListInfo) {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        if list.sections.contains(where: { $0.name == name }) { throw StoreError("\"\(list.name)\" already has a section \"\(name)\".") }
        let id = try withBridge { try $0.createSection(named: name, inList: list.id) }
        let updated = try resolveList(list.id)
        return (try resolveSection(id, in: updated), updated)
    }

    func renameSection(_ section: String, in nameOrID: String, to name: String) throws -> (SectionInfo, ListInfo) {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        let found = try resolveSection(section, in: list)
        try withBridge { try $0.renameSection(found.id, inList: list.id, to: name) }
        let updated = try resolveList(list.id)
        return (try resolveSection(found.id, in: updated), updated)
    }

    /// Deleting a section keeps its reminders; they stay in the list without a section.
    func deleteSection(_ section: String, in nameOrID: String) throws -> (SectionInfo, ListInfo) {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        let found = try resolveSection(section, in: list)
        try withBridge { try $0.deleteSection(found.id, inList: list.id) }
        return (found, list)
    }
}

// MARK: - Detail, images, tags, templates, ordering

extension RemindersStore {
    /// One reminder with its early reminders, which the list fetch leaves out.
    func detail(_ id: String) throws -> (ReminderInfo, ListInfo) {
        let (_, list) = try reminder(id)
        let raw = try withBridge { try $0.reminderDetail(id) }
        return (ReminderInfo(raw), list)
    }

    /// Полные строки в уже снятом ограниченном списке, без поиска каждого UUID во всех списках.
    func details(_ before: [ReminderInfo], in source: ListInfo) throws -> [ReminderInfo] {
        let current = try resolveList(source.id)
        guard Output.list(current, groups: []) == Output.list(source, groups: []),
              Set(before.map(\.id)).count == before.count,
              before.allSatisfy({ UUID(uuidString: $0.id) != nil && $0.listID == source.id && !$0.version.isEmpty }) else { throw StoreError("snapshot_changed") }
        return try withBridge { bridge in
            try before.map { row in
                let reminder = ReminderInfo(try bridge.reminderDetail(row.id))
                guard reminder.id == row.id, reminder.listID == source.id,
                      !reminder.version.isEmpty, reminder.version == row.version,
                      Output.reminder(reminder, in: current) == Output.reminder(row, in: source) else { throw StoreError("snapshot_changed") }
                return reminder
            }
        }
    }

    /// The bytes of an image attachment. Reminders keeps them in its own container, so this needs
    /// Full Disk Access for the app.
    func imageData(reminder id: String, image imageID: String) throws -> (Data, ImageInfo) {
        let (reminder, _) = try reminder(id)
        guard let image = reminder.images.first(where: { $0.id.caseInsensitiveCompare(imageID) == .orderedSame }) else {
            throw StoreError("\"\(reminder.title)\" has no image \(imageID); get_reminder lists its images.")
        }
        guard let path = image.path, let data = FileManager.default.contents(atPath: path) else {
            throw StoreError("Reading images needs Full Disk Access for Apple Reminders MCP (System Settings → Privacy & Security → Full Disk Access); Reminders keeps them in its own folder.")
        }
        return (data, image)
    }

    /// Every tag in use, with how many open and how many reminders in all have it.
    func tags() throws -> [(name: String, open: Int, total: Int)] {
        var counts: [String: (name: String, open: Int, total: Int)] = [:]
        for list in try lists() {
            for reminder in try reminders(in: list.id) {
                for tag in reminder.tags {
                    var entry = counts[tag.lowercased()] ?? (tag, 0, 0)
                    entry.total += 1
                    if !reminder.completed { entry.open += 1 }
                    counts[tag.lowercased()] = entry
                }
            }
        }
        return counts.values.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    /// Renames a tag everywhere, or with nil removes it; returns how many reminders changed.
    func replaceTag(_ tag: String, with replacement: String?) throws -> Int {
        if let writeGuard {
            for list in try lists() where !writeGuard.contains(list.name) {
                if try reminders(in: list.id).contains(where: { $0.tags.contains { $0.caseInsensitiveCompare(tag) == .orderedSame } }) {
                    throw StoreError("Reminders outside \(writeGuard.sorted().map { "\"\($0)\"" }.joined(separator: ", ")) have this tag (HUB_REMINDERS_ALLOWED_LISTS_FILE).")
                }
            }
        }
        return try withBridge { try $0.replaceTag(tag, with: replacement).intValue }
    }

    func templates() throws -> [TemplateInfo] {
        return []
    }

    func resolveTemplate(_ nameOrID: String) throws -> TemplateInfo {
        let all = try templates()
        if let found = all.first(where: { $0.id.caseInsensitiveCompare(nameOrID) == .orderedSame }) { return found }
        let named = all.filter { $0.name == nameOrID }
        if named.count == 1 { return named[0] }
        if named.isEmpty {
            throw StoreError("No template named \"\(nameOrID)\". Templates: \(all.isEmpty ? "none" : all.map { "\"\($0.name)\"" }.joined(separator: ", ")).")
        }
        throw StoreError("Several templates are named \"\(nameOrID)\"; pass one of these ids: \(named.map(\.id).joined(separator: ", ")).")
    }

    /// Reminders copies the list into the template in the background, so it can take a moment
    /// to show its reminders.
    func createTemplate(_ name: String, from nameOrID: String, includeCompleted: Bool) throws -> TemplateInfo {
        let list = try resolveList(nameOrID)
        try checkWritable(name)
        let id = try withBridge { try $0.createTemplate(named: name, fromList: list.id, includeCompleted: includeCompleted) }
        return (try? resolveTemplate(id)) ?? TemplateInfo(id: id, name: name)
    }

    func createList(fromTemplate nameOrID: String, name: String?) throws -> ListInfo {
        let template = try resolveTemplate(nameOrID)
        try checkWritable(name ?? template.name)
        let id = try withBridge { try $0.createList(fromTemplate: template.id, name: name) }
        return try resolveList(id)
    }

    func deleteTemplate(_ nameOrID: String) throws -> TemplateInfo {
        let template = try resolveTemplate(nameOrID)
        try checkWritable(template.name)
        try withBridge { try $0.deleteTemplate(template.id) }
        return template
    }

    func moveSection(_ section: String, in nameOrID: String, relativeTo other: String, after: Bool) throws -> ListInfo {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        let moving = try resolveSection(section, in: list)
        let anchor = try resolveSection(other, in: list)
        if moving.id == anchor.id { throw StoreError("A section cannot move next to itself.") }
        try withBridge { try $0.moveSection(moving.id, inList: list.id, relativeTo: anchor.id, after: after) }
        return try resolveList(list.id)
    }

    /// Moves a list's completed reminders to Recently Deleted; returns how many.
    func clearCompleted(in nameOrID: String) throws -> (list: ListInfo, count: Int) {
        let list = try resolveList(nameOrID)
        try checkWritable(list)
        let done = try reminders(in: list.id).filter(\.completed)
        _ = try softDelete(done, from: list)
        return (list, done.count)
    }
}

// MARK: - Ограниченная синтетическая диагностика
extension RemindersStore: HubDiagnosticBackend {
    func cancellationOutput(_ raw:[String:Any], list:ListInfo) throws -> [String:Any] {
        let text = Output.reminder(ReminderInfo(raw),in:list,detail:true).text
        guard let result = try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any] else { throw StoreError("Diagnostic output rejected.") }
        return result
    }
    private func diagnosticList() throws -> ListInfo {
        try checkWritable(HubDiagnosticPlan.listName)
        let matches = try withBridge { try $0.lists().filter{($0["id"] as? String) == HubDiagnosticPlan.listID} }
        guard matches.count == 1, matches[0]["name"] as? String == HubDiagnosticPlan.listName else { throw StoreError("Diagnostic list identity changed.") }
        return ListInfo(matches[0])
    }
    func diagnosticSnapshot(_ id:String) throws -> [String:Any] {
        let list = try diagnosticList()
        let raw = try withBridge { try $0.reminderDetail(id) }
        guard raw["id"] as? String == id, raw["listId"] as? String == list.id else { throw StoreError("Diagnostic reminder identity changed.") }
        return try cancellationOutput(raw,list:list)
    }
    func diagnosticDeleted(_ ids:[String]) throws -> [String:[String:Any]] {
        let list = try diagnosticList()
        let raw = try withBridge { try $0.diagnosticDeletedReminders(ids) }
        var result:[String:[String:Any]] = [:]
        for (id,row) in raw { result[id] = try cancellationOutput(row,list:list) }
        return result
    }
    func diagnosticChildren(_ id:String,listID:String) throws -> Set<String> {
        let list = try diagnosticList()
        guard listID == list.id else { throw StoreError("Diagnostic list mismatch.") }
        return try withBridge { Set(try $0.reminders(inList:list.id).filter{($0["parentId"] as? String) == id}.compactMap{$0["id"] as? String}) }
    }
    func diagnosticDelete(_ id:String) throws {
        _ = try diagnosticSnapshot(id)
        try withBridge { try $0.deleteReminders([id]) }
    }
    func diagnosticRestore(_ id:String,listID:String,parentID:String?) throws {
        let list = try diagnosticList()
        guard listID == list.id else { throw StoreError("Diagnostic restore list mismatch.") }
        let deleted = try diagnosticDeleted([id])
        guard deleted[id] != nil else { throw StoreError("Diagnostic UUID is not restorable.") }
        if let parentID {
            let parent = try diagnosticSnapshot(parentID)
            guard parent["completed"] as? Bool != true, parent["parent_id"] == nil else { throw StoreError("Diagnostic parent is not open.") }
        }
        try withBridge { try $0.restoreReminders([id],toList:list.id) }
        let restored = try diagnosticSnapshot(id)
        if restored["parent_id"] as? String != parentID {
            guard restored["parent_id"] == nil, let parentID else { throw StoreError("Unexpected diagnostic restore parent.") }
            try withBridge { try $0.updateReminder(id,changes:["parentId":parentID]) }
        }
    }
    func diagnosticRace(_ id:String,notes:String) throws -> [String:Any] {
        _ = try diagnosticSnapshot(id)
        return try withBridge { bridge in
            let raw = try bridge.reminderDetail(id)
            return try bridge.diagnosticRaceDelete(id,expected:raw,notes:notes)
        }
    }
}

// Exact-UUID operations for the separate cancellation identity. No global Recently Deleted scan.
extension RemindersStore {
    func cancellationList(id: String, name: String) throws -> ListInfo {
        try checkWritable(name)
        let matches = try withBridge { try $0.lists().filter { ($0["id"] as? String) == id || ($0["name"] as? String) == name } }
        guard matches.count == 1 else { throw StoreError("Cancellation list identity changed.") }
        let list = ListInfo(matches[0])
        guard HubCancellationChecks.listAllowed(id: list.id, name: list.name,
                                               expectedID: id, expectedName: name, shared: list.shared) else { throw StoreError("Cancellation list identity changed or shared.") }
        return list
    }
    func cancellationActive(_ id: String, list: ListInfo, requireRoot: Bool = false) throws -> [String: Any]? {
        let rows = try withBridge { try $0.reminders(inList: list.id).filter { ($0["id"] as? String) == id } }
        guard rows.count <= 1 else { throw StoreError("Duplicate reminder UUID.") }
        guard rows.first != nil else { return nil }
        let raw = try withBridge { try $0.reminderDetail(id) }
        guard raw["id"] as? String == id, raw["listId"] as? String == list.id else { throw StoreError("Cancellation reminder moved.") }
        if requireRoot && raw["parentId"] != nil { throw StoreError("Root reminder has a parent field.") }
        var output = try cancellationOutput(raw, list: list)
        // Match get_reminder's full parent shape; this also preserves checks on other children.
        let children = try withBridge { try $0.reminders(inList: list.id).filter { ($0["parentId"] as? String) == id }.map(ReminderInfo.init) }
        if !children.isEmpty {
            output["subtasks"] = children.map { child -> [String: Any] in
                var row: [String: Any] = ["id": child.id, "title": child.title]
                if child.completed { row["completed"] = true }
                return row
            }
        }
        return output
    }
    func cancellationDeleted(_ id: String, list: ListInfo, parentID: String?) throws -> [String: Any]? {
        let found = try withBridge { try $0.diagnosticDeletedReminders([id]) }
        guard Set(found.keys).isSubset(of: [id]) else { throw StoreError("Unexpected deleted UUID.") }
        guard let raw = found[id] else { return nil }
        // ReminderKit clears list/parent on soft deletion. A foreign remaining binding is a conflict.
        guard (raw["listId"] as? String ?? "").isEmpty,
              (raw["parentId"] as? String ?? "").isEmpty || raw["parentId"] as? String == parentID else { throw StoreError("Deleted reminder has a new binding.") }
        if parentID == nil && raw["parentId"] != nil { throw StoreError("Deleted root has a residual parent.") }
        var output = try cancellationOutput(raw, list: list)
        output["list_id"] = list.id
        output["list"] = list.name
        if let parentID { output["parent_id"] = parentID } else { output.removeValue(forKey: "parent_id") }
        return output
    }
    func cancellationChildren(_ id: String, list: ListInfo) throws -> Set<String> {
        try withBridge { Set(try $0.reminders(inList: list.id).filter { ($0["parentId"] as? String) == id }.compactMap { $0["id"] as? String }) }
    }
    func cancellationDelete(_ id: String) throws { try withBridge { try $0.deleteReminders([id]) } }
    func cancellationRestore(_ id: String, list: ListInfo, parentID: String?) throws {
        try withBridge { try $0.restoreReminders([id], toList: list.id) }
        let restored = try cancellationActive(id, list: list, requireRoot: parentID == nil)
        guard let restored else { throw StoreError("Restore readback missing.") }
        guard let parentID else {
            guard restored["parent_id"] == nil, try cancellationChildren(id, list: list).isEmpty else { throw StoreError("Restored root hierarchy changed.") }
            return
        }
        if let currentParent = restored["parent_id"] as? String {
            guard currentParent == parentID else { throw StoreError("Restore parent conflict.") }
        } else {
            try withBridge { try $0.updateReminder(id, changes: ["parentId": parentID]) }
        }
    }
}
