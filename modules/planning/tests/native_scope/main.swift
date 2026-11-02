import Foundation
let args = CommandLine.arguments
do {
    _ = try HubCancellationScope.load(path: args[2], sha: args[3], id: args[4], mutation: args[5] == "mutation", approvedRoot: args[1])
    print("ok")
} catch { fputs("\(error)\n", stderr); exit(1) }
