import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "read-compact-project-index.sh"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_hub(tmp, entries):
    """entries: list of (project_id, status, primary_archiproject|None)."""
    hub = Path(tmp) / "_ai-hub"
    rows = []
    for project_id, status, _primary in entries:
        rows.append(
            f"## {project_id}\nName: {project_id.title()}\nTags: fixture\nStatus: {status}\n"
        )
    write(hub / "ai" / "project-registry.md", "# Project Registry\n\n" + "\n".join(rows))
    for project_id, _status, primary in entries:
        lines = [
            "# Project Card",
            f"Project ID: {project_id}",
            f"Name: {project_id.title()}",
            "Purpose: fixture purpose.",
        ]
        if primary is not None:
            lines.append(f"primary_archiproject: {primary}")
        write(hub / "ai" / "project-cards" / f"{project_id}.md", "\n".join(lines) + "\n")
    return hub


class CompactProjectIndexGroupColumnTests(unittest.TestCase):
    def run_index(self, hub):
        return subprocess.run(
            ["bash", str(SCRIPT), str(hub)], text=True, capture_output=True,
        )

    def test_header_has_six_columns_including_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(tmp, [("alpha", "active", "top")])
            result = self.run_index(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            header = lines[0].split("\t")
            self.assertEqual(
                header,
                ["project_id", "name", "tags", "status", "purpose_brief", "group"],
            )

    def test_group_column_reflects_card_primary_archiproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(
                tmp,
                [
                    ("alpha", "active", "top"),
                    ("beta", "active", "none"),
                ],
            )
            result = self.run_index(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = {}
            for line in result.stdout.splitlines()[1:]:
                fields = line.split("\t")
                rows[fields[0]] = fields[5]
            self.assertEqual(rows["alpha"], "top")
            self.assertEqual(rows["beta"], "none")

    def test_card_without_primary_archiproject_field_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(tmp, [("alpha", "active", None)])
            result = self.run_index(hub)
            self.assertEqual(result.returncode, 0, result.stderr)
            fields = result.stdout.splitlines()[1].split("\t")
            self.assertEqual(fields[5], "none")


if __name__ == "__main__":
    unittest.main()
