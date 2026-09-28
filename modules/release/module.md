# Module: release

Id: release
Required: no
Switchable: no
Depends: —
Uses if present: —
Rules: —
Keywords: —

## Purpose

Build the Hub release manifest from module passports and run repository-only
consistency and installer checks; nothing here is installed into a Hub.

## Installs

- —

## Repository only

- scripts/hub_release.py
- scripts/migrate-archiprojects-stage6.py
- scripts/module_passports.py
- scripts/check-module-boundaries.py
- scripts/update-installed-hub.sh
- scripts/install-hub.sh
- scripts/install.sh
- scripts/check-consistency.sh
- scripts/architecture-test.sh
- scripts/hub-smoke-test.sh
- scripts/assistant-workflows.sh
- scripts/assistant-workflows-test.sh
- scripts/refresh-session-inventory.sh
- scripts/test-refresh-session-inventory.sh
- tests/

## Reads

- module passports and the installed Hub's manifest

## Writes

- the Hub release manifest

## Subscribes

- —
