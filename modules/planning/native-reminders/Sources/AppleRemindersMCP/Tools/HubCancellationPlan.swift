import Foundation
import CryptoKit
import Darwin

struct HubCancellationError: Error, CustomStringConvertible {
    let description: String
    init(_ code: String) { description = code }
}

enum HubCancellationChecks {
    static func listAllowed(id: String, name: String, expectedID: String, expectedName: String, shared: Bool) -> Bool {
        id == expectedID && name == expectedName && !shared
    }
    static func status(active: [String: Any]?, deleted: [String: Any]?, id: String,
                       listID: String, listName: String, parentID: String?) throws -> [String: Any] {
        guard (active == nil) != (deleted == nil) else { throw HubCancellationError("reminder_not_found_or_ambiguous") }
        let snapshot = active ?? deleted!
        guard snapshot["id"] as? String == id, snapshot["list_id"] as? String == listID,
              snapshot["list"] as? String == listName, (parentID != nil ? snapshot["parent_id"] as? String == parentID : snapshot["parent_id"] == nil),
              let version = snapshot["version"] as? String, !version.isEmpty else { throw HubCancellationError("reminder_binding_changed") }
        var result: [String: Any] = ["state": active == nil ? "deleted" : "active", "version": version, "snapshot": snapshot]
        if active == nil { result["projected_binding"] = true }
        return result
    }
    static func sameFields(_ actual: [String: Any], _ expected: [String: Any], version: Bool = true) -> Bool {
        var a = actual, e = expected
        a.removeValue(forKey: "subtasks"); e.removeValue(forKey: "subtasks")
        if !version { a.removeValue(forKey: "version"); e.removeValue(forKey: "version") }
        return HubCancellationScope.equal(a, e)
    }
    static func sameParent(_ actual: [String: Any], _ expected: [String: Any], target: String) -> Bool {
        func clean(_ value: [String: Any]) -> [String: Any] {
            var copy = value
            if let children = copy["subtasks"] as? [[String: Any]] {
                let others = children.filter { $0["id"] as? String != target }
                if others.isEmpty { copy.removeValue(forKey: "subtasks") } else { copy["subtasks"] = others }
            }
            return copy
        }
        return HubCancellationScope.equal(clean(actual), clean(expected))
    }
    static func deleteReady(_ status: [String: Any], version: String, remote: [String: Any],
                            parent: [String: Any]?, expectedParent: [String: Any], target: String, children: Set<String>) -> Bool {
        status["state"] as? String == "active" && status["version"] as? String == version &&
        (status["snapshot"] as? [String: Any]).map { sameFields($0, remote) } == true &&
        parent.map { $0["completed"] as? Bool != true && $0["parent_id"] == nil && sameParent($0, expectedParent, target: target) } == true && children.isEmpty
    }
    static func restoreReady(_ status: [String: Any], version: String, tokenRemote: [String: Any],
                             parent: [String: Any]?, expectedParent: [String: Any], target: String) -> Bool {
        status["state"] as? String == "deleted" && status["version"] as? String == version &&
        HubCancellationScope.equal(status, tokenRemote) &&
        parent.map { $0["completed"] as? Bool != true && $0["parent_id"] == nil && sameParent($0, expectedParent, target: target) } == true
    }
}

struct HubCancellationScope {
    static let approvedHubRoot = "/Users/zykovsrg/Documents/vibecode/_ai-hub"
    static func restoreVerified(on build: String) -> Bool { build == "25G83" }
    let hub: URL
    let plan: [String: Any]
    let item: [String: Any]
    let state: [String: Any]
    let progress: [String: Any]
    let config: [String: Any]
    let binding: [String: Any]
    let listID: String
    let listName: String
    let parentID: String?
    let id: String
    let sha: String
    let path: URL

