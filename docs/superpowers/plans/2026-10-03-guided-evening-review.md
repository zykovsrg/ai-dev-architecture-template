# Guided Evening Review Implementation Plan

**Goal:** show tomorrow's urgent calendar before reviewing today's project events one at a time.
**Architecture:** read-only selection helper plus authoritative planning resource. Chat keeps the cursor; existing workflows own writes.
**Tech Stack:** Python standard library, unittest, Hub module installer.

## Constraints

- Active registered projects only; guarded Calendar responses only.
- Exact calendar name `Важно и срочно`, resolved through metadata.
- No Calendar writes during tests; no new persistent queue.
- One question per response; projectless events skip silently.

## Task 1: Selection helper and skill contract

Files: `modules/planning/scripts/evening_review.py`, `modules/planning/tests/test_evening_review.py`, `modules/planning/skills/hub-workflows/resources/evening-review.md`, `modules/planning/rules.md`, `modules/planning/module.md`.

- [x] Add tests for urgent selection, project queue, duplicate task blocks, all-day events, partial coverage, inactive/unregistered and ambiguous ownership.
- [x] Run `python3 -m unittest discover -s modules/planning/tests -p test_evening_review.py -v`; expect failure because helper is absent.
- [x] Implement `prepare_review(metadata, today, tomorrow, projects, tasks, day)` returning `urgent`, `queue`, coverage and skipped count. CLI receives Calendar JSON on stdin and validates active registered roots before reading only canonical task files.
- [x] Replace full-report-first contract with urgent-first conversation; preserve existing sync, snapshots, learning, goals and write boundaries.
- [x] Run planning tests and full `bash scripts/architecture-test.sh --all`; expect exit 0.

## Task 2: Install and verify

- [x] Preview the standard Hub update and apply its exact plan digest.
- [x] Compare installed helper/resource/rules with repository source.
- [x] Run installed helper on complete guarded Calendar fixtures and inspect urgent entries and first eligible task. No Calendar mutations.
- [x] Record verification and actual limitations in architecture memory. Commit source changes locally.
