#!/usr/bin/env python3
"""Tests for refresh_context.py: context over OData, local delivery to the app."""

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
import refresh_context as rc  # noqa: E402

CONTEXT = {"solution": "SolutionData", "task": "t", "current_layout": {"name": "L"}}


def _ctx_for(param):
    """Context AGFM Agent 1.1.0 would answer for this call."""
    return {"solution": "SolutionData" if param.get("data_source") else "SolutionApp",
            "task": param.get("task"),
            "current_layout": {"name": param.get("layout") or "L"}}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        srv = self.server
        srv.requests.append({"path": self.path, "body": json.loads(body)})
        if self.path == "/context":
            self._send(200, {"success": True, "path": "/x"})
            return
        call = json.loads(json.loads(body)["scriptParameterValue"])
        script = call["script"]
        if srv.script_replies:
            status, payload = srv.script_replies.pop(0)
        elif srv.default is not None:
            status, payload = 200, srv.default
        else:
            status, payload = 200, _bridge_ok(_ctx_for(json.loads(call["parameter"])), script)
        if script == "Push Context" and status == 200:
            rc.CONTEXT_PATH.write_text(json.dumps(CONTEXT), encoding="utf-8")
        self._send(status, payload)

    def _send(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, *args):
        pass


def _bridge_ok(ctx, script="AGFMAgentCall"):
    """Real AGFMScriptBridge envelope: the verdict travels as a string in `result`."""
    rp = {"success": True, "script": script, "result": json.dumps(ctx)}
    return {"scriptResult": {"code": 0, "resultParameter": json.dumps(rp)}}


def _not_found(script):
    rp = {"success": False, "error": f"Script not found: {script}"}
    return {"scriptResult": {"code": 0, "resultParameter": json.dumps(rp)}}


class RefreshContextTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.server.requests = []
        self.server.script_replies = []
        self.server.default = None
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "agent" / "config").mkdir(parents=True)
        self.root = root
        main_odata = {"base_url": self.url, "database": "SolutionApp",
                      "username": "u", "password": "p"}
        self.solutions = {"SolutionApp": {"odata": main_odata},
                          "SolutionData": {"odata": {"via": "SolutionApp", "data_source": "Data"}}}
        self._write_automation()
        (root / "agent" / "config" / "companion.json").write_text(json.dumps(
            {"companion": {"advertise_host": "127.0.0.1", "port": self.server.server_port}}))
        for name, value in (("REPO_ROOT", root), ("CONTEXT_PATH", root / "agent" / "CONTEXT.json"),
                            ("AUTOMATION_PATH", root / "agent" / "config" / "automation.json")):
            p = mock.patch.object(rc, name, value)
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def _write_automation(self):
        (self.root / "agent" / "config" / "automation.json").write_text(
            json.dumps({"solutions": self.solutions}))

    def _run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["refresh_context.py", *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = rc.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                err.write(str(exc.code) if not isinstance(exc.code, int) else "")
        return code, out.getvalue(), err.getvalue()

    def _bridge_requests(self):
        return [r for r in self.server.requests if r["path"] != "/context"]

    def _scripts(self):
        return [json.loads(r["body"]["scriptParameterValue"]) for r in self._bridge_requests()]

    def test_secondary_fetches_context_through_the_main_and_posts_it_to_the_app(self):
        code, _, _ = self._run("--task", "t", "--solution", "SolutionData", "--yes")
        self.assertEqual(code, 0)
        bridge = self._bridge_requests()
        self.assertEqual(len(bridge), 1)
        self.assertEqual(bridge[0]["path"], "/SolutionApp/Script.AGFMScriptBridge")
        call = self._scripts()[0]
        self.assertEqual(call["script"], "AGFMAgentCall")
        self.assertEqual(json.loads(call["parameter"]),
                         {"mode": "context", "task": "t", "data_source": "Data"})
        posts = [r for r in self.server.requests if r["path"] == "/context"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["body"]["context"]["solution"], "SolutionData")
        self.assertFalse(rc.CONTEXT_PATH.exists())

    def test_when_the_app_is_down_context_json_is_written(self):
        (self.root / "agent" / "config" / "companion.json").write_text(json.dumps(
            {"companion": {"advertise_host": "127.0.0.1", "port": 1}}))
        code, _, err = self._run("--task", "t", "--solution", "SolutionData", "--yes")
        self.assertEqual(code, 0)
        self.assertIn("la app no respondió", err)
        self.assertIn("tarea no registrada", err)
        self.assertEqual(json.loads(rc.CONTEXT_PATH.read_text(encoding="utf-8"))["solution"],
                         "SolutionData")

    def test_main_with_layout_sends_one_request(self):
        code, _, _ = self._run("--task", "t", "--layout", "L", "--solution", "SolutionApp", "--yes")
        self.assertEqual(code, 0)
        calls = self._scripts()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["script"], "AGFMAgentCall")
        self.assertEqual(json.loads(calls[0]["parameter"]),
                         {"mode": "context", "task": "t", "layout": "L"})
        self.assertNotIn("AGFMGoToLayout", [c["script"] for c in calls])

    def test_old_main_falls_back_to_push_context_with_layout(self):
        self.server.script_replies = [(200, _not_found("AGFMAgentCall"))]
        code, _, _ = self._run("--task", "t", "--layout", "L", "--solution", "SolutionApp",
                               "--yes", "--timeout", "3")
        self.assertEqual(code, 0)
        calls = self._scripts()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["script"], "Push Context")
        self.assertEqual(json.loads(calls[1]["parameter"])["layout"], "L")

    def test_old_main_with_secondary_is_a_clear_error(self):
        self.server.script_replies = [(200, _not_found("AGFMAgentCall"))]
        code, _, err = self._run("--task", "t", "--solution", "SolutionData", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("add-on", err)
        self.assertEqual(len(self._bridge_requests()), 1)

    def test_404_names_the_bridge_and_does_not_fall_back(self):
        self.server.script_replies = [(404, {"error": "not found"})]
        code, _, err = self._run("--task", "t", "--solution", "SolutionApp", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("AGFMScriptBridge", err)
        self.assertEqual(len(self._bridge_requests()), 1)

    def test_context_of_another_file_is_rejected(self):
        self.server.script_replies = [(200, _bridge_ok(
            {"solution": "SolutionApp", "current_layout": {"name": "L"}}))]
        code, _, err = self._run("--task", "t", "--solution", "SolutionData", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("anterior a 1.1.0", err)
        self.assertFalse(rc.CONTEXT_PATH.exists())

    def test_context_of_another_layout_is_rejected(self):
        self.server.script_replies = [(200, _bridge_ok(
            {"solution": "SolutionApp", "current_layout": {"name": "Other"}}))]
        code, _, err = self._run("--task", "t", "--layout", "L", "--solution", "SolutionApp", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("anterior a 1.1.0", err)

    def test_solution_argument_accepts_extension_and_case(self):
        code, _, _ = self._run("--task", "t", "--solution", "solutiondata.fmp12", "--yes")
        self.assertEqual(code, 0)

    def test_auto_falls_back_to_companion_and_prints_the_config_error(self):
        self.solutions = {"SolutionApp": {}}
        self._write_automation()
        with mock.patch.object(rc, "via_companion") as vc:
            def fake(url, script, param, target=""):
                if script == "Push Context":
                    rc.CONTEXT_PATH.write_text(json.dumps(CONTEXT), encoding="utf-8")
            vc.side_effect = fake
            code, _, err = self._run("--task", "t", "--solution", "SolutionApp", "--yes",
                                     "--timeout", "3")
        self.assertEqual(code, 0)
        self.assertIn("OData no disponible", err)
        self.assertIn("SolutionApp", err)


if __name__ == "__main__":
    unittest.main()
