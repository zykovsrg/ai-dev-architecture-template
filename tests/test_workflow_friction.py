import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from scripts import workflow_friction
from scripts.workflow_friction import list_pending, resolve


def _resolve_with_replace_barrier(hub, day, source_sha, identifier, decision, barrier):
    original_replace = workflow_friction.os.replace

    def delayed_replace(source, destination):
        try:
            barrier.wait(timeout=1.0)
        except Exception:
            pass
        original_replace(source, destination)

    workflow_friction.os.replace = delayed_replace
    resolve(Path(hub), day, source_sha, identifier, decision)


class WorkflowFrictionTests(unittest.TestCase):
    def test_unresolved_source_survives_a_list_and_resolves_once(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            source = hub / "ai" / "tmp" / "workflow-friction"
            source.mkdir(parents=True)
            source.joinpath("2026-09-09.txt").write_text("first\nsecond\n", encoding="utf-8")
            pending = list_pending(hub, "2026-09-09")
            self.assertEqual(len(pending["entries"]), 2)
            resolve(hub, "2026-09-09", pending["source_sha256"], pending["entries"][0]["id"], "accepted")
            again = list_pending(hub, "2026-09-09")
            self.assertEqual([item["text"] for item in again["entries"]], ["second"])
            self.assertTrue(source.joinpath("2026-09-09.txt").exists())

    def test_stale_source_cannot_be_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            source = hub / "ai" / "tmp" / "workflow-friction"
            source.mkdir(parents=True)
            file = source / "2026-09-09.txt"
            file.write_text("first\n", encoding="utf-8")
            pending = list_pending(hub, "2026-09-09")
            file.write_text("changed\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                resolve(hub, "2026-09-09", pending["source_sha256"], pending["entries"][0]["id"], "accepted")

    def test_source_symlink_outside_hub_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = root / "hub"
            cache = hub / "ai" / "tmp" / "workflow-friction"
            cache.mkdir(parents=True)
            outside = root / "outside.txt"
            outside.write_text("secret\n", encoding="utf-8")
            cache.joinpath("2026-09-09.txt").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "source must not be a symlink"):
                list_pending(hub, "2026-09-09")

    def test_intermediate_cache_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = root / "hub"
            (hub / "ai").mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (hub / "ai" / "tmp").symlink_to(outside, target_is_directory=True)
            cache = outside / "workflow-friction"
            cache.mkdir()
            cache.joinpath("2026-09-09.txt").write_text("secret\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "cache path must not contain symlinks"):
                list_pending(hub, "2026-09-09")

    def test_state_symlink_outside_hub_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hub = root / "hub"
            cache = hub / "ai" / "tmp" / "workflow-friction"
            cache.mkdir(parents=True)
            cache.joinpath("2026-09-09.txt").write_text("first\n", encoding="utf-8")
            outside = root / "outside-state.json"
            outside.write_text('{"format":1,"entries":{}}', encoding="utf-8")
            cache.joinpath("2026-09-09.state.json").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "state must not be a symlink"):
                list_pending(hub, "2026-09-09")

    def test_concurrent_resolve_preserves_both_dispositions(self):
        try:
            context = multiprocessing.get_context("fork")
        except ValueError:
            self.skipTest("controlled interleaving requires fork")
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            cache = hub / "ai" / "tmp" / "workflow-friction"
            cache.mkdir(parents=True)
            cache.joinpath("2026-09-09.txt").write_text("first\nsecond\n", encoding="utf-8")
            pending = list_pending(hub, "2026-09-09")
            barrier = context.Barrier(2)
            processes = []
            decisions = ("accepted", "rejected")
            for entry, decision in zip(pending["entries"], decisions):
                process = context.Process(
                    target=_resolve_with_replace_barrier,
                    args=(str(hub), "2026-09-09", pending["source_sha256"], entry["id"], decision, barrier),
                )
                process.start()
                processes.append(process)
            for process in processes:
                process.join(5)
                self.assertEqual(process.exitcode, 0)

            state = json.loads(cache.joinpath("2026-09-09.state.json").read_text(encoding="utf-8"))
            self.assertEqual(set(state["entries"]), {entry["id"] for entry in pending["entries"]})
            self.assertEqual(state["entries"][pending["entries"][0]["id"]]["disposition"], "accepted")
            self.assertEqual(state["entries"][pending["entries"][1]["id"]]["disposition"], "rejected")


if __name__ == "__main__":
    unittest.main()
