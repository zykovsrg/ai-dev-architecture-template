# Knowledge Layer Provenance and Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provenance, effective-date, and safe weak-signal inbox support to standalone and hub knowledge scaffolds.

**Architecture:** Durable records remain in four categories and gain required `origin` plus optional `valid_from`. `knowledge/inbox/` is only for `origin: observation`; capture and review retain exact confirmation for every mutation. Hub project creation and enablement create the same directory.

**Tech Stack:** Markdown templates and skills; Bash contract tests.

## Global Constraints

- `origin`: exactly `stated`, `inferred`, or `observation`; never default it.
- `valid_from`: `null` or real `YYYY-MM-DD`.
- Inbox is not a durable category; retain all existing safety and containment rules.

---

### Task 1: Add failing standalone contract tests

**Files:** Modify `scripts/smoke-test.sh:44-83` and `scripts/smoke-test.sh:198-250`.

- [ ] Require `$PROJECT/knowledge/inbox`, `origin: stated`, and `valid_from: null` after installation.
- [ ] Extend capture contract assertions with `explicit \`origin\` choice`, `must not default to \`stated\``, `origin: observation`, and `knowledge/inbox/`.
- [ ] Extend review assertions with `` `origin` and `valid_from` ``, `origin: inferred`, `observation outside the inbox`, and `promote it into one selected durable category`.
- [ ] Run `bash scripts/smoke-test.sh`; expect failure before implementation.
- [ ] Create temporary skill copies below `$TMP_DIR`, remove each new required phrase with `sed`, and prove `assert_rejected` catches every missing guard.
- [ ] Commit: `git add scripts/smoke-test.sh && git commit -m "test: require knowledge provenance and inbox contracts"`.

### Task 2: Implement standalone format and workflows

**Files:** Modify `knowledge/record-template.md`, `template/knowledge/record-template.md`, `knowledge/README.md`, `template/knowledge/README.md`, both `ai/skills/knowledge-capture/SKILL.md` copies, and both `ai/skills/knowledge-review/SKILL.md` copies.

- [ ] Insert this exact frontmatter after `status` in both templates:

```yaml
origin: stated
valid_from: null
```

- [ ] In both READMEs, define the three origins, `valid_from`, and inbox as a temporary holding area; explicitly retain the four durable categories.
- [ ] In capture, require an explicit origin before confirmation; allow `observation` only under `knowledge/inbox/`; allow `stated` and `inferred` only under the selected durable category.
- [ ] In review, validate both new fields, group inferred separately, flag observations outside inbox, and propose only promote/retain/delete for an explicit inbox scope.
- [ ] Verify with `cmp -s` for all four root/template pairs, then run `bash scripts/smoke-test.sh`; expect success.
- [ ] Commit: `git add knowledge template/knowledge ai/skills/knowledge-capture template/ai/skills/knowledge-capture ai/skills/knowledge-review template/ai/skills/knowledge-review && git commit -m "feat: add knowledge provenance and inbox"`.

### Task 3: Add inbox to hub scaffolding

**Files:** Modify `hub-template/ai/architecture.md:99-107`, `hub-template/ai/skills/hub-project-create/SKILL.md:75-150`, `hub-template/ai/skills/hub-knowledge-enable/SKILL.md:18-92`, and `scripts/hub-smoke-test.sh:289-327`.

- [ ] Add `[[ "$text" == *'knowledge/inbox/'* ]]` to both hub scaffold validators; run `bash scripts/hub-smoke-test.sh` and expect failure first.
- [ ] Add inbox to architecture, project-create preview, confirmed procedure, and canonical scaffold. State it is not a fifth durable category.
- [ ] Add inbox to `hub-knowledge-enable` lstat checks, preview, and absent-path creation list, preserving no-read/no-overwrite rules.
- [ ] Run `bash scripts/check-consistency.sh && bash scripts/hub-smoke-test.sh`; expect success.
- [ ] Commit: `git add hub-template/ai/architecture.md hub-template/ai/skills/hub-project-create/SKILL.md hub-template/ai/skills/hub-knowledge-enable/SKILL.md scripts/hub-smoke-test.sh && git commit -m "feat: scaffold knowledge inbox in hub projects"`.

### Task 4: Verify and enter review

**Files:** Modify `ai/current-task.md` only after tests pass.

- [ ] Run `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/hub-smoke-test.sh`, `git diff --check`, and `git status --short`; all checks must pass.
- [ ] Inspect `git diff --check main...HEAD && git diff --stat main...HEAD`; only knowledge format, workflow, hub scaffold, test, task-memory, and documentation changes are allowed.
- [ ] Set `Stage: review` in `ai/current-task.md`; commit with `git add ai/current-task.md && git commit -m "docs: mark knowledge layer ready for review"`.
- [ ] Use `superpowers:requesting-code-review` before `task-finish`.
