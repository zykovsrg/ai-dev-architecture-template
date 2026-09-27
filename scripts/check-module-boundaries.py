#!/usr/bin/env python3
"""Warn when a module's installed files reference a module it may not depend on."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_passports import install_pairs, load_passports  # noqa: E402

# Always-installed modules can never be missing, so anyone may reference them.
ALWAYS_INSTALLED = {"core", "projects", "tasks"}
GENERIC = {"SKILL.md", ".gitkeep", "module.md", "README.md", "rules.md"}


def module_tokens(root, passports, module_id):
    tokens = {(k, True) for k in passports[module_id].keywords}
    for _, target in install_pairs(root, passports, [module_id]):
        parts = Path(target).parts
        if len(parts) >= 3 and parts[:2] == ("ai", "skills"):
            tokens.add((parts[2], False))
        elif parts[-1] not in GENERIC:
            tokens.add((parts[-1], False))
    return tokens


def find_violations(root):
    root = Path(root)
    passports = load_passports(root)
    tokens = {i: module_tokens(root, passports, i) for i in passports}
    violations = set()
    for module_id, passport in passports.items():
        allowed = {module_id, *ALWAYS_INSTALLED, *passport.depends, *passport.uses_if_present}
        for source, _ in install_pairs(root, passports, [module_id]):
            text = (root / source).read_text(encoding="utf-8", errors="replace")
            for other, other_tokens in tokens.items():
                if other in allowed:
                    continue
                for token, keyword in other_tokens:
                    pattern = r"(?<![A-Za-z0-9_.-])" + re.escape(token) + r"(?![A-Za-z0-9_-])"
                    if re.search(pattern, text, re.I if keyword else 0):
                        violations.add((source, other, token))
    return sorted(violations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    violations = find_violations(args.source)
    for source, other, token in violations:
        print(f"WARN {source}: {other} via {token}")
    print(f"module boundaries: {len(violations)} warning(s)")
    return 1 if args.strict and violations else 0


if __name__ == "__main__":
    sys.exit(main())
