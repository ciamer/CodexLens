import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import install
import proxy.server as proxy_server
from mcp_server import handle_request
from tools.analyze_img import get_api_key


class McpServerTests(unittest.TestCase):
    def test_initialize_returns_codex_lens_name(self):
        result = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )

        self.assertEqual(result["result"]["serverInfo"]["name"], "CodexLens")

    def test_tools_list_contains_expected_tools(self):
        result = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {tool["name"] for tool in result["result"]["tools"]}

        self.assertTrue({"analyze_img", "read_docx", "read_pdf", "read_document"}.issubset(names))


class ProxyTests(unittest.TestCase):
    def test_rewrites_image_parts_without_network(self):
        original = proxy_server.analyze_image_base64
        proxy_server.analyze_image_base64 = lambda *args, **kwargs: "OK_DESC"
        try:
            body = json.dumps(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "看图"},
                                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                            ],
                        }
                    ]
                }
            ).encode("utf-8")

            out, count = proxy_server.maybe_rewrite_json(body, "application/json", proxy_server.ProxyConfig())
            payload = json.loads(out.decode("utf-8"))
        finally:
            proxy_server.analyze_image_base64 = original

        self.assertEqual(count, 1)
        self.assertEqual(payload["messages"][0]["content"][1]["type"], "text")
        self.assertIn("OK_DESC", payload["messages"][0]["content"][1]["text"])


class InstallTests(unittest.TestCase):
    def test_upsert_block_migrates_old_name_and_deduplicates(self):
        text = "\n".join(
            [
                'base_url = "x"',
                "",
                "[mcp_servers.codex_turbo]",
                'command = "old"',
                "",
                "[mcp_servers.codex_lens]",
                'command = "new"',
                "",
            ]
        )

        out = install.upsert_block(
            text,
            install.server_block(
                "python",
                "main.py",
                "http://127.0.0.1:57321",
                image_proxy_enabled=False,
            ),
        )

        self.assertEqual(out.count("[mcp_servers.CodexLens]"), 1)
        self.assertEqual(out.count("[mcp_servers.codex_turbo]"), 0)
        self.assertEqual(out.count("[mcp_servers.codex_lens]"), 0)
        self.assertIn("--no-proxy", out)

    def test_server_block_omits_no_proxy_when_image_proxy_enabled(self):
        out = install.server_block(
            "python",
            "main.py",
            "http://127.0.0.1:57321",
            image_proxy_enabled=True,
        )

        self.assertNotIn("--no-proxy", out)

    def test_default_install_enables_image_proxy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            state_path = Path(temp_dir) / "codex-lens-state.json"
            argv = [
                "install.py",
                "--config",
                str(config_path),
                "--state",
                str(state_path),
            ]

            with patch.object(sys, "argv", argv), patch.object(install, "notify"), redirect_stdout(StringIO()):
                install.main()

            text = config_path.read_text(encoding="utf-8")

        self.assertIn('base_url = "http://127.0.0.1:57320/v1"', text)
        self.assertIn("[mcp_servers.CodexLens]", text)
        self.assertNotIn("--no-proxy", text)

    def test_remove_proxy_base_url_only_removes_own_value(self):
        text = 'base_url = "http://127.0.0.1:57320/v1"\nother = "kept"\n'
        out = install.remove_base_url_if_value(text, "http://127.0.0.1:57320/v1")

        self.assertNotIn("base_url", out)
        self.assertIn("other", out)

    def test_build_state_preserves_previous_base_url(self):
        state = install.build_state(
            {},
            had_base_url=True,
            current_base_url="http://127.0.0.1:57321/v1",
            proxy_base_url="http://127.0.0.1:57320/v1",
            upstream_base_url="http://127.0.0.1:57321",
        )

        self.assertTrue(state["had_previous_base_url"])
        self.assertEqual(state["previous_base_url"], "http://127.0.0.1:57321/v1")

    def test_mcp_only_restores_proxy_base_url_from_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            state_path = Path(temp_dir) / "codex-lens-state.json"
            config_path.write_text('base_url = "http://127.0.0.1:57320/v1"\n', encoding="utf-8")
            install.save_state(
                state_path,
                {
                    "had_previous_base_url": True,
                    "previous_base_url": "http://127.0.0.1:57321/v1",
                    "proxy_base_url": "http://127.0.0.1:57320/v1",
                },
            )

            with redirect_stdout(StringIO()):
                install.install_mcp_only(
                    config_path=config_path,
                    state_path=state_path,
                    python_path="python",
                    main_path="main.py",
                    proxy_base_url="http://127.0.0.1:57320/v1",
                    upstream_base_url="http://127.0.0.1:57321",
                )

            text = config_path.read_text(encoding="utf-8")

        self.assertIn('base_url = "http://127.0.0.1:57321/v1"', text)
        self.assertIn("--no-proxy", text)
        self.assertIn("[mcp_servers.CodexLens]", text)


class ApiKeyTests(unittest.TestCase):
    def test_missing_api_key_has_project_specific_error(self):
        old_value = os.environ.pop("CODEX_LENS_API_KEY", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "CODEX_LENS_API_KEY"):
                get_api_key()
        finally:
            if old_value is not None:
                os.environ["CODEX_LENS_API_KEY"] = old_value


if __name__ == "__main__":
    unittest.main()
