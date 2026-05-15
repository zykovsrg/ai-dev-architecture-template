---
name: security-review
type: knowledge
description: |
  Use before release or when changes touch storage, local files, paths, HTML rendering, user data, external APIs, secrets, dependencies, or destructive actions.
  Activates when:
  - code touches files, paths, storage, user data, HTML rendering, API calls, dependencies, or secrets
  - the change may expose data or run destructive operations
  - the user asks to check safety or security risks
  Does NOT activate for:
  - copy-only changes
  - visual-only UI changes
  - local layout changes with no data, files, or external access
---

# Security Review

Check:

1. No unsafe file path handling.
2. No secrets committed.
3. No unsafe eval.
4. No unsafe HTML injection.
5. No unnecessary dependency added.
6. No accidental user data exposure.
7. No destructive file operation without clear reason.

Return only concrete risks and fixes.
