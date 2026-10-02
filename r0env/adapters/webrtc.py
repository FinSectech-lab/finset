"""Chromium WebRTC policy generation and ICE candidate inspection."""
from __future__ import annotations
from dataclasses import dataclass, field
import ipaddress, re
from typing import Any

@dataclass
class WebRTCState:
    policy: str = "proxy_only"
    allow_udp: bool = False
    stun_servers: list[str] = field(default_factory=list)

class WebRTCAdapter:
    def __init__(self, target: Any = None): self.target = target
    def discover(self) -> WebRTCState: return WebRTCState()
    def plan(self, observed: WebRTCState, desired: WebRTCState) -> dict:
        if desired.policy not in {"default", "proxy_only"}: raise ValueError("unsupported Chromium IP handling policy")
        args = [f"--force-webrtc-ip-handling-policy={desired.policy}"]
        if not desired.allow_udp: args.append("--webrtc-stun-probe-trial=Disabled")
        return {"chromium_args": args, "policy": desired.policy, "allow_udp": desired.allow_udp, "stun_servers": desired.stun_servers}
    def apply(self, diff: dict, snapshot: dict | None = None, dry_run: bool = True) -> dict: return {"applied": not dry_run, "dry_run": dry_run, "diff": diff}
    def verify(self, desired: WebRTCState, candidates: list[str] | None = None, protected_ips: set[str] | None = None) -> dict:
        result = classify_candidates(candidates or [])
        leaks = real_ip_leaks(result, protected_ips or set())
        return {"ok": not leaks, "leaks": leaks, "candidates": result, "policy": desired.policy}
    def rollback(self, snapshot: dict, dry_run: bool = True) -> dict: return {"rolled_back": not dry_run, "dry_run": dry_run, "snapshot": snapshot}

def classify_candidates(candidates: list[str]) -> dict[str, list[str]]:
    out = {"host": [], "srflx": [], "relay": [], "unknown": []}
    for candidate in candidates:
        kind = "unknown"
        if " typ host" in candidate: kind = "host"
        elif " typ srflx" in candidate: kind = "srflx"
        elif " typ relay" in candidate: kind = "relay"
        out[kind].append(candidate)
    return out

def candidate_ips(candidates: list[str]) -> set[str]:
    found = set()
    for c in candidates:
        for token in re.findall(r"(?<![\w:])(?:\d{1,3}\.){3}\d{1,3}(?!\w)", c):
            try: ipaddress.ip_address(token); found.add(token)
            except ValueError: pass
    return found

def real_ip_leaks(classified: dict[str, list[str]], protected_ips: set[str]) -> list[str]:
    if not protected_ips: return []
    leaks = []
    for kind in ("host", "srflx"):
        for c in classified.get(kind, []):
            leaks.extend(sorted(candidate_ips([c]) & protected_ips))
    return sorted(set(leaks))

class Adapter(WebRTCAdapter): pass
