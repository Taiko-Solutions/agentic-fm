#!/usr/bin/env python3
"""Tests for run_script.py: run any script of any file of a solution over OData."""

import contextlib
import io
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_script as rs  # noqa: E402

DS = "Datos Históricos"


def _env(**kv):
    """What OData returns when AGFMScriptBridge exits with the JSON object kv."""
    return {"scriptResult": {"code": 0, "resultParameter": json.dumps(kv)}}


VERSION_OK = _env(success=True, script="AGFM Version", result="1.5.0")


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        call = json.loads(json.loads(body)["scriptParameterValue"])
        self.server.calls.append(call)
        status, payload = self.server.replies.pop(0)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, *args):
        pass


class RunScriptTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.server.calls = []
        self.server.replies = []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Path(self.tmp.name) / "agent" / "config"
        cfg.mkdir(parents=True)
        main = {"base_url": f"http://127.0.0.1:{self.server.server_port}",
                "database": "SolutionApp", "username": "u", "password": "p"}
        (cfg / "automation.json").write_text(json.dumps({"solutions": {
            "SolutionApp": {"odata": main},
            "SolutionData": {"odata": {"via": "SolutionApp", "data_source": DS}}}}), encoding="utf-8")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_cli(self, *args, replies=(), answer=None):
        """Run main(); returns (exit code, stdout, stderr)."""
        self.server.replies = [r if isinstance(r, tuple) else (200, r) for r in replies]
        out, err = io.StringIO(), io.StringIO()
        argv = ["--repo", self.tmp.name, *args]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch("builtins.input", return_value=answer or ""):
            try:
                code = rs.main(argv)
            except SystemExit as exc:      # argparse or sys.exit
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    @property
    def calls(self):
        return self.server.calls

    def test_full_block_runs_in_one_request(self):
        code, out, _ = self.run_cli("--solution", "SolutionApp", "--script", "S", "--param", "p", "--yes",
                                    replies=[_env(success=True, script="S", result="hecho")])
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [{"script": "S", "parameter": "p"}])
        self.assertIn("hecho", out)

    def test_via_checks_the_version_then_sends_data_source(self):
        code, out, _ = self.run_cli("--solution", "SolutionData", "--script", "S", "--yes", replies=[
            VERSION_OK, _env(success=True, script="S", data_source=DS, result="ok")])
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0]["script"], "AGFM Version")
        self.assertNotIn("data_source", self.calls[0])
        self.assertEqual(self.calls[1]["script"], "S")
        self.assertEqual(self.calls[1]["data_source"], DS)
        self.assertIn("ok", out)

    def test_old_main_sends_no_script_call(self):
        code, _, err = self.run_cli("--solution", "SolutionData", "--script", "S", "--yes", replies=[
            _env(success=True, script="AGFM Version", result="1.4.0")])
        self.assertEqual(code, 2)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("1.5.0", err)

    def test_main_without_agfm_version_sends_no_script_call(self):
        code, _, _ = self.run_cli("--solution", "SolutionData", "--script", "S", "--yes", replies=[
            _env(success=False, error="Script not found: AGFM Version")])
        self.assertEqual(code, 2)
        self.assertEqual(len(self.calls), 1)

    def test_answer_without_data_source_echo_is_an_error(self):
        code, out, _ = self.run_cli("--solution", "SolutionData", "--script", "S", "--yes", replies=[
            VERSION_OK, _env(success=True, script="S", result="ok")])
        self.assertEqual(code, 2)
        self.assertNotIn("ok", out)

    def test_param_travels_verbatim(self):
        param = 'ñ "comillas" {"a":1}'
        self.run_cli("--solution", "SolutionApp", "--script", "S", "--param", param, "--yes",
                     replies=[_env(success=True, script="S", result="")])
        self.assertEqual(self.calls[0]["parameter"], param)

    def test_plain_text_result_is_printed_as_is(self):
        text = '{"success": false, "script": "x"}'
        code, out, _ = self.run_cli("--solution", "SolutionApp", "--script", "S", "--yes",
                                    replies=[_env(success=True, script="S", result=text)])
        self.assertEqual(code, 0)
        self.assertIn(text, out)

    def test_bridge_failure_shows_error_and_code(self):
        code, _, err = self.run_cli("--solution", "SolutionData", "--script", "S", "--yes", replies=[
            VERSION_OK, _env(success=False, error="script_or_data_source_not_found", error_code=104,
                             script="S", data_source=DS)])
        self.assertEqual(code, 1)
        self.assertIn("script_or_data_source_not_found", err)
        self.assertIn("104", err)

    def test_missing_local_script(self):
        code, _, err = self.run_cli("--solution", "SolutionApp", "--script", "S", "--yes",
                                    replies=[_env(success=False, error="Script not found: S")])
        self.assertEqual(code, 1)
        self.assertIn("no tiene el guion", err)

    def test_without_confirmation_sends_nothing(self):
        code, _, _ = self.run_cli("--solution", "SolutionApp", "--script", "S", answer="n")
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [])

    def test_unknown_solution_sends_nothing(self):
        code, _, _ = self.run_cli("--solution", "NoExiste", "--script", "S", "--yes")
        self.assertEqual(code, 2)
        self.assertEqual(self.calls, [])

    def test_http_401_is_reported(self):
        code, _, err = self.run_cli("--solution", "SolutionApp", "--script", "S", "--yes",
                                    replies=[(401, {"error": "nope"})])
        self.assertEqual(code, 1)
        self.assertIn("401", err)

    def test_json_prints_the_envelope(self):
        code, out, _ = self.run_cli("--solution", "SolutionApp", "--script", "S", "--yes", "--json",
                                    replies=[_env(success=True, script="S", result="r")])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out[out.index("{"):]), {"success": True, "script": "S", "result": "r"})


class ParseVersionTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(rs.parse_version("1.5.0"), (1, 5, 0))
        self.assertEqual(rs.parse_version('"1.10.2"'), (1, 10, 2))
        for bad in ("", "abc", None, "1.5"):
            self.assertIsNone(rs.parse_version(bad))


if __name__ == "__main__":
    unittest.main()
