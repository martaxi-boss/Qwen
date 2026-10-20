---
name: qwen-unified
description: Coordinate Qwen3.8 general reasoning, Qwen3-Coder programming, Qwen Code headless coding, and Qwen-Agent workflows from ChatGPT. Use for Qwen-oriented repository analysis, model routing, code review, programmatic agent orchestration, or integrating a local/API-backed Qwen worker without replacing an existing Codex or Project Leader setup.
---

# Qwen Unified

Use one skill to route work among four separate official Qwen projects. This is an integration layer, not a merged model or a standalone AI engine. Never claim that a Qwen model ran unless an actual model endpoint, Qwen Code CLI, or Qwen-Agent run returned results.

## Routing

1. **General reasoning / planning**: Qwen3.8 via an OpenAI-compatible inference endpoint. Run `python scripts/qwen_unified.py ask --mode general --prompt "..."` when a configured endpoint is available.
2. **Specialized code reasoning**: Qwen3-Coder through the same standard API. Run `python scripts/qwen_unified.py ask --mode coder --prompt "..."`.
3. **Repository modifications / tests**: Qwen Code headless CLI. First preview with `python scripts/qwen_unified.py code --workspace /path/to/repo --prompt "..."`; use `--execute` only with authorized workspace write access, appropriate tool permissions, and a concrete user request. Review diffs and tests before describing success.
4. **Agent workflows**: Qwen-Agent Python framework. Run `python scripts/qwen_unified.py agent --prompt "..."`; optionally pass `--allow-repo-read --workspace /path/to/repo` only for code that the user authorized to share with the configured model provider. These tools are read-only and filter common secrets.

If a suitable local execution tool is missing in the current ChatGPT session, use accessible GitHub or other connected tools for inspection and state that Qwen execution is not available. ChatGPT Skills cannot independently install binaries on the user's VPS, connect to unconfigured endpoints, or bypass platform permissions.

## Setup and preflight

Read `references/integration.md` before installing or configuring. Check availability with `python scripts/qwen_unified.py doctor`. Never set a paid API or deploy a large model silently. A local inference server requires sufficient GPU/RAM and is not provided by the GitHub information repositories.

Configure variables on the machine that runs the CLI:

- `QWEN_BASE_URL` - reachable OpenAI-compatible API base ending in `/v1`, for example `http://127.0.0.1:8000/v1`.
- `QWEN_API_KEY` - provider token, if needed; never write it to source control or logs.
- `QWEN_GENERAL_MODEL` - actual model ID served for Qwen3.8, such as `Qwen/Qwen3.8-27B`.
- `QWEN_CODER_MODEL` - actual served Qwen3-Coder model, such as `Qwen/Qwen3-Coder-Next`.

For remote endpoints use HTTPS. Never represent `doctor` as proof that an API answered: it only checks local configuration/dependencies.

## Working rules

- Respect the existing workspace and any established project conventions. Do not mix projects or overwrite unrelated GitHub repositories.
- Detect the available connector, filesystem and model services before choosing a backend; do not create substitute agents or MCP servers needlessly.
- Start with read-only analysis, and run the smallest necessary test before reporting a modification.
- Check repository `git status`, current branch, existing changes and CI results when tools permit. Never force push, auto-merge, or activate production for routine work.
- Report outcome as **confirmed**, **tested with a mock**, **not tested**, or **requires external setup**. Distinguish ChatGPT's own analysis from output actually obtained from Qwen.
- Do not clone all four upstream projects or bundle model weights into this Skill. Respect each upstream project's license and versioning.

## Deliverable format

Summarize selected backend, inputs, outputs, tests, exact file/commit references, limitations, and whether the Qwen model was really invoked. Use `references/integration.md` for upstream URLs, setup, and troubleshooting. This skill does not grant new execution capabilities to ChatGPT by itself.
