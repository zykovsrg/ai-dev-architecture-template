# Truthfulness Instructions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consistent truthfulness and intellectual-rigor instructions to the active project files and Hub templates.

**Architecture:** Four Markdown instruction files receive the same four-rule section. The active project files keep their project-entry structure; the templates place the section within their existing core-principles area. A read-only comparison verifies that all files contain the required wording.

**Tech Stack:** Markdown, Git, `rg`.

## Global Constraints

- Add the exact four English rules approved in `docs/superpowers/archive/specs/2026-09-22-truthfulness-instructions-design.md`.
- Preserve all existing instructions outside the added section.
- Do not modify files outside the four instruction files and this plan's normal Git metadata.

---

### Task 1: Add truthfulness rules to the active project instructions

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Test: read-only `rg` checks against both files

**Interfaces:**
- Consumes: the approved four-rule block in `docs/superpowers/archive/specs/2026-09-22-truthfulness-instructions-design.md`
- Produces: identical `## Truthfulness and Intellectual Rigor` sections in both active project entry files

- [x] **Step 1: Add the section after the introductory Hub-management paragraph in each file**

```md
## Truthfulness and Intellectual Rigor

- Treat all information as potentially fallible: question it and verify material claims using appropriate evidence.
- Put truth above agreement with the user. Do not agree merely to provide comfort, validation, or approval.
- If the user is wrong, an assumption is unsupported, or a conclusion does not follow from the facts, say so immediately—directly, clearly, and without sugarcoating.
- Act as a rational, constructive intellectual partner. Separate verified facts from inference and state uncertainty explicitly.
```

- [x] **Step 2: Verify both files contain the exact section once**

Run: `rg -n -F '## Truthfulness and Intellectual Rigor' AGENTS.md CLAUDE.md`

Expected: one match in `AGENTS.md` and one match in `CLAUDE.md`.

- [x] **Step 3: Commit the active-instructions change**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "docs: add truthfulness instructions"
```

### Task 2: Add truthfulness rules to the Hub instruction templates

**Files:**
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Test: read-only `rg` checks against both files

**Interfaces:**
- Consumes: the same approved four-rule block
- Produces: identical `## Truthfulness and Intellectual Rigor` sections in both Hub templates

- [x] **Step 1: Add the section after `## Core Principles` in each template**

```md
## Truthfulness and Intellectual Rigor

- Treat all information as potentially fallible: question it and verify material claims using appropriate evidence.
- Put truth above agreement with the user. Do not agree merely to provide comfort, validation, or approval.
- If the user is wrong, an assumption is unsupported, or a conclusion does not follow from the facts, say so immediately—directly, clearly, and without sugarcoating.
- Act as a rational, constructive intellectual partner. Separate verified facts from inference and state uncertainty explicitly.
```

- [x] **Step 2: Verify the required heading appears once in each of all four files**

Run: `rg -n -F '## Truthfulness and Intellectual Rigor' AGENTS.md CLAUDE.md hub-template/AGENTS.md hub-template/CLAUDE.md`

Expected: four matches, one per file.

- [x] **Step 3: Verify no unrelated whitespace errors were introduced**

Run: `git diff --check`

Expected: no output and exit code 0.

- [x] **Step 4: Commit the template-instructions change**

```bash
git add hub-template/AGENTS.md hub-template/CLAUDE.md
git commit -m "docs: add truthfulness template instructions"
```
