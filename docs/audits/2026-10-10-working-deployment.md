# Working deployment — 2026-10-10

The user requested updating working architecture and applications, then excluded both bots hosted on Bothost and canceled further planner updates because the planner project will be deleted soon.

## Architecture — completed

Preserved three installed project-scope learning clarifications in source commit 79c5922. Official release apply changed metadata only. Calendar bridge rebuilt through official sync after a permitted sandbox-cache retry. Final drift: no conflicts or unmanaged files; strict module boundaries: zero warnings. 91 managed files match. Registry: 82 entries validated. 37 focused tests, consistency and 9 installation checks passed. User settings, calendar allowlist, registry and preexisting edits preserved; calendar events unchanged.

Five failures in the full 73-test learning suite reproduce on the clean pre-change baseline; date-fixed fixtures conflict with runtime modification timestamps. They were not caused or repaired by this release.

## Planner — further update canceled

Before cancellation, the desktop bundle was rebuilt from 4b6a345. Signature/plist checks passed; five bundled frontend files match source bytes. Initial live health/state checks returned HTTP 200 and a revision, and four served assets match source. A later health check was refused. Native window inspection was not approved. The cause of process termination is not established; no claim of persistent runtime health is made. At the user's cancellation, no further launch, debugging, updating, or deletion was performed. The generated bundle remains as built.

## Hosted bots — excluded

No bot code upload, push, restart, or hosted-data migration was performed. Read-only GitHub deployment discovery returned no records and ceased after the user's clarification.

## Other applications

The generic planner and analytics commands use updated local source directly. No separately deployed bundle or matching long-running local service was identified. No analytics rebuild or data fetch was triggered. Other projects were not deployed. No remote push was performed.
