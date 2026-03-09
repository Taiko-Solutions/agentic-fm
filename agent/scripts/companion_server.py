#!/usr/bin/env python3
"""
companion_server.py - Lightweight HTTP companion server for agentic-fm.

Replaces the MBS FileMaker Plugin for shell command execution. FileMaker
calls this server via the native Insert from URL step (curl-compatible).

Usage:
    Start server:
        python agent/scripts/companion_server.py

    Start on custom port:
        python agent/scripts/companion_server.py --port 9000

    FileMaker calls it via Insert from URL:
        POST http://localhost:8765/explode
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PORT = 8765
BIND_HOST = "127.0.0.1"
VERSION = "1.0"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("companion_server")


# ---------------------------------------------------------------------------
# Threading HTTP server (handles concurrent requests)
# ---------------------------------------------------------------------------

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer with thread-per-request concurrency."""
    daemon_threads = True


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class CompanionHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        """Route access log through the standard logger."""
        log.info("%s - %s", self.address_string(), fmt % args)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def do_GET(self):
        if self.path == "/health":
            self._handle_health()
        else:
            self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        if self.path == "/explode":
            self._handle_explode()
        else:
            self._send_json({"error": "Not found"}, status=404)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_health(self):
        self._send_json({"status": "ok", "version": VERSION})

    def _handle_explode(self):
        # Read and parse request body
        try:
            body = self._read_body()
            payload = json.loads(body)
        except (ValueError, OSError) as exc:
            self._send_json(
                {"success": False, "exit_code": -1, "error": f"Invalid request: {exc}"},
                status=400,
            )
            return

        # Validate required fields
        missing = [
            f for f in ("solution_name", "export_file_path", "repo_path")
            if not payload.get(f)
        ]
        if missing:
            self._send_json(
                {
                    "success": False,
                    "exit_code": -1,
                    "error": f"Missing required fields: {', '.join(missing)}",
                },
                status=400,
            )
            return

        solution_name = payload["solution_name"]
        export_file_path = payload["export_file_path"]
        repo_path = payload["repo_path"]
        exploder_bin_path = payload.get("exploder_bin_path", "")

        # Expand ~ in paths
        repo_path = os.path.expanduser(repo_path)
        export_file_path = os.path.expanduser(export_file_path)

        # Build environment for subprocess
        env = os.environ.copy()
        if exploder_bin_path:
            env["FM_XML_EXPLODER_BIN"] = os.path.expanduser(exploder_bin_path)

        # Build command: {repo_path}/fmparse.sh -s "{solution_name}" "{export_file_path}"
        fmparse = os.path.join(repo_path, "fmparse.sh")
        cmd = [fmparse, "-s", solution_name, export_file_path]

        log.info(
            "Running fmparse.sh: solution=%r export=%r cwd=%r",
            solution_name,
            export_file_path,
            repo_path,
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            success = result.returncode == 0
            response = {
                "success": success,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            status = 200 if success else 500

            log.info(
                "fmparse.sh exited with code %d", result.returncode
            )

        except Exception as exc:
            log.exception("Exception running fmparse.sh: %s", exc)
            response = {
                "success": False,
                "exit_code": -1,
                "error": str(exc),
            }
            status = 500

        self._send_json(response, status=status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length > 0 else b""

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="agentic-fm companion server — exposes fmparse.sh over HTTP for FileMaker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    port = args.port

    server = ThreadingHTTPServer((BIND_HOST, port), CompanionHandler)

    log.info("companion_server v%s listening on %s:%d", VERSION, BIND_HOST, port)
    log.info("Endpoints: GET /health  POST /explode")
    log.info("Press Ctrl-C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
