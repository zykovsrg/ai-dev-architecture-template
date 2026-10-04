# Cheap-model roles: how each host starts them (spike, 2026-10-04)

Scratch dirs (git-ignored): `.superpowers/sdd/2026-10-04-session-learning/scratch/{claude-probe,codex-probe,codex-probe2}`.

## Claude Code (verified)

- Role file: `.claude/agents/probe.md`, frontmatter `name`, `description`, `model: haiku`, `tools: Read`; body = instructions.
- Command (cwd `scratch/claude-probe`, claude v2.1.126):
  `claude -p "Use the probe agent and print its reply." --output-format json --max-budget-usd 0.5`
- Evidence: the agent replied "claude-haiku-4-5-20251001"; JSON `modelUsage` lists `claude-haiku-4-5-20251001` (3295 in / 21 out) next to the parent `claude-sonnet-4-6`. `modelUsage` is the reliable confirmation; the self-report matched it.
- Install target for the learning module: `.claude/agents/<name>.md` with `model: haiku`.

## Codex (verified via CLI; project-level role discovery NOT verified)

- No `codex` on PATH. Working binary: `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` (codex-cli 0.160.0). `multi_agent` feature is stable and on. `~/.codex/models_cache.json` lists `gpt-6-luna`.
- Model evidence must come from the session rollout (`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, `turn_context.model`), NOT from the model's self-report: with `-m gpt-6-luna` the model answered "gpt-6.1-sol" while the rollout showed `gpt-6-luna`.
- Test 1 (direct model): `codex exec -m gpt-6-luna --skip-git-repo-check --json -s read-only "..." </dev/null` -> rollout model `gpt-6-luna`. Honoured.
- Test 2 (role file + `[agents.probe]` in project `.codex/config.toml`, spawned via natural prompt or `spawn_agent`, cwd `scratch/codex-probe`): `unknown agent_type 'probe'`. The project config was not picked up; a per-run `-c projects."<dir>".trust_level="trusted"` override did not change this, so trust of the scratch dir could not be established from the CLI. Same failure with a self-describing role file (`name`, `description`, `model`, ...) in `.codex/agents/` only (`codex-probe2`).
- Test 3 (role registered via per-run overrides, no file edits):
  `codex exec -c 'agents.probe.description="..."' -c 'agents.probe.config_file="<abs>/scratch/codex-probe/.codex/agents/probe.toml"' --skip-git-repo-check --json -s read-only "Call the spawn_agent tool with agent_type \"probe\" ..."`
  -> child reply "gpt-6-luna"; child rollout `session_meta.agent_role = probe`, its own `turn_context` = model `gpt-6-luna`, effort `low` (parent: `gpt-6.1-sol`). So a role file with `model = "gpt-6-luna"` and `model_reasoning_effort = "low"` IS honoured when registered as `[agents.<name>]` with `description` + `config_file`.
- Role file format that worked (keys): `model`, `model_reasoning_effort`, `developer_instructions`.
- Not touched: `~/.codex/config.toml`, `~/.codex/agents/`.

### Recommended install targets (Codex)

1. Role file `agents/<name>.toml` with `model = "gpt-6-luna"`, `model_reasoning_effort = "low"`, `developer_instructions`.
2. Registration `[agents.<name>]` with `description` and `config_file` in a Codex config that is actually loaded. Expected but UNVERIFIED: registering in a config file (user-level `~/.codex/config.toml` or project-level `.codex/config.toml`). Only per-run `-c agents.probe.*` overrides were tested; no config file was ever shown to work, project-level discovery failed, and relative `config_file` resolution was not tested (absolute path used).
3. Fallback (per brief): if the role cannot be registered, run the scan in the current Codex model with `model_reasoning_effort = "low"`. Direct `-m gpt-6-luna` works for non-interactive `codex exec` runs.

## Decision for Task 5 (controller ruling)

The Codex scan does NOT rely on agent-role registration. The skill runs the scanner as a subprocess:

`<codex binary> exec -m gpt-6-luna -c model_reasoning_effort=low -s read-only --skip-git-repo-check -o <out-file> "<prompt incl. role instructions read from a file>" </dev/null`

- Consolidator: same, with `-m gpt-6.1-sol`.
- Flags (from `codex exec --help`): `-m, --model <MODEL>`; `-c, --config <key=value>`; `-s, --sandbox <SANDBOX_MODE>` [possible values: read-only, workspace-write, danger-full-access]; `-o, --output-last-message <FILE>` ("Specifies file where the last message from the agent should be written"); `-C, --cd <DIR>`; `--skip-git-repo-check`; `--ephemeral` (no session files; do not use if rollout confirmation is wanted).
- Verified once: this exact shape wrote `ok` to the `-o` file and the rollout turn_context showed `gpt-6-luna`, effort `low`.
- Binary discovery: `codex` on PATH, then `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`.
- Model confirmation: rollout `turn_context`, not self-report. No edits to `~/.codex`.
- Claude stays `.claude/agents/<name>.md` with `model: haiku` / `model: opus`.

## Open risks

- Codex project-level `.codex/config.toml` / `.codex/agents/` discovery unverified (likely a trust requirement that the CLI override did not satisfy); the Codex desktop app was not driven.
- Codex model self-report is unreliable; verify via rollout `turn_context`.
- Codex model names (`gpt-6-luna`) may change; they were present in the local models cache today.
- Claude alias `haiku` resolved to `claude-haiku-4-5-20251001` today; the alias may move.
