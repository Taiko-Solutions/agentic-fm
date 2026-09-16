#!/usr/bin/env python3
"""Unit tests for companion_bind (loopback-safe binding for the companion server).

Usage:
    python3 agent/scripts/test_companion_bind.py
"""

import socket
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