    static func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    static func uuid(_ text: String?) -> Bool { text.flatMap(UUID.init(uuidString:)) != nil }
    static func safe(_ path: String) throws -> URL {
        guard path.hasPrefix("/"), !path.split(separator: "/", omittingEmptySubsequences: false).contains("..") else { throw HubCancellationError("unsafe_path") }
        let url = URL(fileURLWithPath: path)
        guard url.standardizedFileURL.path == path, url.resolvingSymlinksInPath().path == path else { throw HubCancellationError("unsafe_path") }
        return url
    }
    static func bytes(_ url: URL) throws -> Data {
        _ = try safe(url.path)
        let size = (try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.intValue ?? Int.max
        guard size <= 2_097_152 else { throw HubCancellationError("file_too_large") }
        let data = try Data(contentsOf: url)
        guard data.count <= 2_097_152 else { throw HubCancellationError("file_too_large") }
        return data
    }
    static func object(_ data: Data) throws -> [String: Any] {
        guard let result = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw HubCancellationError("invalid_json_object") }
        return result
    }
    static func equal(_ a: Any?, _ b: Any?) -> Bool {
        guard let a, let b else { return a == nil && b == nil }
        return (a as? NSObject)?.isEqual(b) ?? false
    }
    static func load(path: String, sha: String, id: String, mutation: Bool,
                     approvedRoot: String = approvedHubRoot) throws -> Self {
        let url = try safe(path)
        guard url.lastPathComponent == "plan.json", uuid(url.deletingLastPathComponent().lastPathComponent), uuid(id),
              sha.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil else { throw HubCancellationError("invalid_plan_reference") }
        let hub = url.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        guard hub.path == approvedRoot, try safe(approvedRoot).path == approvedRoot else { throw HubCancellationError("untrusted_hub_root") }
        guard url.deletingLastPathComponent().deletingLastPathComponent().path == hub.appendingPathComponent("ai/reminders-cancellations").path else { throw HubCancellationError("plan_outside_hub") }
        let raw = try bytes(url)
        guard hash(raw) == sha else { throw HubCancellationError("plan_checksum_mismatch") }
        let plan = try object(raw)
        if plan["version"] as? Int == 2 { return try loadV2(hub: hub, url: url, plan: plan, sha: sha, id: id, mutation: mutation) }
        guard plan["version"] as? Int == 1, plan["operation_id"] as? String == url.deletingLastPathComponent().lastPathComponent,
              let items = plan["items"] as? [[String: Any]], !items.isEmpty,
              let item = items.first(where: { $0["reminder_id"] as? String == id }),
              items.filter({ $0["reminder_id"] as? String == id }).count == 1 else { throw HubCancellationError("invalid_plan_item") }
        if mutation { guard plan["concurrency_policy"] as? String == "no_concurrent_edits" else { throw HubCancellationError("strict_plan_requires_atomicity") } }
        let state = try object(bytes(try safe(url.deletingLastPathComponent().appendingPathComponent("state.json").path)))
        guard state["plan_sha256"] as? String == sha, let approved = state["approved"] as? Bool,
              let progresses = state["items"] as? [String: [String: Any]], Set(progresses.keys) == Set(items.compactMap { $0["reminder_id"] as? String }),
              let progress = progresses[id], let phase = progress["phase"] as? String,
              ["prepared", "deleting", "remote_deleted", "hub_cancelled", "committed", "restoring", "restored"].contains(phase),
              !mutation || approved else { throw HubCancellationError("invalid_or_unapproved_state") }
        let configURL = try safe(hub.appendingPathComponent("ai/reminders-sync.json").path)
        let config = try object(bytes(configURL))
        guard let configPath = config["allowlist_file"] as? String,
              try safe(configPath).path == hub.appendingPathComponent("ai/reminders-allowlist.json").path,
              (ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_LISTS_FILE"] == configPath ||
               ((config["projects"] as? [String: [String: Any]])?[item["project_id"] as? String ?? ""]?["historical_binding_migration"] != nil &&
                ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_LISTS_FILE"] == hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path)) else { throw HubCancellationError("allowlist_path_changed") }
        var scopedConfig = config
        var effectiveItem = item
        if let pid = item["project_id"] as? String, var projects = config["projects"] as? [String: [String: Any]],
           var binding = projects[pid], binding["historical_binding_migration"] != nil {
            let historical = try historicalReceipt(hub: hub, config: config, plan: plan, item: item, state: state, sha: sha)
            guard let before = historical["before"] as? [String: Any], let after = historical["after"] as? [String: Any],
                  let parent = (after["retired_parent"] as? [String: Any])?["snapshot"] as? [String: Any] else { throw HubCancellationError("historical_parent_missing") }
            for key in ["layout","list_id","list_name","parent_id","account_id","native_group_id","retired_parent"] { binding.removeValue(forKey:key) }
            for (key,value) in before { binding[key] = value }
            projects[pid] = binding; scopedConfig["projects"] = projects; effectiveItem["parent"] = parent
        }
        let allowData = try bytes(try safe(configPath))
        let allow = try object(allowData)
        guard plan["allowlist_sha256"] as? String == hash(allowData), let names = allow["names"] as? [String],
              let pid = item["project_id"] as? String, let tid = item["task_id"] as? String,
              let projects = scopedConfig["projects"] as? [String: [String: Any]], let binding = projects[pid],
              let tasks = binding["tasks"] as? [String: [String: Any]], let task = tasks[tid],
              task["reminder_id"] as? String == id,
              let listID = binding["list_id"] as? String, uuid(listID),
              let listName = binding["list_name"] as? String, names.contains(listName),
              let parentID = binding["parent_id"] as? String, uuid(parentID),
              item["list_id"] as? String == listID, item["list_name"] as? String == listName,
              item["parent_id"] as? String == parentID,
              let projectPath = item["project_path"] as? String,
              try safe(projectPath).path == hub.appendingPathComponent("projects/\(pid)").path,
              pid.range(of: "^[a-z0-9-]+$", options: .regularExpression) != nil,
              let originalLink = item["link"] as? [String: Any],
              let source = item["source_path"] as? String, source.hasPrefix(projectPath + "/ai/"),
              let remote = item["remote"] as? [String: Any], remote["id"] as? String == id,
              remote["list_id"] as? String == listID, remote["list"] as? String == listName,
              remote["parent_id"] as? String == parentID, !(remote["version"] as? String ?? "").isEmpty,
              let parent = item["parent"] as? [String: Any], parent["id"] as? String == parentID,
              parent["list_id"] as? String == listID, parent["list"] as? String == listName,
              !(parent["version"] as? String ?? "").isEmpty,
              item["before_texts"] is [String: String], item["after_texts"] is [String: String] else { throw HubCancellationError("binding_or_snapshot_changed") }
        let receipt = ["operation_id": plan["operation_id"]!, "plan_sha256": sha, "reminder_id": id] as [String: Any]
        var cancelled = originalLink; cancelled["cancellation"] = receipt
        guard equal(task, originalLink) || equal(task, cancelled) else { throw HubCancellationError("task_binding_changed") }
        for row in items {
            guard let project = row["project_id"] as? String, let taskID = row["task_id"] as? String,
                  let reminder = row["reminder_id"] as? String, uuid(reminder),
                  let original = row["link"] as? [String: Any],
                  let liveProject = projects[project], let liveTasks = liveProject["tasks"] as? [String: [String: Any]],
                  let live = liveTasks[taskID] else { throw HubCancellationError("plan_task_binding_changed") }
            var own = original
            own["cancellation"] = ["operation_id": plan["operation_id"]!, "plan_sha256": sha, "reminder_id": reminder] as [String: Any]
            guard equal(live, original) || equal(live, own) else { throw HubCancellationError("foreign_cancellation_receipt") }
        }
        let registry = try String(contentsOf: try safe(hub.appendingPathComponent("ai/project-registry.md").path), encoding: .utf8)
        guard let start = registry.range(of: "(?m)^## \(NSRegularExpression.escapedPattern(for: pid))\\n", options: .regularExpression) else { throw HubCancellationError("project_not_registered") }
        let rest = registry[start.upperBound...]
        let block = String(rest[..<(rest.range(of: "(?m)^## ", options: .regularExpression)?.lowerBound ?? rest.endIndex)])
        let lines = block.split(separator: "\n").map(String.init)
        guard lines.filter({ $0 == "Status: active" }).count == 1,
              lines.filter({ $0.hasPrefix("Path: ") }) == ["Path: \(projectPath)"] else { throw HubCancellationError("project_not_active") }
        return Self(hub: hub, plan: plan, item: effectiveItem, state: state, progress: progress, config: config, binding: binding, listID: listID, listName: listName, parentID: parentID, id: id, sha: sha, path: url)
    }
    func restoreToken(path tokenPath: String, sha token: String) throws -> [String: Any] {
        let url = try Self.safe(tokenPath)
        guard token.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              url.path == path.deletingLastPathComponent().appendingPathComponent("restore-\(token).json").path else { throw HubCancellationError("invalid_restore_token_path") }
        let data = try Self.bytes(url)
        guard Self.hash(data) == token else { throw HubCancellationError("restore_checksum_mismatch") }
        let value = try Self.object(data)
        if isHistorical {
            guard value["version"] as? Int == 3, value["purpose"] as? String == "historical_composite_restore",
                  state["restore_token"] as? String == token,
                  let runtime = value["runtime"] as? [String: Any], try Self.runtimeMatches(runtime),
                  value["standard_allowlist_sha256"] as? String == Self.hash(try Self.bytes(Self.safe(hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path))),
                  let rows = value["items"] as? [String: [String: Any]], let row = rows[id], Self.equal(row["parent"],item["parent"]),
                  let pid = item["project_id"] as? String, let binding = (config["projects"] as? [String: [String: Any]])?[pid],
                  Self.equal(row["destination"],Self.structural(binding)), Self.equal(row["historical_binding_migration"],binding["historical_binding_migration"]),
                  (progress["relocation"] as? [String: Any])?["phase"] as? String == "remote_restore_old_pending",
                  Self.equal(row["remote"],progress["deleted_snapshot"]) else { throw HubCancellationError("historical_restore_token_changed") }
        }
        if isVerification {
            guard value["version"] as? Int == 2, value["purpose"] as? String == "project_list_verification",
                  value["plan_sha256"] as? String == sha, Self.equal(value["operation_id"], plan["operation_id"]),
                  Self.equal(value["config"], config), Self.equal(value["allowlist_sha256"], plan["allowlist_sha256"]),
                  value["config_sha256"] as? String == Self.hash(try Self.bytes(Self.safe(hub.appendingPathComponent("ai/reminders-sync.json").path))),
                  let rows = value["items"] as? [String: [String: Any]], Set(rows.keys) == [id], let row = rows[id], Set(row.keys) == ["remote"],
                  Self.equal(row["remote"], progress["deleted_snapshot"]) else { throw HubCancellationError("verification_restore_token_changed") }
            return row
        }
        guard value["plan_sha256"] as? String == sha, Self.equal(value["operation_id"], plan["operation_id"]),
              let rows = value["items"] as? [String: [String: Any]], let row = rows[id],
              row["remote"] is [String: Any], row["before_texts"] is [String: String], row["after_texts"] is [String: String],
              Self.equal(value["allowlist_sha256"], plan["allowlist_sha256"]),
              let tokenConfig = value["config"] as? [String: Any],
              Self.equal(Self.normalizedReceipts(tokenConfig, items: plan["items"] as? [[String: Any]] ?? []),
                         Self.normalizedReceipts(config, items: plan["items"] as? [[String: Any]] ?? [])) else { throw HubCancellationError("restore_token_changed") }
        guard let tokenProjects = tokenConfig["projects"] as? [String: [String: Any]],
              let plannedItems = plan["items"] as? [[String: Any]] else { throw HubCancellationError("restore_token_bindings_changed") }
        for item in plannedItems {
            guard let pid = item["project_id"] as? String, let tid = item["task_id"] as? String,
                  let rid = item["reminder_id"] as? String, let original = item["link"] as? [String: Any],
                  let tasks = tokenProjects[pid]?["tasks"] as? [String: [String: Any]], let link = tasks[tid] else { throw HubCancellationError("restore_token_bindings_changed") }
            var own = original
            own["cancellation"] = ["operation_id": plan["operation_id"]!, "plan_sha256": sha, "reminder_id": rid] as [String: Any]
            guard Self.equal(link, original) || Self.equal(link, own) else { throw HubCancellationError("restore_token_foreign_receipt") }
        }
        return row
    }
    static func normalizedReceipts(_ value: [String: Any], items: [[String: Any]]) -> [String: Any] {
        var copy = value
        guard var projects = copy["projects"] as? [String: [String: Any]] else { return copy }
        for item in items {
            guard let pid = item["project_id"] as? String, let tid = item["task_id"] as? String,
                  let link = item["link"] as? [String: Any], var project = projects[pid],
                  var tasks = project["tasks"] as? [String: [String: Any]], tasks[tid] != nil else { continue }
            tasks[tid] = link; project["tasks"] = tasks; projects[pid] = project
        }
        copy["projects"] = projects
        return copy
    }
}

extension HubCancellationScope {
    var isRoot: Bool { plan["version"] as? Int == 2 }
    var isVerification: Bool { plan["purpose"] as? String == "project_list_verification" }
    static func registered(_ hub: URL, pid: String, projectPath: String) throws {
        guard pid.range(of: "^[a-z0-9-]+$", options: .regularExpression) != nil,
              try safe(projectPath).path == hub.appendingPathComponent("projects/\(pid)").path else { throw HubCancellationError("project_path_changed") }
        let registry = String(decoding: try bytes(safe(hub.appendingPathComponent("ai/project-registry.md").path)), as: UTF8.self)
        guard let start = registry.range(of: "(?m)^## \(NSRegularExpression.escapedPattern(for: pid))\\n", options: .regularExpression) else { throw HubCancellationError("project_not_registered") }
        let rest = registry[start.upperBound...]
        let block = String(rest[..<(rest.range(of: "(?m)^## ", options: .regularExpression)?.lowerBound ?? rest.endIndex)])
        let lines = block.split(separator: "\n").map(String.init)
        guard lines.filter({ $0 == "Status: active" }).count == 1,
              lines.filter({ $0.hasPrefix("Path: ") }) == ["Path: \(projectPath)"] else { throw HubCancellationError("project_not_active") }
    }
    static func migrationPending(_ hub: URL, config: [String: Any], pid: String) throws -> Bool {
        if (config["project_list_migrations_pending"] as? [String: Any])?[pid] != nil { return true }
        let root = try safe(hub.appendingPathComponent("ai/reminders-project-lists").path)
        guard FileManager.default.fileExists(atPath: root.path) else { return false }
        for folder in try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) {
            let raw = try bytes(safe(folder.appendingPathComponent("plan.json").path)), plan = try object(raw)
            if plan["kind"] as? String != "migration" || plan["project"] as? String != pid { continue }
            let state = try object(bytes(safe(folder.appendingPathComponent("state.json").path)))
            if state["phase"] as? String != "preview" && (config["project_list_migrations_completed"] as? [String: String])?[pid] != hash(raw) { return true }
        }
        return false
    }
    // Только чтение завершённой отмены допускает доказанные расширения разрешений.
    static func approvedPermissionChain(hub: URL, from: String, to: String) throws -> Bool {
        let original = try bytes(safe(hub.appendingPathComponent("ai/reminders-allowlist.json").path))
        let root = try safe(hub.appendingPathComponent("ai/reminders-project-lists").path)
        guard FileManager.default.fileExists(atPath: root.path) else { return false }
        var edges: [String: Set<String>] = [:]
        for folder in try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) {
            do {
                let raw = try bytes(safe(folder.appendingPathComponent("plan.json").path))
                let receipt = try object(raw)
                guard receipt["kind"] as? String == "permission", receipt["hub"] as? String == hub.path,
                      let operation = receipt["operation"] as? String, uuid(operation), folder.lastPathComponent == operation else { continue }
                let state = try object(bytes(safe(folder.appendingPathComponent("state.json").path)))
                guard equal(state["approved"], true), state["phase"] as? String == "complete", state["sha256"] as? String == hash(raw),
                      let permission = receipt["permission"] as? [String: Any], let originalText = permission["original"] as? String,
                      Data(originalText.utf8) == original, let before = permission["before"] as? String, let after = permission["after"] as? String,
                      let name = receipt["list_name"] as? String, !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { continue }
                let old = try object(Data(before.utf8)), new = try object(Data(after.utf8))
                guard Set(old.keys) == ["names"], Set(new.keys) == ["names"],
                      let oldNames = old["names"] as? [String], let newNames = new["names"] as? [String],
                      (oldNames + newNames).allSatisfy({ !$0.isEmpty }), Set(oldNames).count == oldNames.count, Set(newNames).count == newNames.count else { continue }
                let added = oldNames.contains(name) ? [] : [name]
                guard newNames == oldNames + added, permission["added"] as? [String] == added else { continue }
                edges[hash(Data(before.utf8)), default: []].insert(hash(Data(after.utf8)))
            } catch { continue }
        }
        var pending = [from], seen: Set<String> = []
        while let value = pending.popLast() {
            if value == to { return true }
            if seen.insert(value).inserted { pending.append(contentsOf: edges[value] ?? []) }
        }
        return false
    }
    static func loadV2(hub: URL, url: URL, plan: [String: Any], sha: String, id: String, mutation: Bool) throws -> Self {
        guard plan["operation_id"] as? String == url.deletingLastPathComponent().lastPathComponent,
              let items = plan["items"] as? [[String: Any]], !items.isEmpty,
              Set(items.compactMap { $0["reminder_id"] as? String }).count == items.count,
              Set(items.compactMap { $0["project_id"] as? String }).count == items.count,
              let item = items.first(where: { $0["reminder_id"] as? String == id }),
              ["strict", "no_concurrent_edits"].contains(plan["concurrency_policy"] as? String ?? ""),
              !mutation || plan["concurrency_policy"] as? String == "no_concurrent_edits" else { throw HubCancellationError("invalid_v2_plan") }
        let purpose = plan["purpose"] as? String ?? ""
        guard ["task_cancellation", "project_list_verification"].contains(purpose) else { throw HubCancellationError("invalid_purpose") }
        let state = try object(bytes(safe(url.deletingLastPathComponent().appendingPathComponent("state.json").path)))
        guard state["plan_sha256"] as? String == sha, let approved = state["approved"] as? Bool,
              let progresses = state["items"] as? [String: [String: Any]], Set(progresses.keys) == Set(items.compactMap { $0["reminder_id"] as? String }),
              let progress = progresses[id], !mutation || approved else { throw HubCancellationError("invalid_or_unapproved_state") }
        let config = try object(bytes(safe(hub.appendingPathComponent("ai/reminders-sync.json").path)))
        if purpose == "project_list_verification" {
            return try loadVerification(hub: hub, url: url, plan: plan, sha: sha, id: id, mutation: mutation, state: state, config: config)
        }
        guard let plannedConfig = plan["config"] as? [String: Any],
              let projects = config["projects"] as? [String: [String: Any]],
              let plannedProjects = plannedConfig["projects"] as? [String: [String: Any]],
              let allowPath = config["standard_allowlist_file"] as? String,
              allowPath == hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path,
              ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_LISTS_FILE"] == allowPath,
              equal(config["cancellation_policy"], plannedConfig["cancellation_policy"]) else { throw HubCancellationError("v2_scope_config_changed") }
        let allowRaw = try bytes(safe(allowPath)), allow = try object(allowRaw)
        let terminal = progresses.values.allSatisfy { ["committed", "restored"].contains($0["phase"] as? String ?? "") }
        let exactPermission = hash(allowRaw) == plan["allowlist_sha256"] as? String
        let historicalPermission = try !exactPermission && !mutation && approved && terminal && (approvedPermissionChain(hub: hub, from: plan["allowlist_sha256"] as? String ?? "", to: hash(allowRaw)))
        guard exactPermission || historicalPermission, let names = allow["names"] as? [String] else { throw HubCancellationError("allowlist_checksum_mismatch") }
        for row in items {
            guard let pid = row["project_id"] as? String, let tid = row["task_id"] as? String,
                  let rid = row["reminder_id"] as? String, uuid(rid),
                  let binding = projects[pid], let beforeBinding = plannedProjects[pid],
                  let lid = binding["list_id"] as? String, uuid(lid),
                  let name = binding["list_name"] as? String, names.contains(name),
                  let aid = binding["account_id"] as? String, uuid(aid), let gid = binding["native_group_id"] as? String, uuid(gid),
                  binding["layout"] as? String == "project_list", binding["parent_id"] is NSNull,
                  row["layout"] as? String == "project_list", row["parent_id"] is NSNull,
                  row["list_id"] as? String == lid, row["list_name"] as? String == name,
                  row["account_id"] as? String == aid, row["native_group_id"] as? String == gid,
                  projects.values.filter({ $0["list_id"] as? String == lid }).count == 1,
                  let projectPath = row["project_path"] as? String,
                  let remote = row["remote"] as? [String: Any], remote["id"] as? String == rid,
                  remote["list_id"] as? String == lid, remote["list"] as? String == name,
                  remote["parent_id"] == nil, remote["subtasks"] == nil, !(remote["version"] as? String ?? "").isEmpty,
                  row["parent"] is NSNull,
                  let original = row["link"] as? [String: Any],
                  let task = (binding["tasks"] as? [String: [String: Any]])?[tid],
                  let texts = row["before_texts"] as? [String: String], Set(texts.keys) == ["current", "future", "paused"],
                  let afterTexts = row["after_texts"] as? [String: String], Set(afterTexts.keys) == Set(texts.keys),
                  let kind = row["source_kind"] as? String,
                  let sourceName = ["current":"current-task.md", "future":"future-tasks.md", "paused":"paused-tasks.md"][kind],
                  row["source_path"] as? String == projectPath + "/ai/" + sourceName,
                  let phase = progresses[rid]?["phase"] as? String,
                  ["prepared", "deleting", "remote_deleted", "hub_cancelled", "committed", "restoring", "restored"].contains(phase) else { throw HubCancellationError("v2_binding_or_snapshot_changed") }
            guard let structure = config["structure"] as? [String: Any],
                  let roles = structure["list_roles"] as? [String: [String: Any]], equal(roles[lid],["kind":"project","project_id":pid]),
                  (structure["projects"] as? [String: [String: Any]])?[pid]?["list_id"] as? String == lid else { throw HubCancellationError("project_list_role_changed") }
            try registered(hub, pid: pid, projectPath: projectPath)
            guard try !migrationPending(hub, config: config, pid: pid) else { throw HubCancellationError("migration_recovery_required") }
            var liveBinding = binding, oldBinding = beforeBinding
            liveBinding.removeValue(forKey: "tasks"); oldBinding.removeValue(forKey: "tasks")
            guard equal(liveBinding, oldBinding) else { throw HubCancellationError("target_binding_changed") }
            var cancelled = original
            cancelled["cancellation"] = ["operation_id": plan["operation_id"]!, "plan_sha256": sha, "reminder_id": rid]
            guard terminal ? equal(task, phase == "restored" ? original : cancelled) : (equal(task, original) || equal(task, cancelled)) else { throw HubCancellationError("foreign_cancellation_receipt") }
        }
        guard let pid = item["project_id"] as? String, let binding = projects[pid], let lid = item["list_id"] as? String, let name = item["list_name"] as? String else { throw HubCancellationError("invalid_v2_item") }
        if !terminal && progress["phase"] as? String != "restoring" {
            guard equal(normalizedReceipts(config, items: items), normalizedReceipts(plannedConfig, items: items)) else { throw HubCancellationError("config_changed") }
        }
        return Self(hub: hub, plan: plan, item: item, state: state, progress: progress, config: config, binding: binding, listID: lid, listName: name, parentID: nil, id: id, sha: sha, path: url)
    }
}

