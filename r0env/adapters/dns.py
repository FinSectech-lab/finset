"""DNS configuration planning and leak probes; apply is dry-run by default."""
from __future__ import annotations
import socket
from dataclasses import dataclass, field
from typing import Any, Callable

class DNSError(RuntimeError): pass
@dataclass
class DNSState:
    mode: str = "system"
    servers: list[str] = field(default_factory=list)
    fallback: str = "deny"
    observed_server: str | None = None

class DNSAdapter:
    def __init__(self, target: Any = None, runner: Callable | None = None): self.target, self.runner = target, runner
    def discover(self) -> DNSState:
        return DNSState()
    def plan(self, observed: DNSState, desired: DNSState) -> dict:
        if desired.mode not in {"system", "udp", "dot", "doh"}: raise DNSError(f"unsupported DNS mode: {desired.mode}")
        if desired.mode != "system" and not desired.servers: raise DNSError("servers required for non-system DNS")
        return {"changes": {"mode": desired.mode, "servers": desired.servers, "fallback": desired.fallback}, "fallback_blocked": desired.fallback == "deny"}
    def apply(self, diff: dict, snapshot: dict | None = None, dry_run: bool = True) -> dict:
        if not dry_run and self.runner is None: raise DNSError("runner required for non-dry-run apply")
        if not dry_run: self.runner(diff)
        return {"applied": not dry_run, "dry_run": dry_run, "diff": diff}
    def verify(self, desired: DNSState, probe: Callable[[str], str | None] | None = None) -> dict:
        probe = probe or (lambda host: socket.gethostbyname(host))
        if desired.fallback == "deny" and not desired.servers: return {"ok": False, "reason": "fallback denied but no DNS server configured"}
        try: probe("example.com")
        except OSError as exc: return {"ok": False, "reason": f"DNS probe failed: {exc}"}
        return {"ok": True, "leak": False, "mode": desired.mode, "servers": desired.servers}
    def rollback(self, snapshot: DNSState | dict, dry_run: bool = True) -> dict: return {"rolled_back": not dry_run, "dry_run": dry_run, "snapshot": snapshot}

def dns_leak_probe(resolve: Callable[[str], str | None], expected_servers: set[str]) -> dict:
    observed = resolve("whoami.dns.example")
    leak = observed is not None and observed not in expected_servers
    return {"observed_server": observed, "expected_servers": sorted(expected_servers), "leak": leak, "ok": not leak}

class Adapter(DNSAdapter): pass
