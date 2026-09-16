#!/usr/bin/env python3
"""Loopback-safe binding for the companion server.

A client resolving ``localhost`` may try ``::1`` before ``127.0.0.1``. If the
companion only binds ``127.0.0.1``, any other process listening on ``::1`` with
the same port silently receives FileMaker's requests (real incident: a stray
``python3 -m http.server 8765`` made *Explode XML* fail with a JSON syntax error).

For loopback binds the companion therefore listens on BOTH loopback addresses,
and refuses to start if either one is already taken. Non-loopback binds keep a
single socket, exactly as before.
"""

import socket

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def ipv6_loopback_available() -> bool:
    """True when this host can bind an IPv6 socket on ``::1``."""
    if not socket.has_ipv6:
        return False
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as probe:
            probe.bind(("::1", 0))
        return True
    except OSError:
        return False


def bind_targets(bind_host: str) -> list[tuple[int, str]]:
    """Return the (family, host) pairs the companion must listen on."""
    host = (bind_host or "").strip()
    if host in LOOPBACK_HOSTS:
        targets = [(socket.AF_INET, "127.0.0.1")]
        if ipv6_loopback_available():
            targets.append((socket.AF_INET6, "::1"))
        return targets
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    return [(family, host)]
