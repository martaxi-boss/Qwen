#!/usr/bin/env python3
"""Qwen Unified: four Qwen upstream components behind one conservative CLI.

Only runs an upstream component when the corresponding endpoint/dependency exists.
No model downloads, installs, paid API calls, or source edits occur in `doctor`.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from urllib import error, parse, request

DEFAULT_GENERAL = "Qwen/Qwen3.8-27B"
DEFAULT_CODER = "Qwen/Qwen3-Coder-Next"
BLOCKED_NAMES = {".env", ".env.local", ".npmrc", ".pypirc", "credentials.json", "id_rsa", "id_ed25519"}
BLOCKED_PARTS = {".git", ".venv", "node_modules", "__pycache__", "secrets", ".ssh"}
ALLOWED_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml", ".html", ".css", ".sh", ".txt"}


def endpoint() -> str:
    base = os.environ.get("QWEN_BASE_URL", "").rstrip("/")
    if not base:
        raise ValueError("QWEN_BASE_URL missing: configure a reachable /v1 API before model use")
    u = parse.urlparse(base)
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("Invalid QWEN_BASE_URL")
    if u.scheme == "http" and u.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Remote QWEN_BASE_URL must use HTTPS")
    if not u.path.rstrip("/").endswith("/v1"):
        raise ValueError("QWEN_BASE_URL must end in /v1")
    return base


def model_for(mode: str) -> str:
    if mode == "general":
        return os.environ.get("QWEN_GENERAL_MODEL") or DEFAULT_GENERAL
    if mode == "coder":
        return os.environ.get("QWEN_CODER_MODEL") or DEFAULT_CODER
    raise ValueError("Unknown model mode")


def doctor() -> dict:
    return {
        "qwen_code_installed": bool(shutil.which("qwen")),
        "qwen_agent_installed": importlib.util.find_spec("qwen_agent") is not None,
        "endpoint_configured": bool(os.environ.get("QWEN_BASE_URL")),
        "general_model_configured": os.environ.get("QWEN_GENERAL_MODEL") or DEFAULT_GENERAL,
        "coder_model_configured": os.environ.get("QWEN_CODER_MODEL") or DEFAULT_CODER,
        "notice": "No connectivity or live model execution is performed by doctor",
    }


def call_model(mode: str, prompt: str, timeout: int, override: str | None = None) -> dict:
    base = endpoint()
    model = override or model_for(mode)
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = os.environ.get("QWEN_API_KEY")
    if key:
        headers["Authorization"] = "Bearer " + key
    req = request.Request(base + "/chat/completions", data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read(8 * 1024 * 1024).decode("utf-8"))
    except error.HTTPError as e:
        raise RuntimeError("Model endpoint returned HTTP " + str(e.code)) from e
    except error.URLError as e:
        raise RuntimeError("Model endpoint unreachable: " + str(e.reason)) from e
    if not isinstance(data, dict) or not data.get("choices"):
        raise RuntimeError("Unexpected model response (no choices)")
    text = data["choices"][0].get("message", {}).get("content", "")
    return {"backend": "qwen-model", "mode": mode, "model": model, "response": text}


def code_command(workspace: str, prompt: str, execute: bool, timeout: int) -> dict:
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Workspace is not an existing directory")
    command = ["qwen", "-p", prompt]
    if not execute:
        return {"backend": "qwen-code", "status": "preview_only", "workspace": str(root),
                "command": "qwen -p <prompt>", "notice": "Use --execute to run Qwen Code"}
    executable = shutil.which("qwen")
    if not executable:
        raise RuntimeError("Qwen Code CLI missing (install and authenticate separately)")
    command[0] = executable
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True,
                               timeout=timeout, check=False)
    return {"backend": "qwen-code", "status": "executed", "workspace": str(root),
            "returncode": completed.returncode, "stdout": completed.stdout[-20000:],
            "stderr": completed.stderr[-5000:]}


def _safe_repo_file(root: Path, rel: str) -> Path:
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError("Only workspace-relative paths are supported")
    if any(part in BLOCKED_PARTS or part.startswith(".env") for part in candidate.parts):
        raise ValueError("Path is excluded")
    target = root.joinpath(candidate)
    if any(parent.is_symlink() for parent in [target, *target.parents] if parent != root.parent):
        raise ValueError("Symlinks are excluded")
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    if target.name in BLOCKED_NAMES or target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("File type/name is excluded")
    if not resolved.is_file() or resolved.stat().st_size > 65536:
        raise ValueError("File missing or too large")
    return resolved


def repo_inventory(root: Path, max_files: int = 50) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if any(part in BLOCKED_PARTS or part.startswith(".env") for part in rel.parts):
            continue
        if path.name in BLOCKED_NAMES or path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        found.append(str(rel))
        if len(found) >= max(1, min(max_files, 200)):
            break
    return found


def agent_run(prompt: str, workspace: str | None, allow_repo_read: bool, override: str | None = None) -> dict:
    try:
        from qwen_agent.agents import Assistant
        from qwen_agent.tools.base import BaseTool, register_tool
    except ImportError as e:
        raise RuntimeError("Install optional Qwen-Agent first: python -m pip install qwen-agent") from e
    base = endpoint()
    llm = {"model": override or model_for("general"), "model_server": base,
           "api_key": os.environ.get("QWEN_API_KEY") or "EMPTY"}
    tools: list[str] = []
    if allow_repo_read:
        if not workspace:
            raise ValueError("--workspace is required with --allow-repo-read")
        root = Path(workspace).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Workspace missing")

        @register_tool("qu_list_files")
        class ListFiles(BaseTool):
            description = "List up to 50 non-secret code/text files in the authorized workspace"
            parameters = []

            def call(self, params: str, **kwargs) -> str:
                return json.dumps(repo_inventory(root), ensure_ascii=False)

        @register_tool("qu_read_file")
        class ReadFile(BaseTool):
            description = "Read one relative non-secret source file within the authorized workspace"
            parameters = [{"name": "path", "type": "string", "required": True,
                           "description": "Workspace-relative source path"}]

            def call(self, params: str, **kwargs) -> str:
                try:
                    path = json.loads(params)["path"]
                    return _safe_repo_file(root, path).read_text(encoding="utf-8", errors="replace")
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    return "Read rejected: " + str(exc)

        tools = ["qu_list_files", "qu_read_file"]
    bot = Assistant(llm=llm, system_message="Report evidence and uncertainty. Do not invent executions.",
                    function_list=tools)
    last = []
    for messages in bot.run(messages=[{"role": "user", "content": prompt}]):
        last = messages
    return {"backend": "qwen-agent", "model": llm["model"], "result": last,
            "repo_read_enabled": allow_repo_read}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Unified routing for official Qwen projects")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Inspect configuration; no network requests")
    ask = sub.add_parser("ask", help="Use Qwen3.8 or Qwen3-Coder model endpoint")
    ask.add_argument("--mode", choices=["general", "coder"], required=True)
    ask.add_argument("--prompt", required=True)
    ask.add_argument("--model", help="Override served model ID")
    ask.add_argument("--timeout", type=int, default=90)
    code = sub.add_parser("code", help="Preview or run Qwen Code in a workspace")
    code.add_argument("--workspace", required=True)
    code.add_argument("--prompt", required=True)
    code.add_argument("--execute", action="store_true", help="Actually invoke the external Qwen CLI")
    code.add_argument("--timeout", type=int, default=600)
    agent = sub.add_parser("agent", help="Use the optional Qwen-Agent Python framework")
    agent.add_argument("--prompt", required=True)
    agent.add_argument("--model", help="Override served model ID")
    agent.add_argument("--workspace")
    agent.add_argument("--allow-repo-read", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "ask":
            result = call_model(args.mode, args.prompt, args.timeout, args.model)
        elif args.command == "code":
            result = code_command(args.workspace, args.prompt, args.execute, args.timeout)
        else:
            result = agent_run(args.prompt, args.workspace, args.allow_repo_read, args.model)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc), "command": args.command}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
