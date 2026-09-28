"""Installed Hub scripts must run on the macOS system Python 3.9."""

import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
PEP604 = re.compile(r"[\w\]]\s*\|\s*None\b|\bNone\s*\|\s*\w")


class Python39CompatTests(unittest.TestCase):
    def test_pep604_annotations_are_postponed(self):
        passports = load_passports(ROOT)
        offenders = []
        for source, _ in install_pairs(ROOT, passports, list(passports)):
            path = ROOT / source
            if path.suffix != ".py" or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if PEP604.search(text) and "from __future__ import annotations" not in text:
                offenders.append(str(source))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
