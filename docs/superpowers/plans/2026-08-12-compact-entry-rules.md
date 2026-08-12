# Compact Entry Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the standalone and hub entry rules concise, evidence-oriented, intellectually rigorous, and explicitly biased toward the simplest sufficient solution.

**Architecture:** Keep mandatory principles and routing in always-loaded entry files, while keeping detailed interpretation in the corresponding architecture files. Consolidate existing wording instead of appending parallel rules, and verify both installer variants through the existing shell test suite.

**Tech Stack:** Markdown instruction files, Bash consistency and smoke tests, Git.

## Global Constraints

- Persistent AI-facing instructions remain in English.
- `AGENTS.md` and `CLAUDE.md` remain equal in meaning except for tool-specific names.
- No new skill, service, dependency, scoring system, or workflow is introduced.
- Prefer the simplest sufficient solution; necessary safety, correctness, legal, medical, and veterinary constraints remain intact.
- Facts must be separated from interpretations, hypotheses, and opinions.
- Entry files contain mandatory routing; optional implementation-tool names live in the selected skill.
- Protected architecture files change only under this explicitly confirmed `architecture-update`.
- Controlled project memory is not changed by this plan.

---

### Task 1: Add regression checks for the new entry contract

**Files:**
- Modify: `scripts/smoke-test.sh`
- Test: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: root and `hub-template/` entry files.
- Produces: regression assertions used by Tasks 2 and 3.

- [ ] **Step 1: Add assertions that initially fail**

Add assertions for both root entry files:

```bash
for entry in "$ROOT/AGENTS.md" "$ROOT/CLAUDE.md"; do
  assert_contains "$entry" 'simplest sufficient solution'
  assert_contains "$entry" 'Separate verified facts from interpretations, hypotheses, and opinions.'
  assert_contains "$entry" 'security-sensitive change'
  assert_contains "$entry" 'wording or copy review'
done
```

Add hub assertions for the two universal principles that must also apply at the single entry point:

```bash
for entry in "$ROOT/hub-template/AGENTS.md" "$ROOT/hub-template/CLAUDE.md"; do
  assert_contains "$entry" 'simplest sufficient solution'
  assert_contains "$entry" 'Separate verified facts from interpretations, hypotheses, and opinions.'
done
```

Add a helper and assertions preventing the optional UI-tool catalog from returning to root entries:

```bash
assert_not_contains() {
  file="$1"
  needle="$2"
  grep -Fq "$needle" "$file" && fail "$file unexpectedly contains: $needle"
}

assert_not_contains "$ROOT/AGENTS.md" 'theme-factory'
assert_not_contains "$ROOT/CLAUDE.md" 'theme-factory'
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `bash scripts/smoke-test.sh`

Expected: `FAIL` because the new principles and missing routes are not yet in the entry files.

- [ ] **Step 3: Commit the failing contract test**

```bash
git add scripts/smoke-test.sh
git commit -m "test: define compact entry rule contract"
```

### Task 2: Refactor standalone entry rules and detailed architecture

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `ai/architecture.md`
- Test: `scripts/check-consistency.sh`
- Test: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: the existing canonical file-list markers and lifecycle workflows.
- Produces: concise standalone entry files and detailed interpretation in `ai/architecture.md`.

- [ ] **Step 1: Consolidate the standalone core principles**

Replace overlapping core-rule wording with these mandatory principles while preserving the current language, scope, testing, memory, and approval safeguards:

```markdown
## Core Principles

