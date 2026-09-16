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


if __name__ == "__main__":
    unittest.main()
