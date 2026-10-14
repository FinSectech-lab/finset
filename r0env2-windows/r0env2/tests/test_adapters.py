from r0env.adapters.dns import DNSAdapter, DNSState, dns_leak_probe
from r0env.adapters.webrtc import WebRTCAdapter, WebRTCState, classify_candidates
from r0env.adapters.browser import BrowserAdapter, BrowserProfile

def test_dns_plan_dry_run_and_leak():
    a = DNSAdapter(); d = a.plan(DNSState(), DNSState(mode="doh", servers=["https://dns.test/query"], fallback="deny"))
    assert a.apply(d)["dry_run"] and d["fallback_blocked"]
    assert dns_leak_probe(lambda _: "9.9.9.9", {"1.1.1.1"})["leak"]

def test_webrtc_policy_and_real_ip_detection():
    a = WebRTCAdapter(); diff = a.plan(WebRTCState(), WebRTCState())
    assert "--force-webrtc-ip-handling-policy=proxy_only" in diff["chromium_args"]
    result = a.verify(WebRTCState(), ["candidate 10.0.0.2 123 typ host", "candidate 203.0.113.9 123 typ srflx"], {"10.0.0.2"})
    assert not result["ok"] and result["leaks"] == ["10.0.0.2"]

def test_browser_isolated_context_dry_run_and_verify():
    profile = BrowserProfile(user_agent="UA", locale="en-US", timezone_id="UTC", viewport={"width": 800, "height": 600}, device_scale_factor=2, color_scheme="dark")
    a = BrowserAdapter(); diff = a.plan({}, profile); assert a.apply(diff)["dry_run"]
    actual = diff["context_options"].copy(); assert a.verify(profile, actual)["ok"]
    actual["locale"] = "de-DE"; assert not a.verify(profile, actual)["ok"]
