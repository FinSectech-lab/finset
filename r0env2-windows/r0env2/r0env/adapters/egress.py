"""Explicit SOCKS5 egress configuration and verification."""
from __future__ import annotations
import json, os, subprocess, urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

class EgressError(RuntimeError): pass
@dataclass
class EgressState:
    proxy_url: str | None
    env: dict[str, str]
    kill_switch: bool

def build_proxy_url(endpoint: str, username: str | None = None, password: str | None = None) -> str:
    p = urlparse(endpoint)
    if p.scheme not in {"socks5", "socks5h", "http", "https"} or not p.hostname or not p.port: raise EgressError("proxy endpoint must include supported scheme, host and port")
    if username is not None:
        from urllib.parse import quote
        auth = f"{quote(username)}:{quote(password or '')}@"
        return f"{p.scheme}://{auth}{p.hostname}:{p.port}"
    return endpoint

def inject_proxy(endpoint: str, username: str | None = None, password: str | None = None) -> EgressState:
    proxy = build_proxy_url(endpoint, username, password)
    env = {k: proxy for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")}
    return EgressState(proxy, env, False)

def apply_kill_switch(enabled: bool, runner=subprocess.run, dry_run: bool = True) -> list[str]:
    # Explicit emergency outbound block; never enabled by normal apply.
    from ..windows import powershell
    command = ("if (-not (Get-NetFirewallRule -Name 'r0env2-kill-switch' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -Name 'r0env2-kill-switch' -DisplayName 'r0env2 emergency outbound block' -Direction Outbound -Action Block -Profile Any | Out-Null }"
               if enabled else "Get-NetFirewallRule -Name 'r0env2-kill-switch' -ErrorAction SilentlyContinue | Remove-NetFirewallRule")
    if not dry_run:
        if runner is subprocess.run:
            powershell(command)
        else:
            runner(command, check=True)
    return [command]


def verify_egress(check_url: str = "https://ipwho.is/", expected_asn: set[str] | None = None, opener=None) -> dict:
    opener = opener or urllib.request.build_opener()
    with opener.open(check_url, timeout=10) as response: data = json.load(response)
    if data.get("success") is False: raise EgressError("egress probe failed")
    observed = str((data.get("connection") or {}).get("asn") or "")
    if expected_asn and observed not in expected_asn: raise EgressError(f"ASN mismatch: observed {observed}, expected {sorted(expected_asn)}")
    return {"ip": data.get("ip"), "asn": observed, "country_code": data.get("country_code"), "source": check_url}
