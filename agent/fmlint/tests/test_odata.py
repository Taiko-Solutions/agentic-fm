"""Tests for agent/fmlint/odata.py (OData resolution and Bridge transport)."""

import json
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent.fmlint.odata import (
    BridgeError,
    ODataConfigError,
    ScriptMissing,
    Target,
    bridge_call,
    find_key,
    load_solutions,
    resolve,
    unwrap,
)

FULL = {
    "base_url": "http://127.0.0.1:1",
    "database": "SolutionApp",
    "username": "user",
    "password": "pass",
}


class ResolveTests(unittest.TestCase):
    def test_full_block_targets_its_own_file(self):
        t = resolve({"SolutionApp": {"odata": FULL}}, "SolutionApp")
        self.assertEqual(t, Target(FULL, None, "SolutionApp"))

    def test_via_targets_the_main_with_its_data_source(self):
        sols = {
            "SolutionApp": {"odata": FULL},
            "SolutionData": {"odata": {"via": "SolutionApp", "data_source": "Data"}},
        }
        self.assertEqual(resolve(sols, "SolutionData"), Target(FULL, "Data", "SolutionApp"))

    def test_name_with_extension_and_other_case_resolves(self):
        sols = {
            "SolutionApp": {"odata": FULL},
            "SolutionData": {"odata": {"via": "SolutionApp", "data_source": "Data"}},
        }
        self.assertEqual(resolve(sols, "solutiondata.fmp12").data_source, "Data")
        sols2 = {
            "SolutionApp.fmp12": {"odata": FULL},
            "SolutionData.fmp12": {"odata": {"via": "SolutionApp", "data_source": "Data"}},
        }
        self.assertEqual(resolve(sols2, "SolutionData").data_source, "Data")
        self.assertEqual(resolve(sols2, "SolutionData").main, "SolutionApp.fmp12")

    def test_via_accepts_extension_in_reference(self):
        sols = {
            "SolutionApp": {"odata": FULL},
            "SolutionData": {"odata": {"via": "SolutionApp.fmp12", "data_source": "Data"}},
        }
        self.assertEqual(resolve(sols, "SolutionData").main, "SolutionApp")

    def test_unknown_name_with_several_solutions_is_an_error(self):
        sols = {"A": {"odata": FULL}, "B": {"odata": FULL}}
        with self.assertRaises(ODataConfigError):
            resolve(sols, "Zzz")
        with self.assertRaises(ODataConfigError):
            resolve(sols, None)

    def test_unknown_name_with_one_solution_uses_it(self):
        sols = {"SolutionApp": {"odata": FULL}}
        self.assertEqual(resolve(sols, "Other").main, "SolutionApp")
        self.assertEqual(resolve(sols, "").main, "SolutionApp")

    def test_via_to_missing_key_is_an_error(self):
        sols = {"SolutionData": {"odata": {"via": "Nope", "data_source": "Data"}}}
        with self.assertRaises(ODataConfigError):
            resolve(sols, "SolutionData")

    def test_via_chain_is_an_error(self):
        sols = {
            "A": {"odata": FULL},
            "B": {"odata": {"via": "A", "data_source": "B"}},
            "C": {"odata": {"via": "B", "data_source": "C"}},
        }
        with self.assertRaises(ODataConfigError):
            resolve(sols, "C")

    def test_main_without_base_url_is_an_error(self):
        sols = {
            "A": {"odata": {"database": "A"}},
            "B": {"odata": {"via": "A", "data_source": "B"}},
        }
        with self.assertRaises(ODataConfigError):
            resolve(sols, "B")

    def test_solution_without_odata_is_an_error(self):
        with self.assertRaises(ODataConfigError):
            resolve({"SolutionApp": {}}, "SolutionApp")


class FindKeyTests(unittest.TestCase):
    def test_find_key_ignores_extension_and_case(self):
        self.assertEqual(find_key({"SolutionApp": {}}, "solutionapp.FMP12"), "SolutionApp")
        self.assertIsNone(find_key({"SolutionApp": {}}, "Other"))


class LoadSolutionsTests(unittest.TestCase):
    def test_missing_file_gives_empty_dict(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_solutions(Path(d)), {})

    def test_reads_solutions_and_rejects_bad_json(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "agent" / "config"
            cfg.mkdir(parents=True)
            (cfg / "automation.json").write_text(json.dumps({"solutions": {"X": {}}}))
            self.assertEqual(load_solutions(Path(d)), {"X": {}})
            (cfg / "automation.json").write_text("{not json")
            with self.assertRaises(ODataConfigError):
                load_solutions(Path(d))


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        self.server.seen = {"path": self.path, "headers": dict(self.headers), "body": body}
        status, ctype, payload = self.server.reply
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, *args):
        pass


class BridgeCallTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.server.seen = None
        self.server.reply = (200, "application/json", "{}")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.odata = dict(FULL, base_url=f"http://127.0.0.1:{self.server.server_port}")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_bridge_call_posts_the_double_serialized_payload(self):
        self.server.reply = (200, "application/json", json.dumps(
            {"scriptResult": {"code": 0, "resultParameter": json.dumps({"success": True})}}))
        param = json.dumps({"data_source": "Datos Históricos"}, ensure_ascii=False)
        out = bridge_call(self.odata, "AGFMAgentCall", param)
        self.assertEqual(out, {"success": True})
        seen = self.server.seen
        self.assertEqual(seen["path"], "/SolutionApp/Script.AGFMScriptBridge")
        self.assertTrue(seen["headers"]["Authorization"].startswith("Basic "))
        inner = json.loads(json.loads(seen["body"])["scriptParameterValue"])
        self.assertEqual(inner, {"script": "AGFMAgentCall", "parameter": param})
        self.assertEqual(json.loads(inner["parameter"])["data_source"], "Datos Históricos")

    def test_http_401_raises_bridge_error_with_status(self):
        self.server.reply = (401, "text/plain", "no")
        with self.assertRaises(BridgeError) as cm:
            bridge_call(self.odata, "S", "")
        self.assertEqual(cm.exception.status, 401)

    def test_404_raises_bridge_error_with_status(self):
        self.server.reply = (404, "text/plain", "no")
        with self.assertRaises(BridgeError) as cm:
            bridge_call(self.odata, "S", "")
        self.assertEqual(cm.exception.status, 404)

    def test_script_not_found_envelope_raises_script_missing(self):
        self.server.reply = (200, "application/json", json.dumps(
            _envelope({"success": False, "error": "Script not found: AGFMAgentCall"})))
        with self.assertRaises(ScriptMissing) as cm:
            bridge_call(self.odata, "AGFMAgentCall", "")
        self.assertEqual(cm.exception.script, "AGFMAgentCall")
        self.assertIsInstance(cm.exception, BridgeError)

    def test_other_bridge_failure_is_not_script_missing(self):
        self.server.reply = (200, "application/json", json.dumps(
            _envelope({"success": False, "error": "boom"})))
        self.assertEqual(bridge_call(self.odata, "S", ""), {"success": False, "error": "boom"})

    def test_unreachable_host_raises_bridge_error_without_status(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        with self.assertRaises(BridgeError) as cm:
            bridge_call(dict(FULL, base_url=f"http://127.0.0.1:{port}"), "S", "", timeout=3)
        self.assertIsNone(cm.exception.status)

    def test_html_body_raises_bridge_error(self):
        self.server.reply = (200, "text/html", "<html>proxy</html>")
        with self.assertRaises(BridgeError) as cm:
            bridge_call(self.odata, "S", "")
        self.assertIsNone(cm.exception.status)

    def test_missing_credentials_is_a_config_error(self):
        with self.assertRaises(ODataConfigError):
            bridge_call(dict(self.odata, password=""), "S", "")


def _envelope(bridge, code=0):
    return {"scriptResult": {"code": code, "resultParameter": json.dumps(bridge)}}


def _real(result, script="AGFMAgentCall"):
    return _envelope({"success": True, "script": script, "result": result})


class UnwrapTests(unittest.TestCase):
    def test_unwrap_peels_three_layers(self):
        body = _real(json.dumps({"solution": "SolutionData"}))
        self.assertEqual(unwrap(body), {"solution": "SolutionData"})

    def test_evaluated_result_that_looks_like_an_envelope_is_not_peeled(self):
        for evaluated in ('{"error":"boom"}', '{"success":false}'):
            verdict = {"success": True, "error_code": 0, "result": evaluated,
                       "expression": "x"}
            out = unwrap(_real(json.dumps(verdict)))
            self.assertEqual(out, verdict)
            self.assertEqual(out["result"], evaluated)

    def test_verdict_in_result_parameter_is_not_peeled_again(self):
        verdict = {"success": True, "error_code": 0, "result": '{"error":"boom"}'}
        self.assertEqual(unwrap(_envelope(verdict)), verdict)

    def test_unwrap_plain_result_is_untouched(self):
        body = {"scriptResult": {"resultParameter": json.dumps({"success": True, "result": "42"})}}
        self.assertEqual(unwrap(body), {"success": True, "result": "42"})


if __name__ == "__main__":
    unittest.main()
