"""Installed Hub scripts must run on the macOS system Python 3.9."""

import ast
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]


def has_union_annotation(tree):
    annotations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
                if arg is not None and arg.annotation is not None:
                    annotations.append(arg.annotation)
            if node.returns is not None:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
    return any(
        isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr)
        for annotation in annotations
        for sub in ast.walk(annotation)
    )


def postpones_annotations(tree):
    return any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def offenders(root, sources):
    found = []
    for source in sources:
        path = root / source
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if has_union_annotation(tree) and not postpones_annotations(tree):
            found.append(str(source))
    return found


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
