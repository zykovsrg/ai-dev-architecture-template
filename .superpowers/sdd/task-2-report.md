# Task 2 report

## RED

Добавлен тест architecture-originated refresh: после изменения canonical title запуск с `--write --refresh-from-architecture` должен обновить board, а ручное изменение board должно завершиться `proposal pending: manual task board edit detected`.

Команда:

```bash
bash scripts/obsidian-projects-kanban-test.sh
```

Ожидаемый failure получен: `error: unknown flag: --refresh-from-architecture` (exit 1).

## GREEN

Добавлен флаг `--refresh-from-architecture`. Он допускается только вместе с `--write` и заменяет только требование `--confirm-generated-write`; manifest validation и hash-проверки не менялись.

Проверки:

```bash
bash scripts/obsidian-projects-kanban-test.sh
```

Результат: `PASS: Obsidian task Kanban and project overview contract` (exit 0).

Дополнительно:

```bash
bash -n scripts/generate-obsidian-projects-kanban.sh scripts/obsidian-projects-kanban-test.sh
git diff --check
```

Обе проверки завершились успешно.

## Commit

`feat: allow guarded architecture board refresh`
