import Testing
import Wire
@testable import AppleRemindersMCP

struct ListSharingTests {
    @Test func explicitSharingState() {
        for shared in [false, true] {
            let list = ListInfo(["id": "test-list", "name": "Тест", "shared": shared])
            let value = Output.list(list, groups: [])
            #expect(value["shared"] == .bool(shared))
            #expect((value["people"] != nil) == shared)
        }
    }
}
