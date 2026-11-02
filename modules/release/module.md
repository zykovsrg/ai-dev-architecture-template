# Модуль: release

Id: release
Required: no
Switchable: no
Depends: —
Uses if present: —
Rules: —
Keywords: —

## Purpose

Собирать манифест выпуска Хаба из паспортов модулей и запускать проверки
согласованности и установщика только в репозитории; ничто отсюда не устанавливается в Хаб.

## Installs

- —

## Repository only

- scripts/hub_release.py
- scripts/module_passports.py
- scripts/check-module-boundaries.py
- scripts/update-installed-hub.sh
- scripts/install-hub.sh
- scripts/install.sh
- scripts/check-consistency.sh
- scripts/architecture-test.sh
- scripts/mutation-test.py
- scripts/mutation-test-strict.py
- scripts/mutation-filesystem.py
- scripts/mutation-inventory.py
- scripts/mutation-check.py
- scripts/test-method-capture.py
- scripts/test-shell-capture.py
- scripts/python_compat.py
- scripts/hub-smoke-test.sh
- scripts/assistant-workflows.sh
- scripts/assistant-workflows-test.sh
- scripts/refresh-session-inventory.sh
- scripts/test-refresh-session-inventory.sh
- tests/

## Reads

- паспорта модулей и манифест установленного Хаба

## Writes

- манифест выпуска Хаба

## Subscribes

- —
