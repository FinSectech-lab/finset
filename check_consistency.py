#!/usr/bin/env python3
"""r0env check: 检测出口国家 vs 系统时区/locale 是否一致。不一致则告警。"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from r0env.resolver import Resolver, ipwho_provider

PROXY = os.environ.get("R0ENV_PROXY", "http://127.0.0.1:7890")
LOG = Path("/home/ljk/Projects/r0env/check_consistency.log")

LOCALE_MAP = {
    "US": "en_US.UTF-8", "GB": "en_GB.UTF-8", "JP": "ja_JP.UTF-8",
    "CN": "zh_CN.UTF-8", "DE": "de_DE.UTF-8", "FR": "fr_FR.UTF-8",
    "KR": "ko_KR.UTF-8", "SG": "en_SG.UTF-8", "HK": "zh_HK.UTF-8",
    "TW": "zh_TW.UTF-8", "AU": "en_AU.UTF-8", "CA": "en_CA.UTF-8",
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_exit_ip():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    with opener.open("https://ipwho.is/", timeout=8) as r:
        return json.loads(r.read().decode())["ip"]


def get_system_timezone():
    out = subprocess.run(["timedatectl", "show", "-p", "Timezone", "--value"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def get_system_locale():
    out = subprocess.run(["bash", "-c", "grep '^LANG=' /etc/locale.conf | cut -d= -f2"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def main():
    try:
        ip = get_exit_ip()
    except Exception as e:
        log(f"ERROR 获取出口 IP 失败: {e}")
        sys.exit(2)

    resolver = Resolver([ipwho_provider], on_conflict="first")
    result = resolver.resolve(ip)
    country = result.country_code
    expected_tz = result.timezone
    expected_locale = LOCALE_MAP.get(country, "en_US.UTF-8")

    actual_tz = get_system_timezone()
    actual_locale = get_system_locale()

    log(f"出口 IP: {ip} ({country}) | 期望时区: {expected_tz} | 实际时区: {actual_tz}")
    log(f"期望 locale: {expected_locale} | 实际 locale: {actual_locale}")

    ok = True
    if actual_tz != expected_tz:
        log(f"WARN 时区不一致！期望 {expected_tz}，实际 {actual_tz}")
        ok = False
    if actual_locale != expected_locale:
        log(f"WARN locale 不一致！期望 {expected_locale}，实际 {actual_locale}")
        ok = False

    if ok:
        log("OK 一致性检查通过")
        sys.exit(0)
    else:
        log("FAIL 一致性检查失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
