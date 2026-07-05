import json
import os
import unittest

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

        self.assertEqual(result["result"]["serverInfo"]["name"], "codex-lens")

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

        out = install.upsert_block(text, install.server_block("python", "main.py", "http://127.0.0.1:57321"))

        self.assertEqual(out.count("[mcp_servers.codex_lens]"), 1)
        self.assertEqual(out.count("[mcp_servers.codex_turbo]"), 0)

    def test_remove_proxy_base_url_only_removes_own_value(self):
        text = 'base_url = "http://127.0.0.1:57320/v1"\nother = "kept"\n'
        out = install.remove_proxy_base_url(text, "http://127.0.0.1:57320/v1")

        self.assertNotIn("base_url", out)
        self.assertIn("other", out)


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