extension HubCancellationScope {
    static func osBuild() -> String {
        var size = 0
        guard sysctlbyname("kern.osversion", nil, &size, nil, 0) == 0, size > 1, size < 128 else { return "" }
        var data = [CChar](repeating: 0, count: size)
        guard sysctlbyname("kern.osversion", &data, &size, nil, 0) == 0 else { return "" }
        return String(decoding: data.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, as: UTF8.self)
    }
    static func executableSHA() throws -> String {
        guard let url = Bundle.main.executableURL else { throw HubCancellationError("executable_unavailable") }
        // Executables are larger than JSON limits. Read only the running executable.
        return hash(try Data(contentsOf: url))
    }
    static func runtimeMatches(_ value: [String: Any]) throws -> Bool {
        let sha = try executableSHA()
        return value["os_build"] as? String == osBuild() && value["binary_sha256"] as? String == sha
    }
    static func simpleSynthetic(_ row: [String: Any], operation: String, id: String, listID: String, name: String) -> Bool {
        Set(row.keys).isSubset(of: ["id", "version", "list", "list_id", "title", "notes", "completed"]) &&
        row["id"] as? String == id && row["list_id"] as? String == listID && row["list"] as? String == name &&
        row["title"] as? String == "Проверка восстановления списка: " + operation &&
        row["notes"] as? String == "Тестовая запись операции " + operation + ". Не является задачей проекта." &&
        (row["completed"] == nil || equal(row["completed"], false)) && !(row["version"] as? String ?? "").isEmpty
    }
    static func normalizedVerification(_ config: [String: Any], operation: String) throws -> [String: Any] {
        var value = config
        guard var entries = value["project_list_verifications"] as? [String: [String: Any]], var entry = entries[operation] else { throw HubCancellationError("verification_binding_missing") }
        entry["plan_sha256"] = NSNull(); entries[operation] = entry; value["project_list_verifications"] = entries
        return value
    }
    static func loadVerification(hub: URL, url: URL, plan: [String: Any], sha: String, id: String, mutation: Bool, state: [String: Any], config: [String: Any]) throws -> Self {
        guard let op = plan["operation_id"] as? String, plan["marker"] as? String == op,
              let items = plan["items"] as? [[String: Any]], items.count == 1, let item = items.first,
              item["reminder_id"] as? String == id, item["project_id"] as? String == "content-system",
              item["task_id"] as? String == "verification-" + op, item["layout"] as? String == "project_list", item["parent_id"] is NSNull,
              Set(item.keys).isDisjoint(with: ["before_texts", "after_texts", "link", "source_path"]),
              let lid = item["list_id"] as? String, uuid(lid), item["list_name"] as? String == "Система контента",
              let aid = item["account_id"] as? String, uuid(aid), let gid = item["native_group_id"] as? String, uuid(gid),
              let projectPath = item["project_path"] as? String, let snapshot = item["remote"] as? [String: Any],
              simpleSynthetic(snapshot, operation: op, id: id, listID: lid, name: "Система контента"),
              let progress = (state["items"] as? [String: [String: Any]])?[id], let phase = progress["phase"] as? String,
              ["prepared", "deleting", "deleted", "restoring", "restored", "cleanup_deleting", "cleaned"].contains(phase),
              state["approved"] as? Bool == true,
              let runtime = plan["runtime"] as? [String: Any], try runtimeMatches(runtime),
              let plannedConfig = plan["config"] as? [String: Any], let originalRaw = plan["config_before_raw"] as? String,
              let configText = plan["config_normalized_json"] as? String,
              hash(Data(configText.utf8)) == plan["config_sha256"] as? String,
              equal(try object(Data(configText.utf8)), try normalizedVerification(plannedConfig, operation: op)) else { throw HubCancellationError("invalid_verification_plan_or_runtime") }
        try registered(hub, pid: "content-system", projectPath: projectPath)
        let configRaw = try bytes(safe(hub.appendingPathComponent("ai/reminders-sync.json").path))
        let closed = phase == "cleaned" && configRaw == Data(originalRaw.utf8)
        if closed && mutation { throw HubCancellationError("verification_already_closed") }
        guard let binding = (plannedConfig["project_list_verifications"] as? [String: [String: Any]])?[op],
              binding["plan_sha256"] is NSNull, binding["approved"] as? Bool == true,
              binding["operation_id"] as? String == op, binding["marker"] as? String == op else { throw HubCancellationError("verification_binding_changed") }
        for key in ["project_id", "task_id", "reminder_id", "layout", "parent_id", "list_id", "list_name", "account_id", "native_group_id"] {
            guard equal(binding[key], item[key]) else { throw HubCancellationError("verification_binding_changed") }
        }
        if !closed {
            guard (config["project_list_verifications"] as? [String: [String: Any]])?[op]?["plan_sha256"] as? String == sha,
                  equal(try normalizedVerification(config, operation: op), try normalizedVerification(plannedConfig, operation: op)) else { throw HubCancellationError("verification_config_changed") }
        }
        let allowPath = hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path
        guard plannedConfig["standard_allowlist_file"] as? String == allowPath,
              ProcessInfo.processInfo.environment["HUB_REMINDERS_ALLOWED_LISTS_FILE"] == allowPath else { throw HubCancellationError("verification_allowlist_path") }
        let allowRaw = try bytes(safe(allowPath))
        guard hash(allowRaw) == plan["allowlist_sha256"] as? String,
              (try object(allowRaw)["names"] as? [String])?.contains("Система контента") == true else { throw HubCancellationError("verification_allowlist_changed") }
        guard let migrationPath = plan["migration_plan"] as? String, let migrationSHA = plan["migration_sha256"] as? String else { throw HubCancellationError("verification_migration_missing") }
        let migrationURL = try safe(migrationPath), migrationRaw = try bytes(migrationURL), migration = try object(migrationRaw)
        let migrationStateRaw = try bytes(safe(migrationURL.deletingLastPathComponent().appendingPathComponent("state.json").path))
        let migrationState = try object(migrationStateRaw)
        guard migrationPath == hub.appendingPathComponent("ai/reminders-project-lists/\(migration["operation"] as? String ?? "")/plan.json").path,
              migration["hub"] as? String == hub.path, migration["kind"] as? String == "migration", migration["project"] as? String == "content-system",
              hash(migrationRaw) == migrationSHA, hash(migrationStateRaw) == plan["migration_state_sha256"] as? String,
              equal(migrationState, plan["migration_state"]), migrationState["phase"] as? String == "destination_ready",
              migrationState["sha256"] as? String == migrationSHA, (migrationState["steps"] as? [String: Any])?.isEmpty == true,
              migrationState["group_done"] as? Bool == true, migrationState["list_id"] as? String == lid,
              migration["account_id"] as? String == aid, migration["group_id"] as? String == gid, migration["list_name"] as? String == "Система контента",
              (config["project_list_migrations_pending"] as? [String: String])?["content-system"] == migrationSHA,
              let migrationConfig = migration["config_raw"] as? String else { throw HubCancellationError("verification_destination_not_ready") }
        var before = try object(Data(migrationConfig.utf8))
        var pending = before["project_list_migrations_pending"] as? [String: String] ?? [:]; pending["content-system"] = migrationSHA; before["project_list_migrations_pending"] = pending
        guard equal(before, try object(Data(originalRaw.utf8))) else { throw HubCancellationError("verification_original_config_changed") }
        guard let projects = config["projects"] as? [String: [String: Any]] else { throw HubCancellationError("verification_projects_missing") }
        for project in projects.values {
            guard project["list_id"] as? String != lid, project["parent_id"] as? String != id,
                  (project["history"] as? [String: Any])?[id] == nil,
                  let tasks = project["tasks"] as? [String: [String: Any]], tasks["verification-" + op] == nil,
                  !tasks.values.contains(where: { $0["reminder_id"] as? String == id }) else { throw HubCancellationError("verification_real_binding_collision") }
        }
        let folder = url.deletingLastPathComponent(), bootstrapRaw = try bytes(safe(folder.appendingPathComponent("bootstrap.json").path)), bootstrap = try object(bootstrapRaw)
        guard hash(bootstrapRaw) == plan["bootstrap_sha256"] as? String, bootstrap["approved"] as? Bool == true,
              bootstrap["phase"] as? String == "created", bootstrap["purpose"] as? String == "project_list_verification", bootstrap["marker"] as? String == op,
              (bootstrap["create_receipt"] as? [String: Any])?["id"] as? String == id, equal(bootstrap["runtime"], runtime), bootstrap["operation_id"] as? String == op,
              bootstrap["reminder_id"] as? String == id, equal(bootstrap["snapshot"], snapshot) else { throw HubCancellationError("verification_bootstrap_changed") }
        for other in try FileManager.default.contentsOfDirectory(at: folder.deletingLastPathComponent(), includingPropertiesForKeys: nil) where other.lastPathComponent != op {
            for name in ["plan.json", "state.json"] {
                let path = try safe(other.appendingPathComponent(name).path)
                if FileManager.default.fileExists(atPath: path.path) {
                    let text = String(decoding: try bytes(path), as: UTF8.self)
                    guard !text.contains(id), !text.contains("verification-" + op) else { throw HubCancellationError("verification_old_plan_collision") }
                }
            }
        }
        return Self(hub: hub, plan: plan, item: item, state: state, progress: progress, config: config, binding: binding, listID: lid, listName: "Система контента", parentID: nil, id: id, sha: sha, path: url)
    }
    func verificationMutation(_ restoring: Bool) throws {
        guard isVerification, let phase = progress["phase"] as? String, let events = state["events"] as? [[String: Any]] else { throw HubCancellationError("verification_state_missing") }
        let stage = restoring ? "restore" : phase == "cleanup_deleting" ? "cleanup" : "delete"
        guard phase == (restoring ? "restoring" : stage == "cleanup" ? "cleanup_deleting" : "deleting"),
              events.last?["stage"] as? String == "before_" + stage else { throw HubCancellationError("verification_step_order") }
        if stage != "delete" {
            guard progress["deleted_snapshot"] is [String: Any], events.contains(where: { $0["stage"] as? String == "confirmed_delete" }) else { throw HubCancellationError("verification_delete_proof_missing") }
        }
        if stage == "cleanup" {
            guard progress["restored_snapshot"] is [String: Any], events.contains(where: { $0["stage"] as? String == "confirmed_restore" }), progress["cleaned_snapshot"] == nil else { throw HubCancellationError("verification_cleanup_proof_missing") }
        }
        guard !events.contains(where: { $0["stage"] as? String == "after_" + stage }) else { throw HubCancellationError("verification_mutation_already_completed") }
    }
    static func acceptedEvidence(hub: URL, config: [String: Any]) throws -> [String: Any] {
        let path = try safe(hub.appendingPathComponent("ai/reminders-project-list-verification.json").path), raw = try bytes(path)
        guard config["project_list_verification_sha256"] as? String == hash(raw) else { throw HubCancellationError("verification_evidence_unpinned") }
        let receipt = try object(raw)
        guard receipt["protocol"] as? Int == 2, receipt["accepted_by"] as? String == "parent", receipt["independent_review_accepted"] as? Bool == true,
              let runtime = receipt["runtime"] as? [String: Any], try runtimeMatches(runtime),
              let op = receipt["operation_id"] as? String, uuid(op), receipt["marker"] as? String == op,
              let rid = receipt["synthetic_uuid"] as? String, uuid(rid), let lid = receipt["list_id"] as? String, uuid(lid),
              let aid = receipt["account_id"] as? String, uuid(aid), let gid = receipt["group_id"] as? String, uuid(gid) else { throw HubCancellationError("verification_evidence_identity") }
        guard config["standard_allowlist_file"] as? String == hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path,
              let projects = config["projects"] as? [String: [String: Any]], let current = projects["content-system"],
              current["layout"] as? String == "project_list", current["parent_id"] is NSNull,
              current["list_id"] as? String == lid, current["account_id"] as? String == aid, current["native_group_id"] as? String == gid,
              projects.values.filter({ $0["list_id"] as? String == lid }).count == 1 else { throw HubCancellationError("verification_evidence_current_scope") }
        try registered(hub, pid: "content-system", projectPath: hub.appendingPathComponent("projects/content-system").path)
        let folder = hub.appendingPathComponent("ai/reminders-cancellations/\(op)")
        let planRaw = try bytes(safe(folder.appendingPathComponent("plan.json").path)), plan = try object(planRaw)
        let stateRaw = try bytes(safe(folder.appendingPathComponent("state.json").path)), state = try object(stateRaw)
        guard hash(planRaw) == receipt["plan_sha256"] as? String, hash(stateRaw) == receipt["journal_sha256"] as? String,
              state["plan_sha256"] as? String == hash(planRaw), state["approved"] as? Bool == true,
              plan["version"] as? Int == 2, plan["purpose"] as? String == "project_list_verification", plan["operation_id"] as? String == op, plan["marker"] as? String == op,
              equal(plan["runtime"], runtime), let items = plan["items"] as? [[String: Any]], items.count == 1, let item = items.first,
              item["reminder_id"] as? String == rid, item["list_id"] as? String == lid, item["account_id"] as? String == aid, item["native_group_id"] as? String == gid,
              let original = item["remote"] as? [String: Any], simpleSynthetic(original, operation: op, id: rid, listID: lid, name: "Система контента"),
              let progress = (state["items"] as? [String: [String: Any]])?[rid], progress["phase"] as? String == "cleaned",
              let events = state["events"] as? [[String: Any]] else { throw HubCancellationError("verification_evidence_dependencies") }
        var lastIndex = -1
        for (stage, expectedState, key) in [("delete", "deleted", "deleted_snapshot"), ("restore", "active", "restored_snapshot"), ("cleanup", "deleted", "cleaned_snapshot")] {
            guard let stored = progress[key] as? [String: Any], stored["state"] as? String == expectedState,
                  let snapshot = stored["snapshot"] as? [String: Any], stored["version"] as? String == snapshot["version"] as? String, simpleSynthetic(snapshot, operation: op, id: rid, listID: lid, name: "Система контента"),
                  HubCancellationChecks.sameFields(snapshot, original, version: false) else { throw HubCancellationError("verification_evidence_snapshot") }
            for prefix in ["after_", "confirmed_"] {
                let matches = events.enumerated().filter { $0.element["stage"] as? String == prefix + stage }
                guard matches.count == 1, let match = matches.first, match.offset > lastIndex, equal(match.element["remote"], stored) else { throw HubCancellationError("verification_evidence_readbacks") }
                lastIndex = match.offset
            }
        }
        let bootstrapRaw = try bytes(safe(folder.appendingPathComponent("bootstrap.json").path))
        let boot = try object(bootstrapRaw)
        guard hash(bootstrapRaw) == plan["bootstrap_sha256"] as? String, boot["phase"] as? String == "created", (boot["create_receipt"] as? [String: Any])?["id"] as? String == rid, equal(boot["snapshot"], original) else { throw HubCancellationError("verification_evidence_bootstrap") }
        guard let migrationPath = plan["migration_plan"] as? String else { throw HubCancellationError("verification_evidence_migration") }
        let migrationURL = try safe(migrationPath), migrationRaw = try bytes(migrationURL), migration = try object(migrationRaw)
        guard migrationPath == hub.appendingPathComponent("ai/reminders-project-lists/\(migration["operation"] as? String ?? "")/plan.json").path,
              hash(migrationRaw) == plan["migration_sha256"] as? String,
              migration["project"] as? String == "content-system", migration["account_id"] as? String == aid, migration["group_id"] as? String == gid,
              let originalState = plan["migration_state"] as? [String: Any], originalState["phase"] as? String == "destination_ready",
              (originalState["steps"] as? [String: Any])?.isEmpty == true, originalState["list_id"] as? String == lid else { throw HubCancellationError("verification_evidence_migration") }
        let completedMigration = try object(bytes(safe(migrationURL.deletingLastPathComponent().appendingPathComponent("state.json").path)))
        guard completedMigration["phase"] as? String == "complete", completedMigration["list_id"] as? String == lid,
              equal(completedMigration["sha256"], plan["migration_sha256"]),
              equal((config["project_list_migrations_completed"] as? [String: Any])?["content-system"], plan["migration_sha256"]),
              (config["project_list_migrations_pending"] as? [String: Any])?["content-system"] == nil else { throw HubCancellationError("verification_migration_not_completed") }
        let allowRaw = try bytes(safe(hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path))
        guard let historicalAllow = (migration["permission"] as? [String: Any])?["after"] as? String,
              hash(Data(historicalAllow.utf8)) == plan["allowlist_sha256"] as? String,
              let historicalNames = try object(Data(historicalAllow.utf8))["names"] as? [String],
              let currentNames = try object(allowRaw)["names"] as? [String], !currentNames.isEmpty,
              Set(historicalNames).isSubset(of:Set(currentNames)) else { throw HubCancellationError("verification_evidence_allowlist") }
        return receipt
    }
}

