#!/usr/bin/env python3
"""r0env auto-apply"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request
from pathlib import Path
from dataclasses import asdict, is_dataclass

PROJ = Path(__file__).parent
sys.path.insert(0, str(PROJ))

from r0env.resolver import Resolver, ipwho_provider
from r0env.adapters.dns import DNSAdapter, DNSState
from r0env.adapters.webrtc import WebRTCAdapter, WebRTCState
from r0env.adapters.browser import BrowserAdapter, BrowserProfile

PROXY = os.environ.get("R0ENV_PROXY", "http://127.0.0.1:7890")
DEFAULT_ENGINE = os.environ.get("R0ENV_ENGINE", "firefox")

LOCALE_MAP = {
    "US": ("en_US.UTF-8", "en-US"), "GB": ("en_GB.UTF-8", "en-GB"),
    "JP": ("ja_JP.UTF-8", "ja-JP"), "CN": ("zh_CN.UTF-8", "zh-CN"),
    "DE": ("de_DE.UTF-8", "de-DE"), "FR": ("fr_FR.UTF-8", "fr-FR"),
    "KR": ("ko_KR.UTF-8", "ko-KR"), "SG": ("en_SG.UTF-8", "en-SG"),
    "HK": ("zh_HK.UTF-8", "zh-HK"), "TW": ("zh_TW.UTF-8", "zh-TW"),
    "AU": ("en_AU.UTF-8", "en-AU"), "CA": ("en_CA.UTF-8", "en-CA"),
}
DEFAULT_LOCALE = ("en_US.UTF-8", "en-US")


def detect_exit_ip(proxy=None, timeout=8):
    # proxy=None -> 用默认；proxy="" -> 直连
    if proxy is None:
        proxy = PROXY
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    else:
        opener = urllib.request.build_opener()
    try:
        with opener.open("https://ipwho.is/", timeout=timeout) as r:
            return json.loads(r.read().decode()).get("ip")
    except Exception as e:
        print(f"[auto] 检测失败: {e}", file=sys.stderr)
        return None


def _to_dict(x):
    if is_dataclass(x): return asdict(x)
    if isinstance(x, dict): return x
    if hasattr(x, "__dict__"): return vars(x)
    return x


def build_profile(ip, engine):
    result = Resolver([ipwho_provider], on_conflict="first").resolve(ip)
    country = result.country_code
    os_locale, browser_locale = LOCALE_MAP.get(country, DEFAULT_LOCALE)
    return {
        "api_version": "v1", "case_id": f"AUTO-{ip}",
        "resolution": {"target_ip": ip, "country": country, "region": result.region,
                       "timezone": result.timezone, "asn": result.asn,
                       "confidence": result.confidence, "source": result.source},
        "region": {"country": country, "timezone": result.timezone},
        "network": {"egress": {"mode": "dry-run"},
                    "dns": {"mode": "doh", "servers": ["https://dns.google/dns-query"], "fallback": "deny"}},
        "browser": {"engine": engine, "user_agent": "Mozilla/5.0",
                    "locale": browser_locale, "timezone_id": result.timezone,
                    "viewport": {"width": 1365, "height": 768},
                    "device_scale_factor": 1, "color_scheme": "light"},
        "webrtc": {"policy": "proxy_only", "allow_udp": False, "stun_servers": []},
        "os": {"timezone": result.timezone, "locale": os_locale},
        "inspection": {"interval_seconds": 300,
                       "auto_correct": ["dns", "egress", "webrtc", "browser_context", "os_locale"],
                       "alert_only": []},
    }


def _dns_state(d):
    return DNSState(mode=d.get("mode", "system"), servers=d.get("servers", []),
                    fallback=d.get("fallback", "allow"), observed_server=d.get("observed_server"))

def _webrtc_state(d):
    return WebRTCState(policy=d.get("policy", "default"), allow_udp=d.get("allow_udp", True),
                       stun_servers=d.get("stun_servers", []))

def _browser_profile(d):
    return BrowserProfile(user_agent=d.get("user_agent", ""), locale=d.get("locale", "en-US"),
                          timezone_id=d.get("timezone_id", "UTC"),
                          viewport=d.get("viewport", {"width": 1280, "height": 720}),
                          device_scale_factor=d.get("device_scale_factor", 1),
                          color_scheme=d.get("color_scheme", "light"),
                          engine=d.get("engine", "firefox"))


def _apply_os_locale(profile, execute):
    tz = profile["os"]["timezone"]; locale = profile["os"]["locale"]
    result = {"timezone": tz, "locale": locale, "applied": False}
    if not execute:
        result["mode"] = "dry-run"; return result
    try:
        subprocess.run(["sudo", "timedatectl", "set-timezone", tz], check=True, capture_output=True, text=True)
        result["timezone_applied"] = True
    except Exception as e:
        result["timezone_error"] = str(e)
    try:
        subprocess.run(["sudo", "bash", "-c", f"echo 'LANG={locale}' > /etc/locale.conf"],
                       check=True, capture_output=True, text=True)
        subprocess.run(["sudo", "locale-gen"], check=False, capture_output=True, text=True)
        result["locale_applied"] = True
    except Exception as e:
        result["locale_error"] = str(e)
    result["applied"] = result.get("timezone_applied", False) and result.get("locale_applied", False)
    return result


def run_adapters(profile, execute=False):
    results = {}; dry_run = not execute
    try:
        dns = DNSAdapter(); desired = _dns_state(profile["network"]["dns"])
        plan = dns.plan(observed=desired, desired=desired)
        results["dns"] = {"plan": _to_dict(plan), "apply": _to_dict(dns.apply(plan, dry_run=dry_run))}
    except Exception as e:
        results["dns"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        webrtc = WebRTCAdapter(); desired = _webrtc_state(profile["webrtc"])
        plan = webrtc.plan(observed=desired, desired=desired)
        results["webrtc"] = {"plan": _to_dict(plan), "apply": _to_dict(webrtc.apply(plan, dry_run=dry_run))}
    except Exception as e:
        results["webrtc"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        browser = BrowserAdapter(); desired = _browser_profile(profile["browser"])
        plan = browser.plan(observed={}, desired=desired)
        results["browser"] = {"plan": _to_dict(plan), "apply": _to_dict(browser.apply(plan, dry_run=dry_run))}
    except Exception as e:
        results["browser"] = {"error": f"{type(e).__name__}: {e}"}
    results["os_locale"] = _apply_os_locale(profile, execute)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ip"); p.add_argument("--auto", action="store_true")
    p.add_argument("--proxy", default=PROXY)
    p.add_argument("--engine", default=DEFAULT_ENGINE, choices=["firefox", "chromium"])
    p.add_argument("--execute", action="store_true")
    p.add_argument("--output", default="-")
    args = p.parse_args()

    if args.auto:
        print(f"[auto] 通过 {args.proxy} 检测...", file=sys.stderr)
        ip = detect_exit_ip(args.proxy)
        if not ip:
            print("[auto] 失败", file=sys.stderr); sys.exit(1)
        print(f"[auto] 出口 IP: {ip}", file=sys.stderr)
    elif args.ip:
        ip = args.ip
    else:
        print("需要 --ip 或 --auto", file=sys.stderr); sys.exit(1)

    profile = build_profile(ip, args.engine)
    adapter_results = run_adapters(profile, execute=args.execute)
    output = {"target_ip": ip, "profile": profile, "adapters": adapter_results,
              "mode": "execute" if args.execute else "dry-run"}
    text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
    if args.output == "-":
        print(text)
    else:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"written: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
