import Foundation
import CryptoKit
import Darwin

struct HubDiagnosticError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}
protocol HubDiagnosticBackend: AnyObject {
    func diagnosticSnapshot(_ id: String) throws -> [String: Any]
    func diagnosticDeleted(_ ids: [String]) throws -> [String: [String: Any]]
    func diagnosticChildren(_ id: String, listID: String) throws -> Set<String>
    func diagnosticDelete(_ id: String) throws
    func diagnosticRestore(_ id: String, listID: String, parentID: String?) throws
    func diagnosticRace(_ id: String, notes: String) throws -> [String: Any]
}
struct HubDiagnosticRecord {
    let role: String, id: String, title: String, notes: String
    let parentID: String?
    let snapshot: [String: Any]
}
struct HubDiagnosticPlan {
    static let listID = "F5F159E5-0132-44CE-B961-B28EA77D47E6"
    static let listName = "вайбкодинг"
    static let approvedRoot = "/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/experiments/reminders-cancellation-20261026/native-live-test"
    let path: URL, sha256: String, marker: String, operation: String
    let records: [HubDiagnosticRecord]
    static func sha(_ data: Data) -> String { SHA256.hash(data:data).map { String(format:"%02x",$0) }.joined() }
    static func safe(_ path: String) throws -> URL {
        guard path.hasPrefix("/"), !path.split(separator:"/",omittingEmptySubsequences:false).contains("..") else { throw HubDiagnosticError("unsafe_path") }
        let url = URL(fileURLWithPath:path)
        guard url.standardizedFileURL.path == path, url.resolvingSymlinksInPath().path == path else { throw HubDiagnosticError("unsafe_path") }
        return url
    }
    static func bytes(_ url: URL) throws -> Data {
        _ = try safe(url.path)
        let attributes = try FileManager.default.attributesOfItem(atPath:url.path)
        guard (attributes[.size] as? NSNumber)?.intValue ?? Int.max <= 1_048_576 else { throw HubDiagnosticError("plan_too_large") }
        let data = try Data(contentsOf:url)
        guard data.count <= 1_048_576 else { throw HubDiagnosticError("plan_too_large") }
        return data
    }
    static func normalized(_ value: [String:Any], versions: Bool = true, deleted: Bool = false) -> [String:Any] {
        var result = value
        result.removeValue(forKey:"subtasks")
        if !versions { result.removeValue(forKey:"version") }
        if deleted { for key in ["list_id","list","parent_id"] { result.removeValue(forKey:key) } }
        return result
    }
    static func equal(_ a:[String:Any], _ b:[String:Any]) -> Bool { NSDictionary(dictionary:a).isEqual(to:b) }
    static func load(path: String, sha256: String, approvedRoot: String = approvedRoot) throws -> Self {
        let url = try safe(path), root = try safe(approvedRoot)
        guard url.lastPathComponent == "approved-plan.json", url.deletingLastPathComponent().deletingLastPathComponent() == root else { throw HubDiagnosticError("plan_outside_approved_root") }
        let data = try bytes(url)
        guard sha256.count == 64, sha(data) == sha256 else { throw HubDiagnosticError("plan_checksum_mismatch") }
        guard let value = try JSONSerialization.jsonObject(with:data) as? [String:Any], value["version"] as? Int == 1,
              let operation = value["operation_id"] as? String, UUID(uuidString:operation) != nil,
              operation == url.deletingLastPathComponent().lastPathComponent,
              let marker = value["run_marker"] as? String, UUID(uuidString:marker) != nil, marker != operation,
              value["list_id"] as? String == listID, value["list_name"] as? String == listName,
              let rows = value["records"] as? [[String:Any]], rows.count == 3 else { throw HubDiagnosticError("invalid_diagnostic_scope") }
        var records:[HubDiagnosticRecord] = []
        for row in rows {
            guard let role = row["role"] as? String, ["parent","ordinary","series"].contains(role),
                  let id = row["id"] as? String, UUID(uuidString:id) != nil,
                  let title = row["title"] as? String, title.contains(marker),
                  let notes = row["notes"] as? String, notes.contains(marker),
                  let snapshot = row["snapshot"] as? [String:Any], snapshot["id"] as? String == id,
                  snapshot["title"] as? String == title, snapshot["notes"] as? String == notes,
                  snapshot["list_id"] as? String == listID, snapshot["list"] as? String == listName,
                  !(snapshot["version"] as? String ?? "").isEmpty, snapshot["completed"] as? Bool != true else { throw HubDiagnosticError("invalid_diagnostic_record") }
            let parent = row["parent_id"] as? String
            guard parent == snapshot["parent_id"] as? String else { throw HubDiagnosticError("parent_mismatch") }
            guard (role == "series") == (snapshot["repeat"] as? [String:Any] != nil) else { throw HubDiagnosticError("series_scope_mismatch") }
            records.append(.init(role:role,id:id,title:title,notes:notes,parentID:parent,snapshot:normalized(snapshot)))
        }
        guard Set(records.map { $0.id.lowercased() }).count == 3, Set(records.map(\.role)) == ["parent","ordinary","series"],
              let parent = records.first(where:{$0.role == "parent"}), parent.parentID == nil,
              records.filter({$0.role != "parent"}).allSatisfy({$0.parentID == parent.id}) else { throw HubDiagnosticError("duplicate_or_foreign_parent") }
        return .init(path:url,sha256:sha256,marker:marker,operation:operation,records:records)
    }
}

