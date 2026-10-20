import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills/qwen-unified/scripts/qwen_unified.py"
spec = importlib.util.spec_from_file_location("qwen_unified", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class QwenUnifiedTests(unittest.TestCase):
    def test_doctor_has_no_keys(self):
        with mock.patch.dict(os.environ, {"QWEN_API_KEY": "super-secret", "QWEN_BASE_URL": "http://localhost:8000/v1"}):
            report = mod.doctor()
        self.assertNotIn("super-secret", json.dumps(report))
        self.assertIn("No connectivity", report["notice"])

    def test_endpoint_validation(self):
        for url in ["http://example.com/v1", "ftp://localhost/v1", "https://example.com/api", "https://me:password@example.com/v1"]:
            with self.subTest(url=url), mock.patch.dict(os.environ, {"QWEN_BASE_URL": url}):
                with self.assertRaises(ValueError):
                    mod.endpoint()
        with mock.patch.dict(os.environ, {"QWEN_BASE_URL": "https://example.com/v1"}):
            self.assertEqual(mod.endpoint(), "https://example.com/v1")

    def test_model_routing_and_authenticated_request(self):
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())
        with mock.patch.dict(os.environ, {"QWEN_BASE_URL": "http://localhost:8000/v1", "QWEN_API_KEY": "key"}), mock.patch.object(mod.request, "urlopen", return_value=response) as open_url:
            result = mod.call_model("coder", "Help", 10)
        req = open_url.call_args.args[0]
        self.assertEqual(req.full_url, "http://localhost:8000/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer key")
        self.assertEqual(json.loads(req.data)["model"], mod.DEFAULT_CODER)
        self.assertEqual(result["response"], "ok")

    def test_code_is_preview_by_default(self):
        with TemporaryDirectory() as temp, mock.patch.object(mod.subprocess, "run") as run:
            output = mod.code_command(temp, "Inspect", False, 30)
        self.assertEqual(output["status"], "preview_only")
        run.assert_not_called()

    def test_code_requires_real_cli_to_execute(self):
        with TemporaryDirectory() as temp, mock.patch.object(mod.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError):
                mod.code_command(temp, "Inspect", True, 30)

    def test_safe_workspace_paths(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "ok.py").write_text("print('ok')")
            (root / ".env").write_text("secret")
            (root / "key.txt").symlink_to(root / ".env")
            self.assertEqual(mod._safe_repo_file(root, "ok.py").name, "ok.py")
            for path in ["../etc/passwd", ".env", "key.txt", "/etc/passwd"]:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    mod._safe_repo_file(root, path)
            self.assertEqual(mod.repo_inventory(root), ["ok.py"])

    def test_missing_endpoint_gives_error_code(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                status = mod.main(["ask", "--mode", "general", "--prompt", "hi"])
        self.assertEqual(status, 2)
        self.assertIn("QWEN_BASE_URL missing", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
