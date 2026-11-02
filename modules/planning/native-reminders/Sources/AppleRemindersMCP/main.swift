import Agents
import EventKit
import Foundation
import Launcher
import Wire

let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev"
let words = Array(CommandLine.arguments.dropFirst())

/// What to do, by the first word: `--stdio` (or, with no words, input from a pipe or socket)
/// serves MCP; `setup` asks for the Reminders permission in the terminal; `--self-check` prints a
/// diagnosis; `agents` lists, sets up and installs AI agents; `skill` prints the skill;
/// `--settings` (or, with no words, a double-click in Finder) opens the settings window; anything
/// else is a command (see Commands). Only the first word counts, so a reminder may be called setup.
enum Mode { case serve, setup, check, agents, skill, version, settings, command, diagnostic }

let mode: Mode = {
    switch words.first {
    case "hub-cancellation-diagnostic": return .diagnostic
    case "--stdio": return .serve
    case "setup", "authorize": return .setup
    case "--self-check": return .check
    case "agents": return .agents
    case "skill": return .skill
    case "--version": return .version
    case "--settings": return .settings
    case nil:
        var info = stat()
        fstat(STDIN_FILENO, &info)
        let kind = info.st_mode & S_IFMT
        return kind == S_IFIFO || kind == S_IFSOCK ? .serve : .settings
    default: return .command
    }
}()

let diagnosticBundleID = "com.xiaofeng.apple-reminders-mcp.hub-cancellation-diagnostic"
let executorBundleID = "com.xiaofeng.apple-reminders-mcp.hub-cancellation-executor"
let isDiagnosticIdentity = Bundle.main.bundleIdentifier == diagnosticBundleID
let isExecutorIdentity = Bundle.main.bundleIdentifier == executorBundleID
if isDiagnosticIdentity {
    switch mode {
    case .diagnostic, .setup, .version: break
    default:
        fputs("Diagnostic app only supports its diagnostic, setup, and version commands.\n", stderr)
        exit(1)
    }
}
if isExecutorIdentity {
    switch mode {
    case .setup, .version: break
    case .command where words.first == "call" && words.count >= 2 &&
        Set(["hub_cancel_capabilities", "hub_cancel_status", "hub_cancel_reminder", "hub_restore_reminder"]).contains(words[1]): break
    default:
        fputs("Hub cancellation executor only supports setup, version, and four exact call tools.\n", stderr)
        exit(1)
    }
}

// Only the app bundle has an identity worth holding the Reminders permission; a bare build runs
// with whatever started it.
if Bundle.main.bundleIdentifier == "com.xiaofeng.apple-reminders-mcp" || isDiagnosticIdentity || isExecutorIdentity {
    launcher_become_responsible("APPLE_REMINDERS_MCP_RELAUNCHED")
}
setvbuf(stdout, nil, _IOLBF, 0)

func describe(_ status: EKAuthorizationStatus) -> String {
    switch status {
    case .fullAccess: "full access"
    case .notDetermined: "not asked yet"
    case .denied: "denied"
    case .restricted: "restricted"
    case .writeOnly: "write only"
    @unknown default: "unknown (\(status.rawValue))"
    }
}

