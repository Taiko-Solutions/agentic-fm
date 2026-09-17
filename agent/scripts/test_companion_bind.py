#!/usr/bin/env python3
"""Unit tests for companion_bind (loopback-safe binding for the companion server).

Usage:
    python3 agent/scripts/test_companion_bind.py
"""

import socket
import sys
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

sys.path.insert(0, str(Path(__file__).resolve().parent))

import companion_bind as cb


class TestBindTargets(unittest.TestCase):

    def test_loopback_ipv4_host_includes_ipv6_loopback_when_available(self):
        targets = cb.bind_targets("127.0.0.1")
        self.assertIn((socket.AF_INET, "127.0.0.1"), targets)
        if cb.ipv6_loopback_available():
            self.assertIn((socket.AF_INET6, "::1"), targets)
        else:
            self.assertEqual(targets, [(socket.AF_INET, "127.0.0.1")])

    def test_localhost_name_is_treated_as_loopback(self):
        self.assertEqual(cb.bind_targets("localhost"), cb.bind_targets("127.0.0.1"))

    def test_wildcard_bind_is_left_unchanged(self):
        self.assertEqual(cb.bind_targets("0.0.0.0"), [(socket.AF_INET, "0.0.0.0")])

    def test_specific_non_loopback_address_is_single_target(self):
        self.assertEqual(cb.bind_targets("192.168.1.20"), [(socket.AF_INET, "192.168.1.20")])


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPortConflicts(unittest.TestCase):

    def test_free_port_has_no_conflicts(self):
        port = _free_port()
        self.assertEqual(cb.port_conflicts(cb.bind_targets("127.0.0.1"), port), [])

    def test_ipv4_squatter_is_reported(self):
        squatter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        squatter.bind(("127.0.0.1", 0))
        squatter.listen(1)
        port = squatter.getsockname()[1]
        try:
            conflicts = cb.port_conflicts(cb.bind_targets("127.0.0.1"), port)
            self.assertEqual(len(conflicts), 1)
            self.assertIn(f"127.0.0.1:{port}", conflicts[0])
        finally:
            squatter.close()

    @unittest.skipUnless(cb.ipv6_loopback_available(), "no IPv6 loopback")
    def test_ipv6_squatter_is_reported_even_if_ipv4_is_free(self):
        squatter = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        squatter.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        squatter.bind(("::1", 0))
        squatter.listen(1)
        port = squatter.getsockname()[1]
        try:
            conflicts = cb.port_conflicts(cb.bind_targets("127.0.0.1"), port)
            self.assertEqual(len(conflicts), 1)
            self.assertIn(f"[::1]:{port}", conflicts[0])
        finally:
            squatter.close()

    def test_port_owner_names_a_process_for_a_listening_port(self):
        squatter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        squatter.bind(("127.0.0.1", 0))
        squatter.listen(1)
        port = squatter.getsockname()[1]
        try:
            owner = cb.port_owner(port)
            # lsof may be missing on some hosts; when present it names this process.
            if owner:
                self.assertIn("pid", owner)
        finally:
            squatter.close()


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"status": "ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class TestServerGroup(unittest.TestCase):

    def _start_group(self):
        port = _free_port()
        targets = cb.bind_targets("127.0.0.1")
        group = cb.ServerGroup(cb.build_servers(_ThreadingHTTPServer, targets, port, _OkHandler))
        thread = threading.Thread(target=group.serve_forever, daemon=True)
        thread.start()
        return group, thread, port

    def _stop_group(self, group, thread):
        group.shutdown()
        group.server_close()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())

    def test_group_answers_on_ipv4_loopback(self):
        group, thread, port = self._start_group()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                self.assertEqual(r.status, 200)
        finally:
            self._stop_group(group, thread)

    @unittest.skipUnless(cb.ipv6_loopback_available(), "no IPv6 loopback")
    def test_group_answers_on_ipv6_loopback(self):
        group, thread, port = self._start_group()
        try:
            with urllib.request.urlopen(f"http://[::1]:{port}/health", timeout=5) as r:
                self.assertEqual(r.status, 200)
        finally:
            self._stop_group(group, thread)

    @unittest.skipUnless(cb.ipv6_loopback_available(), "no IPv6 loopback")
    def test_after_start_the_ipv6_half_is_no_longer_free(self):
        group, thread, port = self._start_group()
        try:
            conflicts = cb.port_conflicts([(socket.AF_INET6, "::1")], port)
            self.assertEqual(len(conflicts), 1)
        finally:
            self._stop_group(group, thread)

    def test_describe_lists_every_address(self):
        group, thread, port = self._start_group()
        try:
            text = group.describe()
            self.assertIn(f"127.0.0.1:{port}", text)
            if cb.ipv6_loopback_available():
                self.assertIn(f"[::1]:{port}", text)
        finally:
            self._stop_group(group, thread)


if __name__ == "__main__":
    unittest.main()
