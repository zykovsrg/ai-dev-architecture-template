# Current Task

Task ID: TASK-ai-dev-architecture-20260928-001

Status: active
Stage: implementation

## Goal

Добавить `.DS_Store` в `.gitignore` шаблона хаба (`modules/core/data/.gitignore`),
чтобы служебный файл macOS не делал дерево хаба «грязным» и не останавливал
обновление.

## Relevant files

- `modules/core/data/.gitignore`
- `tests/test_hub_only_distribution.py`

## Done criteria

- Шаблонный `.gitignore` игнорирует `.DS_Store`; тест это проверяет и был увиден падающим.
- CI зелёный в pull request до слияния в `main`.
- Рабочий хаб обновляется только после «да» пользователя; drift даёт exit 0.

## Agent handoff

Last agent: Claude (Opus 5.5)

What changed: задача записана по согласию пользователя 2026-09-28.

Open risks: нет.

Next agent should check: —
