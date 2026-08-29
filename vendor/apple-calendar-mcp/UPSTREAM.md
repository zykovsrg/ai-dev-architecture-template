Upstream-URL: https://github.com/s-morgan-jeffries/apple-calendar-mcp.git
Upstream-Tag: v0.9.0
Upstream-Commit: 94053dc7a48c44303ac1bc351217f8a14a262806
Audit-Date: 2026-08-29
License: MIT
Auto-Update: disabled

# Local snapshot policy

This directory is a frozen local copy of the exact upstream commit above.
It is not updated automatically and the raw upstream MCP server is never
configured directly in Codex.

The reviewed source did not contain a runtime network client, telemetry, or an
automatic updater. That review is limited to this commit; future upstream code
must be downloaded to a temporary directory, audited again, and copied here
only after explicit user approval.

The Personal AI Hub policy layer is responsible for calendar allowlists,
timezone validation, previews, one-time confirmations, and deletion safety.
