# Qwen Unified for ChatGPT

A single **ChatGPT Skill** that routes tasks to four official Qwen projects without mixing their source code or distributing large model weights.

**Official upstream:** [Qwen3.8](https://github.com/QwenLM/Qwen3.8) (general reasoning), [Qwen3-Coder](https://github.com/QwenLM/Qwen3-Coder) (coding model), [Qwen Code](https://github.com/QwenLM/qwen-code) (coding CLI), and [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) (agent framework).

## What is included

- `skills/qwen-unified/SKILL.md`: ChatGPT routing instructions and guards.
- `skills/qwen-unified/scripts/qwen_unified.py`: actual stdlib Python adapter for OpenAI-compatible Qwen model endpoints, Qwen Code CLI, and optional Qwen-Agent.
- `skills/qwen-unified/references/integration.md`: configuration, trust boundaries, upstream links.
- `tests/`: offline unit tests; no paid API usage.

The skill ZIP can be imported into ChatGPT Skills. **Importing it does not run Qwen locally or install the four backends.** A real Qwen model needs a reachable inference endpoint; Qwen Code and Qwen-Agent are optional host-side installations.

## Try without paying for API calls

```sh
python skills/qwen-unified/scripts/qwen_unified.py doctor
python -m unittest discover -s tests -v
python skills/qwen-unified/scripts/qwen_unified.py code --workspace . --prompt 'Review this repository'
```

The `code` command is a **preview** without `--execute`. For live use, configure the endpoint and optional backends as documented in [integration.md](skills/qwen-unified/references/integration.md). Only execute Qwen Code against an authorized project; source edits are not automatically approved.

## ChatGPT installation

Download `skill.zip` from the provided ChatGPT conversation artifact (or package `skills/qwen-unified` with the skill creator), then import it into your ChatGPT Skills library where supported. The package includes the folder with `SKILL.md`, `agents/openai.yaml`, scripts and references. It does not change your existing Project Leader or Codex projects.

## Status

- Skill instructions and adapters: implemented.
- Offline integration tests: part of this repository.
- Real Qwen model / VPS / provider login: **not configured by this repository**.
- Licenses for upstream code and weights: governed by their respective upstream projects. No upstream weights or source snapshots are vendored here.