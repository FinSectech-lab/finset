import json
import os
import plistlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from r0env import macos, macos_cli, auto
from r0env.browser_runtime import launch_options
from r0env.checker import compare
from r0env.resolver import GeoResult
from r0env.acceptance import compare as browser_compare


@pytest.fixture
def profile():
    return {'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja-JP'},
            'browser': {'engine': 'firefox', 'locale': 'ja-JP', 'timezone_id': 'Asia/Tokyo'},
            'network': {'egress': {'proxy_url': 'http://127.0.0.1:18080'},
                        'dns': {'mode': 'doh', 'servers': ['https://dns.google/dns-query'], 'fallback': 'deny'}}}


@pytest.fixture
def host(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(macos, 'require_user', lambda: None)
    monkeypatch.setattr(macos, 'authorize', lambda: None)
    monkeypatch.setattr(macos, 'write_timezone', lambda value: None)
    monkeypatch.setattr(macos, 'run', lambda args: '')
    return {'timezone': 'Asia/Shanghai', 'locale': 'zh_CN', 'locale_present': True, 'languages': ['zh-Hans']}


def test_preview_no_host_calls(monkeypatch, profile):
    monkeypatch.setattr(macos, 'local_state', lambda: pytest.fail('preview read host'))
    monkeypatch.setattr(macos, 'authorize', lambda: pytest.fail('preview elevated'))
    assert macos.apply_os(profile)['mode'] == 'dry-run'


@pytest.mark.parametrize('value', ['../etc/passwd', '/etc/localtime', '-bad', None, 'Fake/Nowhere'])
def test_invalid_timezone_rejected(value):
    with pytest.raises((ValueError, KeyError, TypeError)):
        macos.validate_timezone(value)


@pytest.mark.parametrize('value', ['$(touch x)', 'ja-JP; id', '', 'ja', None])
def test_invalid_locale(value):
    with pytest.raises(ValueError): macos.normalize_locale(value)


def test_apply_snapshot_and_readback(monkeypatch, profile, host):
    states = iter([host, {**host, 'timezone': 'Asia/Tokyo', 'locale': 'ja_JP'}])
    monkeypatch.setattr(macos, 'local_state', lambda: next(states))
    report = macos.apply_os(profile, True)
    assert report['applied']
    path = Path(report['snapshot'])
    assert json.loads(path.read_text())['state'] == host
    assert path.stat().st_mode & 0o777 == 0o600


def test_command_success_but_readback_mismatch(monkeypatch, profile, host):
    monkeypatch.setattr(macos, 'local_state', lambda: host)
    assert not macos.apply_os(profile, True)['applied']


def test_partial_failure_keeps_snapshot(monkeypatch, profile, host):
    monkeypatch.setattr(macos, 'local_state', lambda: host)
    def fail(args): raise RuntimeError('defaults denied')
    monkeypatch.setattr(macos, 'run', fail)
    result = macos.apply_os(profile, True)
    assert not result['applied'] and result['partial_changes_possible']
    assert Path(result['snapshot']).exists()


def test_auth_failure_before_mutations(monkeypatch, profile, host, tmp_path):
    monkeypatch.setattr(macos, 'local_state', lambda: host)
    def fail(): raise RuntimeError('sudo denied')
    monkeypatch.setattr(macos, 'authorize', fail)
    monkeypatch.setattr(macos, 'write_timezone', lambda value: pytest.fail('mutation'))
    with pytest.raises(RuntimeError): macos.apply_os(profile, True)
    assert not list(tmp_path.iterdir())


def test_reject_whole_process_root(monkeypatch):
    monkeypatch.setattr(macos, 'require_macos', lambda: None)
    monkeypatch.setattr(os, 'geteuid', lambda: 0)
    with pytest.raises(RuntimeError, match='sudo'): macos.require_user()


def test_restore_absent_locale_deletes_only_key(monkeypatch, host, tmp_path):
    state = {**host, 'locale': None, 'locale_present': False}
    p = tmp_path / 'snapshot.json'
    macos.private_json(p, {'schema': 1, 'platform': 'darwin', 'uid': os.getuid(), 'state': state})
    calls = []
    monkeypatch.setattr(macos, 'run', lambda args: calls.append(args))
    monkeypatch.setattr(macos, 'preferences', lambda: {'AppleLocale': 'ja_JP', 'AppleLanguages': ['en']})
    monkeypatch.setattr(macos, 'local_state', lambda: state)
    assert macos.restore(p)['rolled_back']
    assert calls == [['/usr/bin/defaults', 'delete', '-g', 'AppleLocale']]


def test_restore_reject_other_user(monkeypatch, host, tmp_path):
    p = tmp_path / 'snapshot.json'
    macos.private_json(p, {'schema': 1, 'platform': 'darwin', 'uid': -1, 'state': host})
    monkeypatch.setattr(macos, 'authorize', lambda: pytest.fail('must not authorize'))
    with pytest.raises(ValueError): macos.restore(p)


def test_launchagent_paths_are_array(monkeypatch, host, tmp_path):
    monkeypatch.setattr(macos.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1))
    monkeypatch.setattr(macos, 'agent_path', lambda: tmp_path / 'agent.plist')
    monkeypatch.setenv('R0ENV_PROXY', 'http://127.0.0.1:1080')
    assert macos.install_timer()['installed']
    agent = plistlib.loads((tmp_path / 'agent.plist').read_bytes())
    assert agent['StartInterval'] == 300
    assert agent['ProgramArguments'][-2] == '_scheduled_check'
    assert json.loads((tmp_path / 'timer.json').read_text())['proxy'].endswith(':1080')


