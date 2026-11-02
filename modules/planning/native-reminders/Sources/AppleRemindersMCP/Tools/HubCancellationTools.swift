import Foundation
import EventKit
import Wire
import Darwin

enum HubCancellationTools {
    static func verifiedBuild() -> Bool {
        var size = 0
        guard sysctlbyname("kern.osversion", nil, &size, nil, 0) == 0, size > 1, size < 128 else { return false }
        var data = [CChar](repeating: 0, count: size)
        guard sysctlbyname("kern.osversion", &data, &size, nil, 0) == 0 else { return false }
        return HubCancellationScope.restoreVerified(on: String(decoding: data.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, as: UTF8.self))
    }
    static func inspect(_ scope: HubCancellationScope, _ store: RemindersStore, list: ListInfo) throws -> [String: Any] {
        let active = try store.cancellationActive(scope.id, list: list, requireRoot: scope.isRoot)
        let deleted = try store.cancellationDeleted(scope.id, list: list, parentID: scope.parentID)
        return try HubCancellationChecks.status(active: active, deleted: deleted, id: scope.id,
                                                listID: scope.listID, listName: scope.listName, parentID: scope.parentID)
    }
    static func scope(_ input: [String: JSON], mutation: Bool, restoring: Bool = false) throws -> HubCancellationScope {
        let keys = Set(input.keys)
        let needed: Set<String> = restoring ? ["plan", "plan_sha256", "id", "version", "restore_plan", "restore_sha256"] : mutation ? ["plan", "plan_sha256", "id", "version"] : ["plan", "plan_sha256", "id"]
        guard keys == needed, let path = input["plan"]?.string, let sha = input["plan_sha256"]?.string,
              let id = input["id"]?.string else { throw HubCancellationError("invalid_arguments") }
        if mutation { guard let version = input["version"]?.string, !version.isEmpty else { throw HubCancellationError("version_required") } }
        if restoring { guard input["restore_plan"]?.string != nil, input["restore_sha256"]?.string != nil else { throw HubCancellationError("restore_token_required") } }
        return try HubCancellationScope.load(path: path, sha: sha, id: id, mutation: mutation)
    }
    static func run(_ operation: String, input: [String: JSON], store: RemindersStore) throws -> [String: Any] {
        let mutate = operation != "hub_cancel_status"
        let restore = operation == "hub_restore_reminder"
        let scope = try scope(input, mutation: mutate, restoring: restore)
        return try runValidated(operation, input: input, store: store, scope: scope)
    }
    static func runValidated(_ operation: String, input: [String: JSON], store: RemindersStore, scope: HubCancellationScope) throws -> [String: Any] {
        let mutate = operation != "hub_cancel_status", restore = operation == "hub_restore_reminder"
        if mutate && !scope.isRoot { guard verifiedBuild() else { throw HubCancellationError("same_uuid_restore_requires_repeat_verification_on_this_macos_build") } }
        if mutate && scope.isRoot {
            if scope.isVerification { try scope.verificationMutation(restore) }
            else {
                let proof = try HubCancellationScope.acceptedEvidence(hub: scope.hub, config: scope.config)
                guard HubCancellationScope.equal(proof["account_id"], scope.item["account_id"]) else { throw HubCancellationError("project_list_verification_scope_changed") }
            }
        }
        if scope.isHistorical && mutate && !restore { throw HubCancellationError("historical_delete_forbidden") }
        if scope.isHistorical {
            guard let pid = scope.item["project_id"] as? String, let current = (scope.config["projects"] as? [String: [String: Any]])?[pid],
                  let lid = current["list_id"] as? String, let name = current["list_name"] as? String else { throw HubCancellationError("historical_destination_missing") }
            let destination = try store.cancellationList(id:lid,name:name)
            let source = try store.cancellationList(id:scope.listID,name:scope.listName)
            guard destination.accountID == current["account_id"] as? String, source.accountID == destination.accountID,
                  destination.groupID == current["native_group_id"] as? String,
                  try store.cancellationChildren(scope.id,list:source).isEmpty,
                  try store.cancellationChildren(scope.id,list:destination).isEmpty,
                  try store.groups().filter({ $0.id == destination.groupID && $0.accountID == destination.accountID }).count == 1 else { throw HubCancellationError("historical_destination_identity") }
        }
        let list = try store.cancellationList(id: scope.listID, name: scope.listName)
        if scope.isRoot {
            guard list.accountID == scope.item["account_id"] as? String, list.groupID == scope.item["native_group_id"] as? String,
                  try store.groups().filter({ $0.id == list.groupID && $0.accountID == list.accountID }).count == 1 else { throw HubCancellationError("project_list_account_or_group_changed") }
        }
        let status = try inspect(scope, store, list: list)
        if !mutate { return status }
        let phase = scope.progress["phase"] as? String
        if scope.isRoot { return try runRoot(scope, input: input, store: store, list: list, status: status, restoring: restore) }
        guard let parentID = scope.parentID else { throw HubCancellationError("legacy_parent_required") }
        if restore {
            guard phase == "restoring", let tokenPath = input["restore_plan"]?.string, let token = input["restore_sha256"]?.string else { throw HubCancellationError("restore_phase_required") }
            let row = try scope.restoreToken(path: tokenPath, sha: token)
            guard let expected = row["remote"] as? [String: Any], let expectedParent = scope.item["parent"] as? [String: Any],
                  let version = input["version"]?.string else { throw HubCancellationError("fresh_restore_token_conflict") }
            let parent = try store.cancellationActive(parentID, list: list)
            guard parent?["id"] as? String == scope.parentID,
                  HubCancellationChecks.restoreReady(status, version: version, tokenRemote: expected,
                                                      parent: parent, expectedParent: expectedParent, target: scope.id) else { throw HubCancellationError("fresh_restore_token_conflict") }
            try store.cancellationRestore(scope.id, list: list, parentID: scope.parentID)
            let after = try inspect(scope, store, list: list)
            guard after["state"] as? String == "active", let fresh = after["snapshot"] as? [String: Any],
                  let old = status["snapshot"] as? [String: Any], HubCancellationChecks.sameFields(fresh, old, version: false) else { throw HubCancellationError("restore_readback_fields_changed") }
            return after
        }
        guard phase == "deleting" else { throw HubCancellationError("delete_phase_required") }
        guard let expected = scope.item["remote"] as? [String: Any], let expectedParent = scope.item["parent"] as? [String: Any],
              let version = input["version"]?.string else { throw HubCancellationError("fresh_delete_conflict") }
        let parent = try store.cancellationActive(parentID, list: list)
        let children = try store.cancellationChildren(scope.id, list: list)
        guard parent?["id"] as? String == scope.parentID,
              HubCancellationChecks.deleteReady(status, version: version, remote: expected,
                                                parent: parent, expectedParent: expectedParent, target: scope.id,
                                                children: children) else { throw HubCancellationError("fresh_delete_conflict") }
        try store.cancellationDelete(scope.id)
        let after = try inspect(scope, store, list: list)
        guard after["state"] as? String == "deleted", let deleted = after["snapshot"] as? [String: Any],
              HubCancellationChecks.sameFields(deleted, expected, version: false) else { throw HubCancellationError("delete_readback_fields_changed") }
        return after
    }
    static func runRoot(_ scope: HubCancellationScope, input: [String: JSON], store: RemindersStore, list: ListInfo, status: [String: Any], restoring: Bool) throws -> [String: Any] {
        guard let version = input["version"]?.string, status["version"] as? String == version,
              try store.cancellationChildren(scope.id, list: list).isEmpty,
              let snapshot = status["snapshot"] as? [String: Any], snapshot["parent_id"] == nil, snapshot["subtasks"] == nil else { throw HubCancellationError("root_version_or_hierarchy_changed") }
        let phase = scope.progress["phase"] as? String
        if restoring {
            guard phase == "restoring", status["state"] as? String == "deleted",
                  let tokenPath = input["restore_plan"]?.string, let token = input["restore_sha256"]?.string else { throw HubCancellationError("restore_phase_required") }
            let row = try scope.restoreToken(path: tokenPath, sha: token)
            guard HubCancellationScope.equal(row["remote"], status) else { throw HubCancellationError("fresh_restore_token_conflict") }
            try store.cancellationRestore(scope.id, list: list, parentID: nil)
        } else {
            guard phase == "deleting" || (scope.isVerification && phase == "cleanup_deleting"), status["state"] as? String == "active" else { throw HubCancellationError("delete_phase_required") }
            let expected = phase == "cleanup_deleting" ? (scope.progress["restored_snapshot"] as? [String: Any])?["snapshot"] as? [String: Any] : scope.item["remote"] as? [String: Any]
            guard let expected, HubCancellationChecks.sameFields(snapshot, expected) else { throw HubCancellationError("fresh_delete_conflict") }
            try store.cancellationDelete(scope.id)
        }
        let after = try inspect(scope, store, list: list)
        guard after["state"] as? String == (restoring ? "active" : "deleted"),
              let fresh = after["snapshot"] as? [String: Any], fresh["parent_id"] == nil,
              try store.cancellationChildren(scope.id, list: list).isEmpty,
              HubCancellationChecks.sameFields(fresh, snapshot, version: false) else { throw HubCancellationError("root_mutation_readback_changed") }
        return after
    }
    static func tools(_ store: RemindersStore) -> [Tool] {
        let fields: [String: JSON] = ["plan": Schema.text("Canonical Hub plan path"), "plan_sha256": Schema.text("Plan SHA-256"), "id": Schema.text("Exact reminder UUID")]
        let status = Tool("hub_cancel_status", title: "Exact cancellation status", summary: "Reads one planned reminder UUID", input: .object(fields), effect: .reads) { input in
            try await answer("hub_cancel_status", input, store)
        }
        var mutating = fields; mutating["version"] = Schema.text("Fresh exact version")
        let cancel = Tool("hub_cancel_reminder", title: "Cancel planned reminder", summary: "Deletes only one approved planned UUID", input: .object(mutating), effect: .writes) { input in
            try await answer("hub_cancel_reminder", input, store)
        }
        var restoring = mutating; restoring["restore_plan"] = Schema.text("Fresh immutable restore plan"); restoring["restore_sha256"] = Schema.text("Restore token SHA-256")
        let undo = Tool("hub_restore_reminder", title: "Restore planned reminder", summary: "Restores only one approved planned UUID", input: .object(restoring), effect: .writes) { input in
            try await answer("hub_restore_reminder", input, store)
        }
        let capabilities = Tool("hub_cancel_capabilities", title: "Cancellation capabilities", summary: "Reports no concurrent edits contract", input: .object([:]), effect: .reads) { input in
            guard input.isEmpty else { return ToolAnswer("invalid_arguments", failed: true) }
            let verified = verifiedBuild()
            var result: [String: JSON] = ["protocol": .int(1), "atomic_version_check": false, "optimistic_version_check": true,
                                          "same_uuid_restore_verified": .bool(verified), "requires_no_concurrent_edits": true,
                                          "verified_os_build": "25G83"]
            result["supported_versions"] = .array([.int(1), .int(2)])
            result["project_list_same_uuid_restore_verified"] = false
            do {
                let hub = URL(fileURLWithPath: HubCancellationScope.approvedHubRoot)
                let config = try HubCancellationScope.object(HubCancellationScope.bytes(HubCancellationScope.safe(hub.appendingPathComponent("ai/reminders-sync.json").path)))
                let proof = try HubCancellationScope.acceptedEvidence(hub: hub, config: config)
                result["project_list_same_uuid_restore_verified"] = true
                result["project_list_verified_scope"] = .object(["family": "same_os_executor_account", "account_id": .string(proof["account_id"] as! String)])
            } catch { result["project_list_reason"] = .string((error as? HubCancellationError)?.description ?? "project_list_verification_missing") }
            if !verified { result["reason"] = "Повторная проверка восстановления нужна для этой версии macOS." }
            return ToolAnswer(JSON.object(result).text)
        }
        return [capabilities, status, cancel, undo]
    }
    static func answer(_ operation: String, _ input: [String: JSON], _ store: RemindersStore) async throws -> ToolAnswer {
        // The executor never requests TCC access from a call.
        guard EKEventStore.authorizationStatus(for: .reminder) == .fullAccess else { return ToolAnswer("existing_full_access_required_no_prompt", failed: true) }
        do {
            let value = try run(operation, input: input, store: store)
            let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
            return ToolAnswer(String(decoding: data, as: UTF8.self))
        } catch {
            let code = (error as? HubCancellationError)?.description ?? "native_scope_or_reminder_conflict"
            return ToolAnswer(code, failed: true)
        }
    }
}