enum HubCancellationDiagnostic {
    static func durable(_ path:URL,_ value:[String:Any]) throws {
        _ = try HubDiagnosticPlan.safe(path.path)
        let data = try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys,.prettyPrinted])
        let temporary = path.deletingLastPathComponent().appendingPathComponent(".journal-"+UUID().uuidString)
        let fd = open(temporary.path,O_WRONLY|O_CREAT|O_EXCL,0o600)
        guard fd >= 0 else { throw HubDiagnosticError("journal_open_failed") }
        var renamed = false
        defer { close(fd); if !renamed { unlink(temporary.path) } }
        try data.withUnsafeBytes { buffer in
            var position = 0
            while position < buffer.count {
                let count = write(fd,buffer.baseAddress!.advanced(by:position),buffer.count-position)
                guard count > 0 else { throw HubDiagnosticError("journal_write_failed") }
                position += count
            }
        }
        guard fsync(fd) == 0, rename(temporary.path,path.path) == 0 else { throw HubDiagnosticError("journal_flush_failed") }
        renamed = true
        let directory = open(path.deletingLastPathComponent().path,O_RDONLY)
        guard directory >= 0 else { throw HubDiagnosticError("journal_directory_failed") }
        defer { close(directory) }
        guard fsync(directory) == 0 else { throw HubDiagnosticError("journal_directory_flush_failed") }
    }
    static func run(plan:HubDiagnosticPlan,stage:String,authorized:Bool,backend:HubDiagnosticBackend,
                    journalWriter:((URL,[String:Any]) throws -> Void)? = nil) throws -> [String:Any] {
        guard ["race","roundtrip","cleanup"].contains(stage) else { throw HubDiagnosticError("invalid_stage") }
        guard authorized else { throw HubDiagnosticError("existing_full_access_required_no_prompt") }
        let journal = plan.path.deletingLastPathComponent().appendingPathComponent("diagnostic-state.json")
        let lockURL = try HubDiagnosticPlan.safe(plan.path.deletingLastPathComponent().appendingPathComponent(".diagnostic.lock").path)
        let fd = open(lockURL.path,O_CREAT|O_RDWR|O_NOFOLLOW,0o600)
        guard fd >= 0 else { throw HubDiagnosticError("diagnostic_lock_failed") }
        defer { close(fd) }
        guard flock(fd,LOCK_EX|LOCK_NB) == 0 else { throw HubDiagnosticError("diagnostic_already_running") }
        let ids = plan.records.map(\.id), parent = plan.records.first(where:{$0.role == "parent"})!
        let ordinary = plan.records.first(where:{$0.role == "ordinary"})!
        var state:[String:Any]
        if FileManager.default.fileExists(atPath:journal.path) {
            guard let existing = try JSONSerialization.jsonObject(with:HubDiagnosticPlan.bytes(journal)) as? [String:Any],
                  existing["plan_sha256"] as? String == plan.sha256,
                  let snapshots = existing["snapshots"] as? [String:[String:Any]], Set(snapshots.keys) == Set(ids),
                  existing["done"] is [String], existing["deleted"] is [String] else { throw HubDiagnosticError("invalid_diagnostic_journal") }
            state = existing
        } else {
            state = ["plan_sha256":plan.sha256,"operation_id":plan.operation,"snapshots":Dictionary(uniqueKeysWithValues:plan.records.map{($0.id,$0.snapshot)}),"done":[String](),"deleted":[String](),"results":[String:Any]()]
        }
        let writer = journalWriter ?? durable
        func save() throws { try writer(journal,state) }
        func snapshot(_ id:String)->[String:Any] { (state["snapshots"] as! [String:[String:Any]])[id]! }
        func remember(_ id:String,_ value:[String:Any]) {
            var snapshots = state["snapshots"] as! [String:[String:Any]]; snapshots[id] = HubDiagnosticPlan.normalized(value);state["snapshots"] = snapshots
        }
        func identity(_ value:[String:Any],_ record:HubDiagnosticRecord,deleted:Bool = false) throws {
            guard value["id"] as? String == record.id, value["title"] as? String == record.title,
                  (value["notes"] as? String)?.contains(plan.marker) == true, value["completed"] as? Bool != true,
                  deleted || (value["list_id"] as? String == HubDiagnosticPlan.listID && value["list"] as? String == HubDiagnosticPlan.listName && value["parent_id"] as? String == record.parentID) else { throw HubDiagnosticError("synthetic_identity_changed") }
        }
        func childrenSafe() throws {
            let actual = try backend.diagnosticChildren(parent.id,listID:HubDiagnosticPlan.listID)
            guard actual.isSubset(of:Set(ids.filter{$0 != parent.id})) else { throw HubDiagnosticError("foreign_child_blocks_diagnostic") }
            for record in plan.records where record.role != "parent" {
                guard try backend.diagnosticChildren(record.id,listID:HubDiagnosticPlan.listID).isEmpty else { throw HubDiagnosticError("target_has_children") }
            }
        }
        func inspect(_ record:HubDiagnosticRecord) throws -> (deleted:Bool,value:[String:Any]) {
            let deleted = try backend.diagnosticDeleted([record.id])
            guard Set(deleted.keys).isSubset(of:[record.id]) else { throw HubDiagnosticError("foreign_deleted_result") }
            if let value = deleted[record.id] { try identity(value,record,deleted:true); return (true,value) }
            let value = try backend.diagnosticSnapshot(record.id); try identity(value,record); return (false,value)
        }
        let pending = state["pending"] as? [String:String]
        // Весь пакет проверяется до первой записи или внешнего изменения.
        for record in plan.records {
            let actual = try inspect(record), expected = snapshot(record.id)
            if pending?["id"] == record.id {
                var raced = expected; raced["notes"] = ordinary.notes + "\n[diagnostic-race:"+plan.marker+"]"
                let allowed = HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actual.value,versions:false,deleted:actual.deleted),HubDiagnosticPlan.normalized(expected,versions:false,deleted:actual.deleted)) ||
                    (pending?["action"] == "race" && HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actual.value,versions:false,deleted:actual.deleted),HubDiagnosticPlan.normalized(raced,versions:false,deleted:actual.deleted)))
                guard allowed else { throw HubDiagnosticError("pending_snapshot_conflict") }
            } else {
                let expectedDeleted = (state["deleted"] as! [String]).contains(record.id)
                guard actual.deleted == expectedDeleted,
                      HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actual.value,versions:!actual.deleted,deleted:actual.deleted),HubDiagnosticPlan.normalized(expected,versions:!actual.deleted,deleted:actual.deleted)) else { throw HubDiagnosticError("snapshot_version_conflict") }
            }
        }
        try childrenSafe()
        let done = state["done"] as! [String]
        if done.contains(stage) { return (state["results"] as? [String:[String:Any]])?[stage] ?? ["ok":true,"stage":stage] }
        guard stage == "race" || done.contains("race") else { throw HubDiagnosticError("race_stage_required") }
        guard stage != "cleanup" || done.contains("roundtrip") else { throw HubDiagnosticError("roundtrip_stage_required") }
        try save()
        func intent(_ record:HubDiagnosticRecord,_ action:String) throws {
            state["pending"] = ["id":record.id,"action":action,"stage":stage]
            try save()
        }
        func verifyFields(_ record:HubDiagnosticRecord,_ actual:[String:Any],_ expected:[String:Any]) throws {
            try identity(actual,record)
            guard HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actual,versions:false),HubDiagnosticPlan.normalized(expected,versions:false)) else { throw HubDiagnosticError("roundtrip_fields_changed") }
        }
        func beforeMutation(_ record:HubDiagnosticRecord,_ expected:[String:Any],deleting:Bool) throws {
            try childrenSafe()
            let actual = try inspect(record)
            guard (!deleting || !actual.deleted),
                  HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actual.value,versions:deleting,deleted:actual.deleted),HubDiagnosticPlan.normalized(expected,versions:deleting,deleted:actual.deleted)) else { throw HubDiagnosticError("fresh_mutation_conflict") }
            if record.role != "parent" {
                let actualParent = try inspect(parent)
                guard !actualParent.deleted, HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(actualParent.value),snapshot(parent.id)) else { throw HubDiagnosticError("fresh_parent_conflict") }
            } else if deleting {
                guard try backend.diagnosticChildren(parent.id,listID:HubDiagnosticPlan.listID).isEmpty else { throw HubDiagnosticError("parent_not_leaf_at_cleanup") }
            }
        }
        func restore(_ record:HubDiagnosticRecord,_ expected:[String:Any]) throws {
            let actual = try inspect(record)
            if actual.deleted {
                try childrenSafe(); try intent(record,"restore")
                try beforeMutation(record,expected,deleting:false)
                try backend.diagnosticRestore(record.id,listID:HubDiagnosticPlan.listID,parentID:record.parentID)
            }
            let restored = try backend.diagnosticSnapshot(record.id)
            try verifyFields(record,restored,expected); remember(record.id,restored)
            state["deleted"] = (state["deleted"] as! [String]).filter{$0 != record.id}
            if stage == "roundtrip" { state["roundtrip_ids"] = Array(Set((state["roundtrip_ids"] as? [String] ?? [])+[record.id])) }
            state.removeValue(forKey:"pending"); try save()
        }
        var result:[String:Any] = ["ok":true,"stage":stage,"operation_id":plan.operation,"atomic_version_check":false,"production_enabled":false]
        if stage == "race" {
            let notes = ordinary.notes + "\n[diagnostic-race:"+plan.marker+"]"
            var expected = snapshot(ordinary.id); expected["notes"] = notes
            var race:[String:Any]
            if state["race_native"] != nil {
                race = state["race_native"] as! [String:Any]
            } else if pending?["action"] == "race" {
                let actual = try inspect(ordinary)
                guard actual.deleted || actual.value["notes"] as? String == notes else { throw HubDiagnosticError("race_outcome_unknown_no_retry") }
                race = ["stale_save_succeeded":actual.deleted,"competing_edit_saved":actual.value["notes"] as? String == notes,"interrupted":true]
            } else {
                try intent(ordinary,"race")
                try beforeMutation(ordinary,snapshot(ordinary.id),deleting:true)
                race = try backend.diagnosticRace(ordinary.id,notes:notes)
                state["race_native"] = race; try save()
            }
            // Отказ конкурентной гарантии фиксируется; удалённый UUID возвращается точным restore.
            let after = try inspect(ordinary)
            let preserved = after.value["notes"] as? String == notes
            if !preserved { expected["notes"] = after.value["notes"] }
            remember(ordinary.id,expected)
            state["race_native"] = race
            try save()
            try restore(ordinary,expected)
            result.merge(race){_,new in new};result["notes_preserved"] = preserved
            result["snapshot"] = snapshot(ordinary.id)
        } else if stage == "roundtrip" {
            for record in plan.records where record.role != "parent" {
                let completed = state["roundtrip_ids"] as? [String] ?? []
                if completed.contains(record.id) { continue }
                let expected = snapshot(record.id), actual = try inspect(record)
                let pendingRestore = (state["pending"] as? [String:String])?["action"] == "restore" && (state["pending"] as? [String:String])?["id"] == record.id
                if !actual.deleted && !pendingRestore {
                    try childrenSafe(); try intent(record,"delete")
                    try beforeMutation(record,expected,deleting:true)
                    try backend.diagnosticDelete(record.id)
                }
                if !pendingRestore || actual.deleted {
                    let deleted = try inspect(record)
                    guard deleted.deleted else { throw HubDiagnosticError("soft_delete_readback_failed") }
                    guard HubDiagnosticPlan.equal(HubDiagnosticPlan.normalized(deleted.value,versions:false,deleted:true),HubDiagnosticPlan.normalized(expected,versions:false,deleted:true)) else { throw HubDiagnosticError("deleted_fields_changed") }
                    state["deleted"] = Array(Set((state["deleted"] as! [String])+[record.id]));try save()
                }
                try restore(record,expected)
            }
            result["same_uuid_restore_verified"] = true
            result["snapshots"] = state["snapshots"]
        } else {
            // Только эти UUID. Родитель последним; повторная проверка детей не допускает каскад.
            for record in plan.records.sorted(by:{$0.role != "parent" && $1.role == "parent"}) {
                let actual = try inspect(record)
                if actual.deleted {
                    state["deleted"] = Array(Set((state["deleted"] as! [String])+[record.id]));state.removeValue(forKey:"pending");try save();continue
                }
                try childrenSafe(); try intent(record,"cleanup")
                try beforeMutation(record,snapshot(record.id),deleting:true)
                try backend.diagnosticDelete(record.id)
                guard try inspect(record).deleted else { throw HubDiagnosticError("cleanup_readback_failed") }
                state["deleted"] = Array(Set((state["deleted"] as! [String])+[record.id]));state.removeValue(forKey:"pending");try save()
            }
            result["deleted_ids"] = ids
        }
        state["done"] = done + [stage]
        var results = state["results"] as? [String:[String:Any]] ?? [:];results[stage] = result;state["results"] = results
        state.removeValue(forKey:"pending");try save();return result
    }
}