def test_launchagent_failure_no_false_install(monkeypatch, host, tmp_path):
    monkeypatch.setattr(macos.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1))
    monkeypatch.setattr(macos, 'agent_path', lambda: tmp_path / 'agent.plist')
    def fail(args): raise RuntimeError('no GUI session')
    monkeypatch.setattr(macos, 'run', fail)
    with pytest.raises(RuntimeError): macos.install_timer()
    assert not (tmp_path / 'agent.plist').exists()


def test_firefox_saved_proxy_and_webrtc(monkeypatch, profile):
    monkeypatch.delenv('R0ENV_PROXY', raising=False)
    engine, opts, context = launch_options(profile)
    assert opts['proxy']['server'].endswith(':18080')
    assert opts['firefox_user_prefs']['media.peerconnection.enabled'] is False
    assert 'network.proxy.type' not in opts['firefox_user_prefs']
    assert context['timezone_id'] == 'Asia/Tokyo'


def test_direct_browser_overrides_saved_proxy(monkeypatch, profile):
    monkeypatch.setenv('R0ENV_PROXY', '')
    _, opts, _ = launch_options(profile)
    assert 'proxy' not in opts
    assert opts['firefox_user_prefs']['network.proxy.type'] == 0


def test_checker_mismatch_is_failure():
    result = GeoResult('8.8.8.8', country_code='JP', timezone='Asia/Tokyo')
    assert not compare(result, {'timezone': 'Asia/Tokyo', 'locale': 'zh_CN'})['ok']
    assert compare(result, {'timezone': 'Asia/Tokyo', 'locale': 'ja_JP'})['ok']


def test_acceptance_egress_mismatch(profile):
    actual = {'language': 'ja-JP', 'timezone': 'Asia/Tokyo', 'webrtc': 'undefined', 'ip': '8.8.8.8'}
    assert not browser_compare(profile, actual, '1.1.1.1')['egress']


def test_chromium_no_false_webrtc_pass(profile):
    profile['browser']['engine'] = 'chromium'
    actual = {'language': 'ja-JP', 'timezone': 'Asia/Tokyo', 'webrtc': 'function', 'ip': '8.8.8.8'}
    assert browser_compare(profile, actual, '8.8.8.8')['webrtc_disabled'] is None


def test_cli_preview_reject_execute():
    assert macos_cli.main(['preview', '--execute']) == 2


def test_cli_abbreviated_execute_rejected():
    with pytest.raises(SystemExit) as exc: macos_cli.main(['preview', '--exec'])
    assert exc.value.code == 2


def test_cli_no_unknown_args():
    assert macos_cli.main(['browser', '--proxy', 'x']) == 2


def test_cli_proxy_explicit_ip(monkeypatch):
    calls = []
    monkeypatch.setattr(auto, 'main', lambda args: calls.append(args) or 0)
    assert macos_cli.main(['preview', '--ip', '8.8.8.8', '--proxy', 'http://localhost:1']) == 0
    assert '--auto' not in calls[0]