let writeGuard: Set<String>
do { writeGuard = isExecutorIdentity && (mode == .setup || mode == .version) ? [] : try loadHubAllowedLists() }
catch {
    fputs("Allowed lists configuration rejected: \(error)\n", stderr)
    exit(1)
}
if mode == .agents || mode == .settings || mode == .check || mode == .serve {
    fputs("This restricted Hub build only supports explicit CLI commands and setup.\n", stderr)
    exit(1)
}
/// Строгая граница до обработки параметров инструментами.
func hubAllowsOrganization(_ tool: String, _ arguments: [String: JSON], lists: Set<String>, groups: Set<String>) -> Bool {
    let keys = Set(arguments.keys)
    if tool == "manage_group" {
        return keys == ["action", "group"] && arguments["action"]?.string == "create"
            && arguments["group"]?.string.map(groups.contains) == true
    }
    if tool == "manage_list" {
        if arguments["action"]?.string == "create" {
            let guarded = keys == ["action", "list", "expected_account_id"]
                && arguments["expected_account_id"]?.string.flatMap(UUID.init(uuidString:)) != nil
            return (keys == ["action", "list"] || guarded) && arguments["list"]?.string.map(lists.contains) == true
        }
        if keys.contains("new_name") || keys.contains("expected_name") {
            let names = [arguments["expected_name"]?.string, arguments["new_name"]?.string]
            return keys == ["action", "list", "expected_name", "new_name", "expected_account_id", "expected_group_id"]
                && arguments["action"]?.string == "update"
                && arguments["list"]?.string.flatMap(UUID.init(uuidString:)) != nil
                && arguments["expected_account_id"]?.string.flatMap(UUID.init(uuidString:)) != nil
                && (arguments["expected_group_id"] == .null || arguments["expected_group_id"]?.string.flatMap(UUID.init(uuidString:)) != nil)
                && names.allSatisfy { name in
                    guard let name else { return false }
                    return !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        && name.rangeOfCharacter(from: .newlines) == nil && lists.contains(name)
                } && names[0] != names[1]
        }
        let withExpected = keys == ["action", "list", "group", "expected_group_id"]
        let validExpected = arguments["expected_group_id"] == .null || arguments["expected_group_id"]?.string.flatMap(UUID.init(uuidString:)) != nil
        return (keys == ["action", "list", "group"] || (withExpected && validExpected)) && arguments["action"]?.string == "update"
            && arguments["list"]?.string.flatMap(UUID.init(uuidString:)) != nil
            && (arguments["group"] == .null || arguments["group"]?.string.flatMap(UUID.init(uuidString:)) != nil) && !groups.isEmpty
    }
    return true
}

let store = RemindersStore(writeGuard: writeGuard)
/// What the server offers and the commands run.
let allowedNames: Set<String> = ["create_reminder", "update_reminder", "get_reminder", "find_reminders", "manage_list", "manage_group", "list_lists"]
let standardTools = (readTools(store) + writeTools(store) + organizeTools(store)).filter { allowedNames.contains($0.name) }.map { tool in
    Tool(tool.name, title: tool.title, summary: tool.summary, input: tool.input, effect: tool.effect) { arguments in
        guard hubAllowsOrganization(tool.name, arguments, lists: writeGuard, groups: store.groupWriteGuard) else {
            return ToolAnswer("Organization operation is outside explicit Hub permissions.", failed: true)
        }
        let restricted: Set<String> = ["add_images", "remove_images", "location", "when_messaging", "assigned_to", "urgent", "url", "tags", "early_alerts", "smart_list"]
        guard restricted.isDisjoint(with: arguments.keys) else {
            return ToolAnswer("Field disabled in restricted Hub build.", failed: true)
        }
        return try await tool.run(arguments)
    }
}
let tools = isExecutorIdentity ? HubCancellationTools.tools(store) : standardTools

/// Runs `work` on the main actor and exits with what it returns. The top-level code itself stays
/// synchronous: async top-level code runs as one long job on the main queue, and the settings
/// window's event loop inside it would keep every other main-actor task from running.
func runThenExit(_ work: @escaping @MainActor () async -> Int32) -> Never {
    Task { @MainActor in exit(await work()) }
    dispatchMain()
}

switch mode {
case .diagnostic:
    do {
        let arguments = Array(words.dropFirst())
        guard arguments.count == 6, arguments[0] == "--plan", arguments[2] == "--sha256", arguments[4] == "--stage" else {
            throw HubDiagnosticError("Expected --plan PATH --sha256 HASH --stage race|roundtrip|cleanup")
        }
        let plan = try HubDiagnosticPlan.load(path:arguments[1],sha256:arguments[3])
        let existingAccess = EKEventStore.authorizationStatus(for:.reminder) == .fullAccess
        let result = try HubCancellationDiagnostic.run(plan:plan,stage:arguments[5],authorized:existingAccess,backend:store)
        let data = try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys,.prettyPrinted])
        print(String(decoding:data,as:UTF8.self));exit(0)
    } catch {
        // Только общий код ошибки: содержимое чужих объектов не печатается.
        let message = (error as? HubDiagnosticError)?.description ?? "diagnostic_native_or_journal_error"
        let data = try! JSONSerialization.data(withJSONObject:["ok":false,"error":message],options:[.sortedKeys])
        print(String(decoding:data,as:UTF8.self));exit(1)
    }
