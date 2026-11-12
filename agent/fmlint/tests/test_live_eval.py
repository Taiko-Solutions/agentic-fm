"""Tests for C004 live evaluation target resolution and circuit breaker."""

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

from agent.fmlint.rules.live_eval import LiveEvalError

CALCS = [(i, f"Expr ( {i} )") for i in range(1, 6)]


def _make_handler(requests, responder):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            outer = json.loads(self.rfile.read(n))
            requests.append(json.loads(outer["scriptParameterValue"]))
            code, body, ctype = responder(requests[-1])
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    return H


def ok_verdict(result="1", **extra):
    v = {"success": True, "error_code": 0, "result": result}
    v.update(extra)
    return (200, _bridge(json.dumps(v)), "application/json")


def _bridge(result, script="AGFMEvaluation"):
    """Real AGFMScriptBridge envelope around AGFM Agent's verdict string."""
    rp = {"success": True, "script": script, "result": result}
    return json.dumps({"scriptResult": {"code": 0, "resultParameter": json.dumps(rp)}})


def _not_found(script):
    rp = {"success": False, "error": f"Script not found: {script}"}
    return (200, json.dumps({"scriptResult": {"code": 0, "resultParameter": json.dumps(rp)}}),
            "application/json")


class LiveEvalTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.responder = lambda p: ok_verdict()
        handler = _make_handler(self.requests, lambda p: self.responder(p))
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "agent" / "config").mkdir(parents=True)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def full(self):
        return {
            "base_url": f"http://127.0.0.1:{self.port}",
            "database": "SolutionApp",
            "username": "u",
            "password": "p",
        }

    def run_rule(self, solutions, solution="SolutionApp", layout="Lay"):
        (self.root / "agent" / "config" / "automation.json").write_text(
            json.dumps({"solutions": solutions}), encoding="utf-8"
        )
        ctx = SimpleNamespace(
            _project_root=self.root, solution_name=solution, layout_name=layout, available=True
        )
        return LiveEvalError()._evaluate_calcs(CALCS, ctx)

    def multi(self):
        return {
            "SolutionApp": {"odata": self.full()},
            "SolutionData": {"odata": {"via": "SolutionApp", "data_source": "Data"}},
        }

    def test_full_block_calls_agfmevaluation_without_data_source(self):
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(diags, [])
        self.assertEqual(len(self.requests), 5)
        self.assertEqual(self.requests[0]["script"], "AGFMEvaluation")
        inner = json.loads(self.requests[0]["parameter"])
        self.assertEqual(inner, {"expression": "Expr ( 1 )", "layout": "Lay"})

    def test_via_calls_agfmagentcall_on_the_main_with_mode_and_data_source(self):
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual(diags, [])
        self.assertEqual(self.requests[0]["script"], "AGFMAgentCall")
        inner = json.loads(self.requests[0]["parameter"])
        self.assertEqual(inner["mode"], "evaluate")
        self.assertEqual(inner["data_source"], "Data")
        self.assertEqual(inner["expression"], "Expr ( 1 )")
        self.assertEqual(inner["layout"], "Lay")

    def test_bad_via_gives_one_warning_and_no_request(self):
        sols = {"SolutionApp": {"odata": self.full()},
                "SolutionData": {"odata": {"via": "Nope", "data_source": "Data"}}}
        diags = self.run_rule(sols, solution="SolutionData")
        self.assertEqual(len(self.requests), 0)
        self.assertEqual([(d.rule_id, d.severity.name) for d in diags], [("C005", "WARNING")])

    def test_401_stops_after_one_request(self):
        self.responder = lambda p: (401, "{}", "application/json")
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("401", diags[0].message)
        self.assertIn("SolutionApp", diags[0].message)

    def test_old_main_without_agentcall_says_update_the_add_on(self):
        self.responder = lambda p: _not_found("AGFMAgentCall")
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("no tiene AGFMAgentCall", diags[0].message)
        self.assertIn("actualiza el add-on", diags[0].message)

    def test_main_without_agfmevaluation_says_install_the_add_on(self):
        self.responder = lambda p: _not_found("AGFMEvaluation")
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(diags), 1)
        self.assertIn("no tiene AGFMEvaluation", diags[0].message)

    def test_404_names_the_bridge_or_database(self):
        self.responder = lambda p: (404, "{}", "application/json")
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(diags), 1)
        self.assertIn("AGFMScriptBridge", diags[0].message)
        self.assertIn("404", diags[0].message)

    def test_evaluated_result_shaped_like_an_error_is_not_aborted(self):
        for evaluated in ('{"error":"boom"}', '{"success":false}'):
            self.requests.clear()
            self.responder = lambda p, e=evaluated: ok_verdict(result=e)
            diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
            self.assertEqual(diags, [])
            self.assertEqual(len(self.requests), 5)

    def test_agent_unreachable_stops(self):
        self.responder = lambda p: ok_verdict(error="agent_unreachable", error_code=7)
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("«Data»", diags[0].message)
        self.assertIn("error 7", diags[0].message)

    def test_question_mark_and_eval_error_are_still_c004(self):
        def resp(p):
            expr = json.loads(p["parameter"])["expression"]
            if expr == "Expr ( 1 )":
                return ok_verdict(result="?")
            if expr == "Expr ( 2 )":
                return (200, _bridge(json.dumps(
                    {"success": False, "error_code": 1200})), "application/json")
            return ok_verdict()
        self.responder = resp
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual([d.rule_id for d in diags], ["C004", "C004"])
        self.assertEqual([d.line for d in diags], [1, 2])

    def test_unknown_solution_with_two_entries_gives_one_warning(self):
        diags = self.run_rule(self.multi(), solution="Zzz")
        self.assertEqual(len(self.requests), 0)
        self.assertEqual([d.rule_id for d in diags], ["C005"])

    def test_secondary_without_odata_block_does_not_fall_back_to_main(self):
        sols = {"SolutionApp": {"odata": self.full()}, "SolutionData": {}}
        diags = self.run_rule(sols, solution="SolutionData")
        self.assertEqual(len(self.requests), 0)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("sin configuración OData para SolutionData", diags[0].message)

    def test_html_body_stops_with_one_warning(self):
        self.responder = lambda p: (200, "<html>proxy</html>", "text/html")
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])

    def test_unexpected_error_key_gives_one_warning(self):
        self.responder = lambda p: ok_verdict(error="bad_param")
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("bad_param", diags[0].message)

    def test_old_agent_message_is_in_the_warning(self):
        self.responder = lambda p: ok_verdict(error=-1, message="unknown mode: evaluate")
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("unknown mode: evaluate", diags[0].message)

    def test_non_dict_verdict_gives_one_warning(self):
        self.responder = lambda p: (200, json.dumps({"scriptResult": ["x"]}), "application/json")
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([d.rule_id for d in diags], ["C005"])
        self.assertIn("respuesta inesperada", diags[0].message)

    def test_agent_unreachable_without_data_source_has_no_none(self):
        self.responder = lambda p: ok_verdict(error="agent_unreachable", error_code=7)
        diags = self.run_rule({"SolutionApp": {"odata": self.full()}})
        self.assertEqual(len(diags), 1)
        self.assertNotIn("None", diags[0].message)

    def test_missing_credentials_gives_one_warning_and_no_request(self):
        odata = self.full()
        del odata["password"]
        diags = self.run_rule({"SolutionApp": {"odata": odata}})
        self.assertEqual(len(self.requests), 0)
        self.assertEqual([d.rule_id for d in diags], ["C005"])

    def test_question_mark_on_via_path_is_c004(self):
        self.responder = lambda p: ok_verdict(result="?")
        diags = self.run_rule(self.multi(), solution="SolutionData")
        self.assertEqual({d.rule_id for d in diags}, {"C004"})
        self.assertEqual(len(diags), 5)

    def test_no_base_url_anywhere_is_silent(self):
        diags = self.run_rule({"SolutionApp": {"odata": {}}})
        self.assertEqual(diags, [])
        self.assertEqual(len(self.requests), 0)


if __name__ == "__main__":
    unittest.main()
