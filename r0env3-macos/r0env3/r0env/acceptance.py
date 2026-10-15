"""Measure an isolated browser; untested leak protections remain unverified."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from . import macos, network
from .browser_runtime import launch_options


def compare(profile, actual, exit_ip):
    desired = profile['browser']
    return {'language': actual['language'] == desired['locale'],
            'timezone': actual['timezone'] == desired['timezone_id'],
            'egress': actual['ip'] == exit_ip,
            'webrtc_disabled': actual['webrtc'] == 'undefined' if desired['engine'] == 'firefox' else None}


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--output', type=Path, default=macos.data_dir() / 'acceptance')
    parser.add_argument('--headless', action='store_true')
    opts = parser.parse_args(argv)
    macos.require_user()
    report = {'scope': 'isolated browser only', 'checks': {},
              'unverified': ['system DNS leaks', 'IPv6 leaks', 'proxy outage blocking', 'installed browsers', 'whole-host routing']}
    try:
        profile = json.loads((macos.data_dir() / 'profile.json').read_text())
        engine, launch, context = launch_options(profile)
        launch['headless'] = opts.headless
        # Use exactly the same explicit/saved proxy as the browser under test.
        proxy = launch.get('proxy', {}).get('server', '')
        observed_exit = network.exit_ip(proxy)
        report['host'] = macos.local_state()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(**launch)
            try:
                page = browser.new_context(**context).new_page()
                page.goto('https://ipwho.is/', wait_until='domcontentloaded', timeout=30000)
                data = json.loads(page.locator('body').inner_text())
                if data.get('success') is not True:
                    raise RuntimeError('浏览器出口查询失败')
                actual = page.evaluate('''() => ({language:navigator.language, languages:navigator.languages,
                    timezone:Intl.DateTimeFormat().resolvedOptions().timeZone, webrtc:typeof RTCPeerConnection})''')
                actual['ip'] = data['ip']
                report['actual'] = actual
                report['checks'] = compare(profile, actual, observed_exit)
                report['checks']['host_timezone'] = report['host']['timezone'] == profile['os']['timezone']
                report['checks']['host_locale'] = report['host']['locale'] == macos.normalize_locale(profile['os']['locale'])
            finally:
                browser.close()
    except Exception as exc:
        report['error'] = str(exc)
    report['overall'] = 'error' if 'error' in report else 'fail' if False in report['checks'].values() else 'partial'
    folder = opts.output.expanduser() / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    macos.private_json(folder / 'report.json', report)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    (folder / 'report.txt').write_text(text + '\n', encoding='utf-8')
    (folder / 'report.txt').chmod(0o600)
    print(text)
    print(f'报告: {folder}')
    # No complete pass: unmeasured protections always remain unverified.
    return 2 if 'error' in report else 1 if False in report['checks'].values() else 3