- Talk to the user in Russian and explain unfamiliar technical terms simply.
- Keep persistent AI-facing instructions in English.
- Use a concise, direct, informational style. Add structure only when it improves clarity; avoid filler and unnecessary detail.
- Separate verified facts from interpretations, hypotheses, and opinions. Use evidence appropriate to the claim, state uncertainty honestly, and never invent facts, statistics, sources, or confidence.
- When the user makes an assumption or decision, test its logic and report material errors, missing considerations, counterarguments, and simpler alternatives. Prioritize accuracy over agreement; do not argue without a practical reason.
- Prefer the simplest sufficient solution. Do not add a new entity—code, file, dependency, service, process, project, medication, or anything else—unless it solves a specific problem that existing entities cannot adequately solve and its benefit justifies the added complexity.
- Preserve confirmed scope, use minimal diffs, and do not mix refactoring with bug work unless explicitly requested. Capture useful out-of-scope ideas as future-task candidates.
- Explain real risks before changing storage, data models, dependencies, or architecture. Add tests for risky changes, or explain why manual verification is more practical.
- For medical or veterinary information, use current evidence-based professional sources, state uncertainty and limits, and never independently replace or cancel a qualified professional's prescription.
- Do not overwrite unfinished task memory or change protected architecture files without the required workflow and explicit confirmation.
- In review mode, support findings with files, diffs, logs, tests, or appropriate external sources; otherwise label them as hypotheses.
```

- [ ] **Step 2: Replace the routing catalog with a compact complete map**

Keep the current default-context sentence and canonical file lists. Replace duplicated lifecycle and routing details with:

```markdown
## Lifecycle And Routing

- New session, tool, chat, or restored context → open `environment-check`; show only its snapshot and menu.
- New work → open `task-intake`; changed unfinished work → open `task-switch`.
- Bug, regression, crash, performance issue, or complex task → use Superpowers when available.
- Tests → `write-tests`; UI change → `ui-review`; security-sensitive change → `security-review`; wording or copy review → `copy-review`.
- Release or merge → `release-check`; architecture change → `architecture-update`; completion → propose `task-finish` and wait for confirmation.

Before using a workflow, open its current `ai/skills/<name>/SKILL.md`. Route by the user's request and the skill's `name` and `description`; do not load all skills. Read extra project memory only when the selected task or skill requires it.
```

Preserve the precedence order. Collapse the output section into one concise paragraph. Remove the standalone list of UI-polish tool names and the duplicate Superpowers paragraph.

- [ ] **Step 3: Add detailed interpretation to `ai/architecture.md`**

Add one section near the existing communication and clean-architecture rules:

```markdown
## Simplicity, Evidence, And Intellectual Rigor

Prefer the simplest solution that is sufficient, safe, and complete. Before proposing or adding any entity, state the problem it solves, check whether an existing entity solves it adequately, and compare the benefit with the burden of understanding, monitoring, maintaining, and managing it. Necessary complexity remains justified for safety, correctness, legal compliance, or the user's confirmed goal.

Use evidence appropriate to the claim. Project files, diffs, tests, and logs are primary evidence for local-project facts; current authoritative or professional sources are required for unstable external and health-related claims. Separate verified facts from inference and opinion, state uncertainty, and never invent facts, statistics, sources, or confidence.

Test the user's assumptions when they affect a decision. Report material errors, omissions, counterarguments, and simpler alternatives, but do not manufacture disagreement. For medical and veterinary matters, follow current evidence-based professional sources and never independently cancel, replace, or alter a qualified professional's prescription.

Concise communication is the default. Add headings only when they improve navigation. Give enough information for the current decision; do not add detail merely to anticipate every possible question.
```

Replace the conflicting sentence `It is better to over-explain than to leave the user guessing.` with:

```text
Explain enough for the current decision; prefer a short clear answer over exhaustive background.
```

- [ ] **Step 4: Run standalone checks**

Run:

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected: canonical lists and entry parity pass; smoke tests still fail only if Task 3 hub principles are not yet present; `git diff --check` prints nothing.

- [ ] **Step 5: Commit the standalone implementation**

```bash
git add AGENTS.md CLAUDE.md ai/architecture.md
git commit -m "feat: simplify standalone entry rules"
```

### Task 3: Align the hub entry point and user-facing documentation

**Files:**
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `README.md`
- Modify: `docs/start-prompts.md`
- Modify: `docs/concepts.md`
- Test: `scripts/check-consistency.sh`
- Test: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: the universal principles established by Task 2 and existing hub routing/security gates.
- Produces: consistent behavior in standalone and Personal AI Hub installations.

- [ ] **Step 1: Add compact universal principles to both hub entries**

Add a `Core Principles` section without weakening or duplicating hub routing:

```markdown
## Core Principles

