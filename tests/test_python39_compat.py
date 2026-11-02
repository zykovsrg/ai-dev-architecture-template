"""Installed Hub scripts must run on the macOS system Python 3.9."""

import ast
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports
from scripts.python_compat import has_union_annotation, offenders, postpones_annotations

ROOT = Path(__file__).resolve().parents[1]


class Python39CompatTests(unittest.TestCase):
    def test_union_annotations_are_postponed(self):
        passports = load_passports(ROOT)
        sources = [source for source, _ in install_pairs(ROOT, passports, list(passports))]
        self.assertEqual(offenders(ROOT, sources), [])

    def test_detector_catches_any_union(self):
        for code in ("def f(x: str | int): pass", "def f() -> list[str] | None: pass", "x: int | str = 1"):
            self.assertTrue(has_union_annotation(ast.parse(code)), code)
        self.assertFalse(has_union_annotation(ast.parse("y = 1 | 2")))
        self.assertTrue(postpones_annotations(ast.parse("from __future__ import annotations\n")))


if __name__ == "__main__":
    unittest.main()
