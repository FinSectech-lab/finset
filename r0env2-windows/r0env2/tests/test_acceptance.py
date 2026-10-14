import json
from pathlib import Path
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace
import pytest
from r0env import acceptance as a


@pytest.mark.parametrize('observed,reference,status', [({'ip': '8.8.8.8'}, {'ip': '8.8.8.8'}, 'pass'),
    ({'ip': '1.1.1.1'}, {'ip': '8.8.8.8'}, 'fail'),
    ({'error': 'timeout'}, {'ip': '8.8.8.8'}, 'unverified'),
    ({'ip': '::1'}, {}, 'unverified')])
def test_egress_comparison(observed, reference, status):
    assert a.compare_ip(observed, reference)['status'] == status


@pytest.mark.parametrize('measurement,status', [
    ({'status': 'disabled'}, 'pass'),
    ({'status': 'complete', 'candidates': []}, 'unverified'),
    ({'status': 'timeout', 'candidates': []}, 'unverified'),
    ({'status': 'complete', 'candidates': ['candidate:1 1 udp 123 8.8.8.8 1234 typ srflx']}, 'pass'),
    ({'status': 'complete', 'candidates': ['candidate:1 1 udp 123 1.1.1.1 1234 typ srflx']}, 'fail'),
    ({'status': 'complete', 'candidates': ['candidate:1 1 udp 123 2001:4860:4860::8888 1234 typ srflx']}, 'unverified'),
])
def test_ice_requires_evidence(measurement, status):
    assert a.assess_webrtc(measurement, [{'ip': '8.8.8.8'}, {}])['status'] == status


def test_actual_host_probe_disables_application_proxy(monkeypatch):
    seen = []
    def run(command, **kwargs):
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout='{"ip":"8.8.8.8"}', stderr='')
    monkeypatch.setattr(a.subprocess, 'run', run)
    assert a.probe_ip(4)['ip'] == '8.8.8.8'
    assert seen[0][1] == '--disable'
    assert '--noproxy' in seen[0] and '-4' in seen[0]


def test_wrong_ip_family_is_not_pass(monkeypatch):
    monkeypatch.setattr(a.network, 'fetch_json', lambda *args: {'ip': '8.8.8.8'})
    assert 'error' in a.probe_ip(6, 'http://localhost:7890')


def test_overall_never_passes_missing_evidence():
    assert a.overall([]) == 'unverified'
    assert a.overall([{'status': 'pass'}, {'status': 'unverified'}]) == 'unverified'
    assert a.overall([{'status': 'fail'}, {'status': 'unverified'}]) == 'fail'


def test_collector_real_http_rejects_forged_callback():
    collector = a.Collector([{'exe': 'chrome.exe', 'path': 'unused'}])
    token = next(iter(collector.tokens))
    server = collector.server
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(origin + '/' + token, timeout=3) as response:
            page = response.read().decode()
            assert 'stun:stun.cloudflare.com:3478' in page
            assert response.headers['Referrer-Policy'] == 'no-referrer'
        body = json.dumps({'user_agent': 'Chrome/test'}).encode()
        bad = urllib.request.Request(origin + '/' + token, data=body, headers={'Origin': 'https://untrusted.example'})
        with pytest.raises(urllib.error.HTTPError) as error:
            opener.open(bad, timeout=3)
        assert error.value.code == 403 and not collector.reports
        good = urllib.request.Request(origin + '/' + token, data=body, headers={'Origin': origin})
        with opener.open(good, timeout=3) as response:
            assert response.status == 204
        assert collector.reports[token]['user_agent'] == 'Chrome/test'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_acceptance_writes_fail_and_unknown_results(monkeypatch, tmp_path):
    monkeypatch.setattr(a.sys, 'platform', 'win32')
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('R0ENV_PROXY', 'http://localhost:7890')
    monkeypatch.setattr(a.diagnostics, 'collect', lambda: {'inventory': {'system': {}}})
    monkeypatch.setattr(a, 'browser_paths', lambda _: [])
    monkeypatch.setattr(a, 'probe_ip', lambda family, proxy=None: {'ip': '8.8.8.8' if proxy else '1.1.1.1'})
    assert a.main(['--output', str(tmp_path / 'reports')]) == 1
    report = json.loads(next((tmp_path / 'reports').rglob('report.json')).read_text())
    assert report['overall'] == 'fail'
    assert report['checks']['dns_leak']['status'] == 'unverified'
    assert report['checks']['proxy_failure_blocking']['status'] == 'unverified'


def test_browser_runtime_not_replaced_by_temporary_profile(monkeypatch):
    collector = a.Collector([{'exe': 'chrome.exe', 'path': 'C:/Chrome/chrome.exe'}])
    seen = []
    def launch(command, **kwargs):
        seen.append(command)
        token = next(iter(collector.tokens))
        with collector.lock:
            collector.reports[token] = {'user_agent': 'Chrome/test'}
        collector.changed.set()
    monkeypatch.setattr(a.subprocess, 'Popen', launch)
    reports = collector.run(timeout=1)
    assert len(seen[0]) == 2
    assert seen[0][0] == 'C:/Chrome/chrome.exe'
    assert reports[0]['measurement']['user_agent'] == 'Chrome/test'
