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
import subprocess

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


def _format_address(family: int, host: str, port: int) -> str:
    return f"[{host}]:{port}" if family == socket.AF_INET6 else f"{host}:{port}"


def port_owner(port: int) -> str:
    """Describe which process listens on ``port`` (via lsof). Empty if unknown."""
    try:
        out = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpc"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    owners = []
    pid = ""
    for line in out.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("c"):
            owners.append(f"{line[1:]} (pid {pid})")
    return ", ".join(dict.fromkeys(owners))


def port_conflicts(targets: list[tuple[int, str]], port: int) -> list[str]:
    """Try to bind every target; return one line per address that is taken.

    The probe mirrors the real server socket options (SO_REUSEADDR, and
    IPV6_V6ONLY for IPv6) so a free port is never reported as taken.
    """
    conflicts = []
    owner = None
    for family, host in targets:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            try:
                probe.bind((host, port))
            except OSError as exc:
                if owner is None:
                    owner = port_owner(port)
                detail = exc.strerror or str(exc)
                suffix = f" — in use by {owner}" if owner else ""
                conflicts.append(f"{_format_address(family, host, port)} ({detail}){suffix}")
    return conflicts
