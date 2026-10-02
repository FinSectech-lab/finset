import os
import pytest
from r0env.models import R0EnvConfig
from r0env.resolver import Resolver, GeoResult, PrivateAddressError, SourceConflictError, validate_public_ip
from r0env.adapters.egress import build_proxy_url, apply_kill_switch

def test_default_auto_correct_and_env_bypass(monkeypatch):
    c = R0EnvConfig(case_id="T")
    assert c.inspection.auto_correct == ["dns", "egress", "webrtc", "browser_context", "os_locale"]
    with pytest.raises(PermissionError): c.require_confirmation()
    monkeypatch.setenv("R0ENV_AUTO_APPLY", "1")
    assert c.auto_apply is True
    c.require_confirmation()

def test_private_ip_rejected():
    with pytest.raises(PrivateAddressError): validate_public_ip("192.168.1.1")

def test_conflicting_sources_rejected():
    providers = [lambda ip: GeoResult(ip, "US", timezone="America/Los_Angeles"), lambda ip: GeoResult(ip, "DE", timezone="Europe/Berlin")]
    with pytest.raises(SourceConflictError): Resolver(providers).resolve("8.8.8.8")

def test_proxy_and_killswitch_are_explicit():
    assert build_proxy_url("socks5://proxy.example:1080", "u", "p") == "socks5://u:p@proxy.example:1080"
    commands = apply_kill_switch(True, dry_run=True)
    assert commands and all(c.startswith("nft ") for c in commands)