extension HubCancellationScope {
    var isHistorical: Bool {
        guard !isRoot, let pid = item["project_id"] as? String else { return false }
        return (config["projects"] as? [String: [String: Any]])?[pid]?["historical_binding_migration"] != nil
    }
    static func structural(_ binding: [String: Any]) -> [String: Any] {
        binding.filter { ["layout","list_id","list_name","parent_id","account_id","native_group_id","retired_parent"].contains($0.key) }
    }
    static func historicalReceipt(hub: URL, config: [String: Any], plan: [String: Any], item: [String: Any], state: [String: Any], sha: String) throws -> [String: Any] {
        guard plan["version"] as? Int == 1, let pid = item["project_id"] as? String, let rid = item["reminder_id"] as? String,
              let tid = item["task_id"] as? String, let projects = config["projects"] as? [String: [String: Any]], let binding = projects[pid],
              let ref = binding["historical_binding_migration"] as? [String: String], let path = ref["path"] else { throw HubCancellationError("historical_reference_missing") }
        let raw = try bytes(safe(path)), receipt = try object(raw)
        guard hash(raw) == ref["sha256"], receipt["protocol"] as? Int == 1, receipt["contract"] as? String == "legacy-restore-then-active-move-v1",
              let op = receipt["migration_operation"] as? String, uuid(op),
              path == hub.appendingPathComponent("ai/historical_binding_migrations/\(op)/receipt.json").path,
              let migrationPath = receipt["migration_plan"] as? String,
              migrationPath == hub.appendingPathComponent("ai/reminders-project-lists/\(op)/plan.json").path else { throw HubCancellationError("historical_receipt_pin") }
        let migrationURL = try safe(migrationPath), migrationRaw = try bytes(migrationURL), migration = try object(migrationRaw)
        let migrationState = try object(bytes(safe(migrationURL.deletingLastPathComponent().appendingPathComponent("state.json").path)))
        let digest = hash(migrationRaw)
        guard receipt["migration_sha256"] as? String == digest, migration["kind"] as? String == "migration", migration["project"] as? String == pid,
              migration["operation"] as? String == op, migration["hub"] as? String == hub.path,
              migrationState["phase"] as? String == "complete", migrationState["approved"] as? Bool == true,
              migrationState["sha256"] as? String == digest, equal(migrationState["list_id"], binding["list_id"]),
              (config["project_list_migrations_completed"] as? [String: String])?[pid] == digest,
              (config["project_list_migrations_pending"] as? [String: Any])?[pid] == nil,
              let finalText = migrationState["final_config"] as? String,
              let finalBinding = (try object(Data(finalText.utf8))["projects"] as? [String: [String: Any]])?[pid],
              let beforeText = migration["config_raw"] as? String,
              let beforeBinding = (try object(Data(beforeText.utf8))["projects"] as? [String: [String: Any]])?[pid],
              let historical = migration["historical"] as? [String: [String: Any]], let proof = historical[rid],
              let runtime = migration["historical_runtime"] as? [String: Any], try runtimeMatches(runtime),
              let children = migration["children"] as? [String], let steps = migrationState["steps"] as? [String: [String: Any]],
              Set(children) == Set(steps.keys), steps.values.allSatisfy({ $0["status"] as? String == "done" }) else { throw HubCancellationError("historical_migration_uncommitted") }
        let expected: [String: Any] = ["protocol":1,"contract":"legacy-restore-then-active-move-v1","migration_operation":op,"migration_plan":migrationPath,
            "migration_sha256":digest,"project_id":pid,"before":structural(beforeBinding),"after":structural(finalBinding),
            "historical":historical,"runtime":runtime,"old_account_id":migration["account_id"]!,"moved_ids":children]
        guard equal(receipt, expected), equal(structural(binding), receipt["after"]), equal(finalBinding["historical_binding_migration"],ref),
              let itemText = proof["item_json"] as? String, hash(Data(itemText.utf8)) == proof["item_sha256"] as? String,
              equal(try object(Data(itemText.utf8)), item), let receiptText = proof["receipt_json"] as? String,
              hash(Data(receiptText.utf8)) == proof["receipt_sha256"] as? String,
              let operation = plan["operation_id"] as? String,
              proof["plan"] as? String == hub.appendingPathComponent("ai/reminders-cancellations/\(operation)/plan.json").path,
              proof["plan_sha256"] as? String == sha,
              let progress = (state["items"] as? [String: [String: Any]])?[rid], state["approved"] as? Bool == true,
              ["committed","restoring","restored"].contains(progress["phase"] as? String ?? ""),
              equal(progress["deleted_snapshot"],proof["deleted_snapshot"]),
              (proof["deleted_snapshot"] as? [String: Any])?["state"] as? String == "deleted" else { throw HubCancellationError("historical_original_changed") }
        let cancelledReceipt: [String: Any] = ["operation_id":operation,"plan_sha256":sha,"reminder_id":rid]
        guard equal(try object(Data(receiptText.utf8)),cancelledReceipt), let original = item["link"] as? [String: Any],
              let link = (binding["tasks"] as? [String: [String: Any]])?[tid] else { throw HubCancellationError("historical_link_changed") }
        var cancelled = original; cancelled["cancellation"] = cancelledReceipt
        let phase = progress["phase"] as? String
        let localCommit = phase == "restoring" && ["canonical_restore","complete"].contains((progress["relocation"] as? [String: Any])?["phase"] as? String ?? "")
        guard (phase == "restored" ? equal(link,original) : (equal(link,cancelled) || (localCommit && equal(link,original)))), binding["layout"] as? String == "project_list", binding["parent_id"] is NSNull,
              let lid = binding["list_id"] as? String, uuid(lid), let name = binding["list_name"] as? String,
              let aid = binding["account_id"] as? String, uuid(aid), aid == receipt["old_account_id"] as? String,
              uuid(binding["native_group_id"] as? String), projects.values.filter({ $0["list_id"] as? String == lid }).count == 1,
              let structure = config["structure"] as? [String: Any], let roles = structure["list_roles"] as? [String: [String: Any]],
              equal(roles[lid],["kind":"project","project_id":pid]),
              (structure["projects"] as? [String: [String: Any]])?[pid]?["list_id"] as? String == lid,
              config["standard_allowlist_file"] as? String == hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path,
              (try object(bytes(safe(hub.appendingPathComponent("ai/reminders-standard-allowlist.json").path)))["names"] as? [String])?.contains(name) == true,
              let projectPath = item["project_path"] as? String else { throw HubCancellationError("historical_destination_changed") }
        try registered(hub, pid: pid, projectPath: projectPath)
        guard let parentID = item["parent_id"] as? String, let after = receipt["after"] as? [String: Any],
              let parent = (after["retired_parent"] as? [String: Any])?["snapshot"] as? [String: Any],
              let source = (migration["source"] as? [String: [String: Any]])?[parentID], let oldParent = item["parent"] as? [String: Any],
              parent["id"] as? String == parentID, equal(parent["list_id"], item["list_id"]), equal(parent["list"], item["list_name"]),
              parent["parent_id"] == nil || parent["parent_id"] is NSNull,
              parent["subtasks"] == nil || (parent["subtasks"] as? [Any])?.isEmpty == true else { throw HubCancellationError("historical_parent_changed") }
        let clean: ([String: Any]) -> [String: Any] = { $0.filter { !["version","subtasks"].contains($0.key) } }
        guard equal(clean(parent),clean(source)), equal(clean(source),clean(oldParent)) else { throw HubCancellationError("historical_parent_changed") }
        return receipt
    }
}
