# Qwen Unified integration reference

## Sources and division of responsibilities

| Component | Official upstream | Runtime integration |
| --- | --- | --- |
| Qwen3.8 | https://github.com/QwenLM/Qwen3.8 | Model weights are distributed separately (Hugging Face / ModelScope). Serve through a compatible API. |
| Qwen3-Coder | https://github.com/QwenLM/Qwen3-Coder | Model weights are separate. Serve the exact chosen variant through a compatible API. |
| Qwen Code | https://github.com/QwenLM/qwen-code | Optional `qwen` executable for headless code tasks. |
| Qwen-Agent | https://github.com/QwenLM/Qwen-Agent | Optional Python package `qwen-agent` for tool-using workflows. |

All components are upstream projects, not bundled copies. Check their license files, current documentation and model-specific terms before any redistribution/deployment. Qwen3.8 and Qwen3-Coder GitHub repositories alone do not provide a ready-to-run model endpoint or large model weight files.

## Install adapters (on a trusted machine)

The unified script itself uses only the Python 3.10+ standard library.

- Optional coding CLI: follow upstream Qwen Code docs or use `npm install -g @qwen-code/qwen-code` with Node.js 22+.
- Optional Qwen-Agent: `python -m pip install -U qwen-agent`.
- For local inference, provision separately a compatible server (e.g. vLLM, SGLang, llama.cpp with support for the chosen model). Do not assume a standard VPS can serve a large model.

Configure the endpoint and models using environment variables (no credentials in a file committed to GitHub):

```sh
export QWEN_BASE_URL=http://127.0.0.1:8000/v1
export QWEN_GENERAL_MODEL=Qwen/Qwen3.8-27B
export QWEN_CODER_MODEL=Qwen/Qwen3-Coder-Next
# export QWEN_API_KEY=...  # only if the endpoint requires it
python skills/qwen-unified/scripts/qwen_unified.py doctor
```

Examples (run from the repository root):

```sh
python skills/qwen-unified/scripts/qwen_unified.py ask --mode general --prompt 'Design a test plan'
python skills/qwen-unified/scripts/qwen_unified.py ask --mode coder --prompt 'Explain this Python function'
python skills/qwen-unified/scripts/qwen_unified.py code --workspace . --prompt 'Review tests and suggest improvements'
# Intentionally only a preview by default; --execute starts the CLI.
python skills/qwen-unified/scripts/qwen_unified.py agent --prompt 'Suggest a dependency audit plan'
```

The remote endpoint must use HTTPS (plain HTTP is allowed only for localhost). A public URL, tunnel or service connector is required for the ChatGPT runtime to reach a separate user's VPS. Running a script in the ChatGPT sandbox does not connect to localhost on the user's VPS.

## Authentication, data and costs

Qwen Code itself is open-source, but the model provider may charge for API tokens. No free cloud quota is assumed. Local hosting avoids per-token API charges but has infrastructure costs. The `code` command does not bypass Qwen Code's authorization mechanisms. No API keys, model weights, or external-service sessions are stored in the Skill.

Qwen-Agent's optional read-only tools need `--allow-repo-read`; they intentionally skip obvious credential files, private key formats, symlinks, `.git` and vendored directories. Inspect the selected project before sending potentially private content to any external inference provider.

## Compatibility boundaries

- The script is an adapter: the exact model identifiers and API capabilities must match the deployment.
- Qwen-Agent Python APIs may change across versions; use the officially documented `Assistant` and `BaseTool` interfaces and run a real smoke test after installation.
- For Qwen Code, `qwen -p` depends on the CLI being installed and authenticated in that environment.
- A Skill is instructions plus optional scripts: importing it into ChatGPT alone does not create host processes or make external model endpoints accessible.
- Project Leader/Codex is **not** modified or linked by default. Integrate only after reviewing repository-specific architecture and obtaining authorization to change that project.

## Validation tiers

1. **Unit tests**: exercise routing and safety with mocked requests, no model costs.
2. **Dependency test**: run `doctor` and check Qwen Code / Qwen-Agent installations (not proof of response).
3. **Live integration**: invoke `ask`, `agent`, and Qwen Code against an explicitly configured provider/repository; report each verified action and costs, if available.