case .setup:
    runThenExit {
        let status = EKEventStore.authorizationStatus(for: .reminder)
        print("Reminders access:", describe(status))
        if status == .notDetermined {
            print("Asking for access; click Allow in the dialog (it may be behind other windows).")
            let granted = (try? await EKEventStore().requestFullAccessToReminders()) ?? false
            print(granted ? "Access granted." : "Access was not granted.")
        } else if status != .fullAccess {
            print(RemindersStore.permissionHelp)
        }
        return EKEventStore.authorizationStatus(for: .reminder) == .fullAccess ? 0 : 1
    }

case .check:
    print("Apple Reminders MCP \(version) (\(Bundle.main.bundleIdentifier ?? "development build"))")
    print("Reminders access:", describe(EKEventStore.authorizationStatus(for: .reminder)))
    if launcher_is_sandboxed() != 0 { print("Sandbox: yes, so macOS keeps Reminders out of reach; run this outside the sandbox") }
    if EKEventStore.authorizationStatus(for: .reminder) == .fullAccess {
        do {
            let lists = try store.lists()
            let total = try lists.reduce(0) { $0 + (try store.reminders(in: $1.id).count) }
            print("Reminders data: OK, \(total) reminders in \(lists.count) lists")
        } catch {
            print("Reminders data:", error)
        }
    }
    print("Full Disk Access (optional):", DeletedDatabase.available ? "yes" : "no")
    print("Agents may complete repeating reminders:", Settings.allowCompletingRecurring ? "yes" : "no")
    if Settings.toolsFileOverride != nil {
        print("Tools file:", Settings.exposure.file.path, "(from APPLE_REMINDERS_MCP_TOOLS_FILE)")
    }
    do {
        let offered = Set(try Settings.exposure.offered(tools).map(\.name))
        let off = tools.map(\.name).filter { !offered.contains($0) }.sorted()
        print("Tools offered to AI assistants: \(offered.count) of \(tools.count)" + (off.isEmpty ? "" : " (turned off: \(off.joined(separator: ", ")))"))
    } catch {
        print("Tools offered to AI assistants: none, \(Settings.exposure.file.path) can't be read (\(error))")
    }
    print("Write guard:", writeGuard.sorted().joined(separator: ", "))
    exit(0)

case .agents:
    runThenExit { await AgentsCommand.run(Array(words.dropFirst())) }

case .skill:
    print(Skill.text(for: Installation.detect()), terminator: "")
    exit(0)

case .version:
    print("apple-reminders-mcp \(version)")
    exit(0)

case .command:
    if isExecutorIdentity && EKEventStore.authorizationStatus(for: .reminder) != .fullAccess {
        fputs("existing_full_access_required_no_prompt\n", stderr)
        exit(1)
    }
    runThenExit { await Commands.run(words, tools: tools) }

case .settings:
    SettingsPanel.show(tools: tools)
    exit(0)

case .serve:
    let instructions = """
        Apple Reminders on this Mac, synced through iCloud to the user's devices. find_reminders and \
        list_lists read; pass a reminder's id and version to update_reminder or delete_reminder. Times are \
        local to \(TimeZone.current.identifier): due and start take 2026-10-21 (all day) or 2026-10-21T09:00, \
        and a due time adds an alert then. urgent makes that alert ring like an alarm and needs a due time; \
        repeat and early_alerts need a due date. Tags are native, written without #. Subtasks are one level \
        deep (parent_id); sections divide a list. Lists marked shared are seen by other people: confirm \
        with the user before adding to or changing them, and assign with assigned_to. Deleted reminders \
        go to Recently Deleted; list_deleted and restore_reminder bring them back.
        """
    let service = Service(name: "apple-reminders-mcp", version: version, instructions: instructions,
                          tools: tools, exposure: Settings.exposure)
    runThenExit {
        await StdioServer.run(service)
        return 0
    }
}