def test_apply_saves_profile_privately(monkeypatch, profile, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(auto, '_apply_os_locale', lambda *a: {'applied': True})
    profile['webrtc'] = {'policy': 'proxy_only', 'allow_udp': False}
    auto.run_adapters(profile, True)
    assert (tmp_path / 'profile.json').stat().st_mode & 0o777 == 0o600


def test_acceptance_failure_still_writes_report(monkeypatch, tmp_path):
    from r0env import acceptance
    monkeypatch.setattr(macos, 'require_user', lambda: None)
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / 'missing'))
    destination = tmp_path / 'reports'
    assert acceptance.main(['--output', str(destination), '--headless']) == 2
    report = json.loads(next(destination.glob('*/report.json')).read_text())
    assert report['overall'] == 'error'
    assert 'system DNS leaks' in report['unverified']


def test_timezone_command_uses_argument_array(monkeypatch):
    calls = []
    monkeypatch.setattr(macos, 'run', lambda args: calls.append(args))
    macos.write_timezone('Asia/Tokyo')
    assert calls == [['/usr/bin/sudo', '-n', '/usr/sbin/systemsetup', '-settimezone', 'Asia/Tokyo']]


@pytest.mark.parametrize('args', [['--direct', '--proxy', 'http://localhost:1'], ['--proxy=http://localhost:1', '--direct']])
def test_direct_proxy_conflict_no_network(monkeypatch, args):
    monkeypatch.setattr(auto, 'main', lambda args: pytest.fail('must reject before network'))
    assert macos_cli.main(['preview', *args]) == 2


def test_failed_apply_preserves_old_profile(monkeypatch, profile, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    path = tmp_path / 'profile.json'
    path.write_text('{"previous": true}')
    monkeypatch.setattr(auto, '_apply_os_locale', lambda *a: {'applied': False})
    profile['webrtc'] = {'policy': 'proxy_only', 'allow_udp': False}
    result = auto.run_adapters(profile, True)
    assert result['profile_saved'] is False
    assert path.read_text() == '{"previous": true}'


def test_restore_partial_failure_reports_state(monkeypatch, host, tmp_path):
    path = tmp_path / 'snapshot.json'
    macos.private_json(path, {'schema': 1, 'platform': 'darwin', 'uid': os.getuid(), 'state': host})
    def fail(args): raise RuntimeError('defaults failed')
    monkeypatch.setattr(macos, 'run', fail)
    result = macos.restore(path)
    assert not result['rolled_back']
    assert result['timezone_command_completed']
    assert result['partial_changes_possible']


def test_atomic_profile_serialization_failure_keeps_previous(tmp_path):
    path = tmp_path / 'profile.json'
    macos.private_json(path, {'previous': True})
    with pytest.raises(TypeError): macos.private_json(path, {'invalid': object()})
    assert json.loads(path.read_text()) == {'previous': True}


def test_atomic_profile_replace_failure_keeps_previous(monkeypatch, tmp_path):
    path = tmp_path / 'profile.json'
    macos.private_json(path, {'previous': True})
    def fail(*args): raise OSError('disk failure')
    monkeypatch.setattr(macos.os, 'replace', fail)
    with pytest.raises(OSError): macos.private_json(path, {'new': True})
    assert json.loads(path.read_text()) == {'previous': True}
    assert list(tmp_path.iterdir()) == [path]


def test_failed_timer_update_restores_loaded_task(monkeypatch, host, tmp_path):
    path = tmp_path / 'agent.plist'
    old_agent = plistlib.dumps({'Label': macos.LABEL, 'StartInterval': 300})
    path.write_bytes(old_agent)
    settings = tmp_path / 'timer.json'
    settings.write_text('{"proxy":"http://localhost:1234"}')
    monkeypatch.setattr(macos, 'agent_path', lambda: path)
    monkeypatch.setattr(macos.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0))
    calls = []
    def run(args):
        calls.append(args)
        if args[1] == 'bootstrap' and len(calls) == 2:
            raise RuntimeError('new registration failed')
    monkeypatch.setattr(macos, 'run', run)
    with pytest.raises(RuntimeError, match='旧配置已恢复'): macos.install_timer()
    assert path.read_bytes() == old_agent
    assert json.loads(settings.read_text())['proxy'] == 'http://localhost:1234'
    assert [c[1] for c in calls] == ['bootout', 'bootstrap', 'bootstrap']
