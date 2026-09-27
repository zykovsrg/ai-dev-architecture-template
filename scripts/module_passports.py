#!/usr/bin/env python3
"""Read module passports (modules/<id>/module.md) with the standard library only."""

import re
from dataclasses import dataclass, field
from pathlib import Path

EVENTS = (
    "after-task-write",
    "before-task-confirmation",
    "after-calendar-change",
    "before-task-close",
    "after-project-create",
)
HEADERS = {"Id", "Required", "Switchable", "Depends", "Uses if present", "Rules", "Keywords"}
SECTIONS = {"Purpose", "Installs", "Repository only", "Reads", "Writes", "Subscribes"}
EMPTY = "—"


@dataclass
class Passport:
    id: str
    required: bool
    switchable: bool
    depends: list = field(default_factory=list)
    uses_if_present: list = field(default_factory=list)
    rules: object = None
    keywords: list = field(default_factory=list)
    installs: list = field(default_factory=list)
    repo_only: list = field(default_factory=list)
    subscribes: dict = field(default_factory=dict)
    purpose: str = ""


def _items(value):
    value = value.strip()
    return [] if value in ("", EMPTY) else [part.strip() for part in value.split(",")]


def _flag(value, name, path):
    if value not in ("yes", "no"):
        raise ValueError(f"{path}: {name} must be yes or no")
    return value == "yes"


def parse_passport(path):
    path = Path(path)
    headers, sections, current = {}, {name: [] for name in SECTIONS}, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            if current not in SECTIONS:
                raise ValueError(f"{path}: unknown section {current}")
            continue
        if current is None:
            match = re.match(r"^([A-Za-z ]+):\s*(.*)$", line)
            if match and match.group(1) in HEADERS:
                headers[match.group(1)] = match.group(2).strip()
            continue
        sections[current].append(line)
    if "Id" not in headers:
        raise ValueError(f"{path}: missing Id")

    def bullets(name):
        out = []
        for line in sections[name]:
            if line.startswith("- "):
                item = line[2:].strip()
                if item != EMPTY:
                    out.append(item)
        return out

    installs = []
    for item in bullets("Installs"):
        if " -> " not in item:
            raise ValueError(f"{path}: install line needs 'source -> target': {item}")
        source, target = (part.strip().strip("`") for part in item.split(" -> ", 1))
        if target.startswith(".local/") or (
            target.startswith("projects/") and target != "projects/.gitkeep"
        ):
            raise ValueError(f"{path}: install target must not touch {target!r}")
        installs.append((source, target))
    subscribes = {}
    for item in bullets("Subscribes"):
        event, _, command = item.partition(":")
        if event.strip() not in EVENTS or not command.strip():
            raise ValueError(f"{path}: bad subscription {item}")
        subscribes[event.strip()] = command.strip().strip("`")
    rules = headers.get("Rules", EMPTY)
    return Passport(
        id=headers["Id"],
        required=_flag(headers.get("Required", "no"), "Required", path),
        switchable=_flag(headers.get("Switchable", "no"), "Switchable", path),
        depends=_items(headers.get("Depends", EMPTY)),
        uses_if_present=_items(headers.get("Uses if present", EMPTY)),
        rules=None if rules == EMPTY else rules.strip("`"),
        keywords=_items(headers.get("Keywords", EMPTY)),
        installs=installs,
        repo_only=[item.strip("`") for item in bullets("Repository only")],
        subscribes=subscribes,
        purpose="\n".join(sections["Purpose"]).strip(),
    )


def load_passports(root):
    passports = {}
    for path in sorted(Path(root).glob("modules/*/module.md")):
        passport = parse_passport(path)
        if passport.id != path.parent.name:
            raise ValueError(f"{path}: Id {passport.id} differs from folder")
        passports[passport.id] = passport
    return passports


def install_pairs(root, passports, selected):
    root = Path(root)
    pairs = []
    for module_id in selected:
        for source, target in passports[module_id].installs:
            if source.endswith("/"):
                base = root / source
                if not base.is_dir():
                    raise ValueError(f"missing install directory: {source}")
                for path in sorted(base.rglob("*")):
                    if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                        continue
                    rel = path.relative_to(base).as_posix()
                    pairs.append((source + rel, target + rel))
            else:
                if not (root / source).is_file():
                    raise ValueError(f"missing install file: {source}")
                pairs.append((source, target))
    return sorted(pairs)


def installable(passports):
    return sorted(i for i, p in passports.items() if p.installs)


def resolve_selection(passports, previous, with_, without):
    for module_id in list(with_) + list(without):
        if module_id not in passports:
            raise ValueError(f"unknown module: {module_id}")
        if not passports[module_id].switchable:
            raise ValueError(f"module cannot be switched: {module_id}")
    available = set(installable(passports))
    chosen = available if previous is None else set(previous) & available
    chosen |= {i for i, p in passports.items() if p.required}
    chosen = (chosen | set(with_)) - set(without)
    for module_id in sorted(chosen):
        for dep in passports[module_id].depends:
            if dep not in chosen:
                raise ValueError(f"module {module_id} requires {dep}")
    return sorted(chosen)


def _skill_names(passports, module_id, root):
    names = set()
    if root is not None:
        for _, target in install_pairs(root, passports, [module_id]):
            if target.startswith("ai/skills/"):
                first = target[len("ai/skills/"):].split("/", 1)[0]
                if first:
                    names.add(first)
    else:
        for _, target in passports[module_id].installs:
            if target.startswith("ai/skills/"):
                rest = target[len("ai/skills/"):].rstrip("/")
                if rest:
                    names.add(rest.split("/", 1)[0])
    return sorted(names)


def render_modules_md(passports, selected, root=None):
    lines = ["# Installed Modules", "",
             "Generated by the Hub installer from module passports. Do not edit.", "",
             "## Modules", ""]
    for module_id in selected:
        rules = passports[module_id].rules
        lines.append(f"- {module_id}" + (f" — rules: `{rules}`" if rules else ""))
    lines += ["", "## Skills", ""]
    for module_id in sorted(selected):
        skills = _skill_names(passports, module_id, root)
        if skills:
            lines.append(f"- {module_id}: " + ", ".join(f"`{s}`" for s in skills))
    lines += ["", "## Events", ""]
    for event in EVENTS:
        lines += [f"### {event}", ""]
        subscribers = [i for i in selected if event in passports[i].subscribes]
        for module_id in subscribers:
            p = passports[module_id]
            suffix = f" — rules: `{p.rules}`" if p.rules else ""
            lines.append(f"- {module_id}: `{p.subscribes[event]}`{suffix}")
        if not subscribers:
            lines.append(f"- {EMPTY}")
        lines.append("")
    return "\n".join(lines)