- Use concise Russian and explain unfamiliar technical terms simply.
- Separate verified facts from interpretations, hypotheses, and opinions; use evidence appropriate to the claim and state uncertainty honestly.
- Test material assumptions and prioritize accuracy over agreement.
- Prefer the simplest sufficient solution. Add no entity unless it solves a specific problem that existing entities cannot adequately solve and its benefit justifies the complexity.
- For medical or veterinary information, use current evidence-based professional sources and never independently replace or cancel a qualified professional's prescription.
```

Keep the existing project-confirmation, allowed-root, secret-handling, and isolation rules unchanged. Keep `AGENTS.md` and `CLAUDE.md` semantically equal after tool-name normalization.

- [ ] **Step 2: Add the detailed principle to hub architecture**

Reuse the detailed section from Task 2 in `hub-template/ai/architecture.md`. State that hub routing and project isolation remain higher-priority safety constraints and cannot be removed in the name of simplicity.

- [ ] **Step 3: Synchronize public documentation**

In `README.md`, replace the short communication rule in the universal installation prompt with concise instructions covering brevity, fact/inference separation, honest uncertainty, logic checking, and the simplest sufficient solution.

In `docs/start-prompts.md`, replace `Do not make large changes without a plan and confirmation.` and adjacent communication wording with the same compact principles. Do not reproduce the full detailed architecture section.

In `docs/concepts.md`, add a short explanation that minimalism means reducing management burden, not removing necessary safety or functionality.

- [ ] **Step 4: Run the complete verification suite**

Run:

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected:

```text
OK [standalone canonical blocks]
OK [hub entry parity] — equal after tool-name normalization
Smoke tests passed.
```

`git diff --check` must print nothing.

- [ ] **Step 5: Review protected-file scope and updater behavior**

Run:

```bash
git diff --name-only
rg -n 'AGENTS.md|CLAUDE.md|ai/architecture.md' scripts/update-installed-architecture.sh scripts/update-installed-hub.sh
```

Confirm that every protected-file change belongs to the approved architecture update, controlled memory is untouched, and both existing updaters already distribute the modified files without updater-code changes.

- [ ] **Step 6: Commit documentation and hub alignment**

```bash
git add hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md README.md docs/start-prompts.md docs/concepts.md scripts/smoke-test.sh
git commit -m "feat: align concise rules across installation modes"
```

### Task 4: Final review and release readiness

**Files:**
- Review: all files changed by Tasks 1–3
- Test: `scripts/check-consistency.sh`
- Test: `scripts/smoke-test.sh`

**Interfaces:**
- Consumes: completed standalone, hub, test, and documentation changes.
- Produces: reviewed branch ready for the separately confirmed finish/release workflow.

- [ ] **Step 1: Check the implementation against every specification section**

Verify: minimal-entity decision test, necessary-complexity exception, evidence standards, medical/veterinary limits, concise style, logic checking, complete routing, no optional UI-tool catalog, standalone/hub parity, and no new skill or dependency.

- [ ] **Step 2: Run final verification from a clean command invocation**

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
git status --short
```

Expected: all checks pass, no whitespace errors, and status contains only intentional plan implementation changes if any remain uncommitted.

- [ ] **Step 3: Request code review**

Use `superpowers:requesting-code-review` against the complete implementation diff. Address only verified findings that are within the approved specification.

- [ ] **Step 4: Present completion for confirmation**

Summarize changed rules, tests, token impact, protected-file scope, and any residual risk. Propose `task-finish`; do not merge, push, or close the task without the user's confirmation.
