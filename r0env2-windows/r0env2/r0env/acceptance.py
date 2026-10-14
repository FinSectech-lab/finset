"""Real Windows/browser measurements; unavailable evidence is never a pass."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from . import diagnostics, network, windows

PAGE = r'''<!doctype html><meta charset="utf-8"><title>r0env 实机验收</title>
<style>body{font:18px system-ui;max-width:900px;margin:50px auto;padding:20px}pre{white-space:pre-wrap}</style>
<h1>r0env 实机验收</h1><p>正在读取此浏览器的实际环境并发起 IP/STUN 探测。请保持页面打开。</p>
<p>不会读取历史记录、密码或 Cookie。结果仅回传本机。IP 探测访问 ipify，STUN 探测访问 Cloudflare。</p><pre id="result">检测中……</pre>
<script>
async function ip(url) {
 const c=new AbortController(), timer=setTimeout(()=>c.abort(),12000);
 try { const r=await fetch(url,{signal:c.signal,cache:'no-store',credentials:'omit'});
 if(!r.ok) throw Error('HTTP '+r.status); return {ip:(await r.json()).ip};
 } catch(e) { return {error:String(e)}; } finally {clearTimeout(timer);}
}
async function ice() {
 if(typeof RTCPeerConnection==='undefined') return {status:'disabled',candidates:[]};
 let pc; const candidates=[];
 try {
 pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.cloudflare.com:3478'}]});
 const completion=new Promise(resolve=>{
   pc.onicecandidate=e=>{if(e.candidate)candidates.push(e.candidate.candidate);else resolve('complete');};
 });
 pc.createDataChannel('audit'); await pc.setLocalDescription(await pc.createOffer());
 const status=await Promise.race([completion,new Promise(r=>setTimeout(()=>r('timeout'),12000))]);
 return {status,candidates};
 } catch(e) {return {status:'error',error:String(e),candidates};}
 finally {if(pc)pc.close();}
}
(async()=>{
 const [ipv4,ipv6,webrtc]=await Promise.all([ip('https://api.ipify.org?format=json'),ip('https://api6.ipify.org?format=json'),ice()]);
 const report={user_agent:navigator.userAgent,language:navigator.language,languages:navigator.languages,
 timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,ipv4,ipv6,webrtc};
 document.getElementById('result').textContent=JSON.stringify(report,null,2);
 try {const r=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report)});
 if(!r.ok)throw Error('HTTP '+r.status);
 document.querySelector('p').textContent='已回传本机。请等待命令窗口生成完整报告；本页面不代表全部验收通过。';
 }catch(e){document.querySelector('p').textContent='回传失败，请保留页面结果：'+e;}
})();
</script>'''


def result(status, detail, **evidence):
    return {'status': status, 'detail': detail, **evidence}


def compare_ip(observed, reference):
    try:
        actual = ipaddress.ip_address(observed['ip'])
        expected = ipaddress.ip_address(reference['ip'])
    except (KeyError, ValueError, TypeError):
        return result('unverified', '探测失败/没有对应地址族的代理出口基准；不能解释为已阻断', observed=observed, reference=reference)
    return result('pass' if actual == expected else 'fail',
                  '本次探测出口与代理基准一致' if actual == expected else '出口不同：可能绕过代理或节点采用多出口，需排查',
                  observed=str(actual), expected=str(expected))


def assess_webrtc(measurement, references):
    if measurement.get('status') == 'disabled':
        return result('pass', '此页面未暴露 RTCPeerConnection API；仅限当前浏览器环境')
    expected = set()
    for ref in references:
        try:
            expected.add(ipaddress.ip_address(ref['ip']))
        except (KeyError, ValueError, TypeError):
            pass
    addresses = []
    for candidate in measurement.get('candidates', []):
        fields = candidate.split()
        if len(fields) > 7:
            try:
                addresses.append(ipaddress.ip_address(fields[4]))
            except ValueError:
                pass  # mDNS candidates are not evidence of a public IP.
    families = {a.version for a in expected}
    unexpected = sorted({str(a) for a in addresses if a.is_global and a.version in families and a not in expected})
    if unexpected and expected:
        return result('fail', 'ICE 暴露了不在代理出口基准中的公网地址', addresses=unexpected)
    if measurement.get('status') != 'complete' or not any(a.is_global for a in addresses) or not expected or any(a.is_global and a.version not in families for a in addresses):
        return result('unverified', '未获得可充分比较的完整 ICE 结果；空候选/超时不等于无泄漏', measurement=measurement)
    return result('pass', '本次 STUN 探测的公网 ICE 地址与代理基准一致', addresses=[str(a) for a in addresses])


def probe_ip(family, proxy=None):
    url = 'https://api.ipify.org?format=json' if family == 4 else 'https://api6.ipify.org?format=json'
    try:
        if proxy is not None:
            data = network.fetch_json(url, proxy)
        else:
            # Disable curl config AND all application proxies: test the TUN route.
            command = ['curl.exe', '--disable', '--silent', '--show-error', '--fail',
                       '--connect-timeout', '6', '--max-time', '12', f'-{family}',
                       '--noproxy', '*', url]
            completed = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace', timeout=15)
            if completed.returncode:
                raise RuntimeError(completed.stderr.strip() or f'curl exit {completed.returncode}')
            data = json.loads(completed.stdout)
        address = ipaddress.ip_address(data['ip'])
        if address.version != family or not address.is_global:
            raise ValueError('unexpected IP family or nonpublic IP')
        return {'ip': str(address)}
    except Exception as exc:
        # Do not include proxy URLs/credentials in reports.
        return {'error': type(exc).__name__, 'detail': 'IP probe failed; see connectivity and proxy settings'}


def browser_paths(inventory):
    found = {}
    for browser in inventory.get('registered_browsers', []):
        if browser.get('exe') in ('msedge.exe', 'chrome.exe', 'firefox.exe'):
            path = Path(browser['path'])
            if path.is_file():
                found.setdefault(str(path.resolve()).casefold(), {'exe': browser['exe'], 'path': str(path)})
    suffixes = [('msedge.exe', 'Microsoft/Edge/Application/msedge.exe'),
                ('chrome.exe', 'Google/Chrome/Application/chrome.exe'),
                ('firefox.exe', 'Mozilla Firefox/firefox.exe')]
    for root in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        for exe, suffix in suffixes:
            if not os.environ.get(root):
                continue
            path = Path(os.environ[root]) / suffix
            if path.is_file():
                found.setdefault(str(path.resolve()).casefold(), {'exe': exe, 'path': str(path)})
    return list(found.values())


class Collector:
    def __init__(self, browsers):
        self.tokens = {secrets.token_urlsafe(24): browser for browser in browsers}
        self.reports = {}
        self.lock = threading.Lock()
        self.changed = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def valid_token(self):
                token = urlsplit(self.path).path.lstrip('/')
                expected_host = f'127.0.0.1:{self.server.server_port}'
                if self.headers.get('Host') != expected_host or token not in owner.tokens:
                    return None
                return token

            def do_GET(self):
                if self.valid_token() is None:
                    self.send_error(404)
                    return
                body = PAGE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                token = self.valid_token()
                origin = f'http://127.0.0.1:{self.server.server_port}'
                if token is None or self.headers.get('Origin') != origin:
                    self.send_error(403)
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 65536:
                        raise ValueError('invalid length')
                    self.connection.settimeout(5)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict) or not isinstance(payload.get('user_agent'), str):
                        raise ValueError('invalid report')
                    with owner.lock:
                        owner.reports.setdefault(token, payload)
                    owner.changed.set()
                except (ValueError, OSError):
                    self.send_error(400)
                    return
                self.send_response(204)
                self.end_headers()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True

    def run(self, timeout=90):
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        launch_errors = {}
        try:
            for token, browser in self.tokens.items():
                url = f'http://127.0.0.1:{self.server.server_port}/{token}'
                print(f"打开实际浏览器：{browser['exe']}。请保留验收页面；如出现配置选择，选择日常配置。", flush=True)
                try:
                    # No temporary profiles or Playwright environment overrides.
                    subprocess.Popen([browser['path'], url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except OSError as exc:
                    launch_errors[token] = {'error': str(exc)}
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with self.lock:
                    if len(self.reports) + len(launch_errors) >= len(self.tokens):
                        break
                self.changed.wait(min(1, max(0, deadline-time.monotonic())))
                self.changed.clear()
            return [{'browser': browser, 'measurement': self.reports.get(token, launch_errors.get(token, {'error': 'browser timeout/no callback'}))}
                    for token, browser in self.tokens.items()]
        finally:
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=5)


def assess_browser(entry, references, expected):
    data = entry['measurement']
    if 'error' in data:
        return {'browser': entry['browser'], 'checks': {'runtime': result('unverified', str(data['error']))}, 'measurement': data}
    expected_marker = {'chrome.exe': 'Chrome/', 'msedge.exe': 'Edg/', 'firefox.exe': 'Firefox/'}[entry['browser']['exe']]
    identity = result('pass' if expected_marker in data.get('user_agent', '') else 'unverified', '校对回传浏览器 UA；UA 可被修改，因此不能证明所有 profile 已覆盖')
    checks = {'identity': identity, 'ipv4': compare_ip(data.get('ipv4', {}), references[0]),
              'ipv6': compare_ip(data.get('ipv6', {}), references[1]),
              'webrtc': assess_webrtc(data.get('webrtc', {}), references)}
    for name, key in [('locale', 'language'), ('timezone_id', 'timezone')]:
        target = expected.get(name)
        actual = data.get(key)
        checks[key] = result('unverified' if not target or not actual else 'pass' if actual == target else 'fail',
                             '浏览器实际值与目标配置比较', observed=actual, expected=target)
    checks['local_address_exposure'] = result('unverified', '原始 ICE 候选保存在 measurement；未对局域网身份信息作完整评估')
    return {'browser': entry['browser'], 'checks': checks, 'measurement': data}


def overall(checks):
    statuses = [item['status'] for item in checks]
    if 'fail' in statuses:
        return 'fail'
    return 'pass' if statuses and all(s == 'pass' for s in statuses) else 'unverified'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Windows 实机验收：真实系统/浏览器探测，不修改配置', allow_abbrev=False)
    parser.add_argument('--output', type=Path, default=windows.data_dir() / 'acceptance')
    parser.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args(argv)
    if sys.platform != 'win32':
        raise RuntimeError('必须在 Windows 上运行实机验收')
    if not 15 <= args.timeout <= 300:
        parser.error('--timeout 必须在 15 到 300 秒之间')
    folder = args.output / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': '当前 Windows、发现的 Edge/Chrome/Firefox 各一个实际浏览器会话；不是所有应用或所有 profile',
              'overall': 'unverified', 'checks': {}, 'browsers': []}
    try:
        print('采集 Windows 实际设置……', flush=True)
        inventory = diagnostics.collect()['inventory']
        report['inventory'] = inventory
        print('探测代理出口与绕过应用代理的系统出口（IPv4/IPv6）……', flush=True)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            tasks = [pool.submit(probe_ip, family, proxy) for proxy in (network.proxy_url(), None) for family in (4, 6)]
            p4, p6, host4, host6 = [task.result() for task in tasks]
        report['measurements'] = {'proxy_ipv4': p4, 'proxy_ipv6': p6, 'host_ipv4': host4, 'host_ipv6': host6}
        checks = report['checks']
        if not network.proxy_url():
            checks['proxy_reference'] = result('unverified', '没有显式代理基准，不能证明 TUN 接管')
        checks['host_ipv4'] = compare_ip(host4, p4)
        checks['host_ipv6'] = compare_ip(host6, p6)
        path = windows.data_dir() / 'profile.json'
        profile = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if profile.get('os'):
            actual = inventory['system']
            expected = profile['os']
            for key, value in [('timezone', windows.windows_timezone(expected['timezone'])),
                               ('culture', windows.culture_name(expected['locale'])),
                               ('system_locale', windows.culture_name(expected['locale']))]:
                checks[key] = result('pass' if actual.get(key) == value else 'fail', '系统实际设置与保存目标比较', observed=actual.get(key), expected=value)
        else:
            checks['system_target'] = result('unverified', '没有已保存的目标 profile，不能判定语言/时区是否符合目标')
        browsers = browser_paths(inventory)
        entries = Collector(browsers).run(args.timeout) if browsers else []
        report['browsers'] = [assess_browser(entry, (p4, p6), profile.get('browser', {})) for entry in entries]
        if not browsers:
            checks['browser_coverage'] = result('unverified', '没有发现支持的浏览器；便携版/自定义路径须单独核实')
        checks['dns_leak'] = result('unverified', '未采集权威 DNS 观测或物理网卡抓包；DNS 地址/TUN 开关不能证明无泄漏')
        checks['proxy_failure_blocking'] = result('unverified', '未停止代理进行受控断连测试，不能认定断连时会阻断直连')
        checks['whole_host_coverage'] = result('unverified', '有限目的地址的探测不能证明所有应用、协议、浏览器配置均被覆盖')
        all_checks = list(checks.values()) + [c for b in report['browsers'] for c in b['checks'].values()]
        report['overall'] = overall(all_checks)
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['checks']['execution'] = result('unverified', '执行未完成；已有失败证据仍保留')
        report['overall'] = overall(list(report['checks'].values()) + [c for b in report['browsers'] for c in b['checks'].values()])
    finally:
        json_path = folder / 'report.json'
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['r0env Windows 实机验收', f"总体结论：{report['overall']}", report['scope'], '',
                 'pass 仅表示本项探测通过；unverified 不等于安全。']
        if report.get('error'):
            lines.append('执行错误：' + report['error'])
        for name, item in report['checks'].items():
            lines.append(f"[{item['status']}] {name}: {item['detail']}")
        for browser in report['browsers']:
            lines.append('\n浏览器：' + browser['browser']['path'])
            for name, item in browser['checks'].items():
                lines.append(f"[{item['status']}] {name}: {item['detail']}")
        (folder / 'report.txt').write_text('\n'.join(lines), encoding='utf-8-sig')
        print('\n'.join(lines), flush=True)
        print(f'报告：{json_path}', flush=True)
    return 1 if report['overall'] == 'fail' else 0 if report['overall'] == 'pass' else 2
