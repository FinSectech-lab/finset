import base64
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from r0env import auto, checker, network, windows, windows_cli
from r0env.browser_runtime import launch_options
from r0env.resolver import GeoResult


@pytest.mark.parametrize('iana,expected', [('Asia/Tokyo', 'Tokyo Standard Time'),
    ('America/Los_Angeles', 'Pacific Standard Time'), ('Asia/Shanghai', 'China Standard Time'),
    ('Asia/Hong_Kong', 'China Standard Time'), ('Europe/Berlin', 'W. Europe Standard Time'),
    ('Etc/UTC', 'UTC'), ('Asia/Kolkata', 'India Standard Time')])
def test_timezone_mapping(iana, expected):
    assert windows.windows_timezone(iana) == expected


@pytest.mark.parametrize('value', [None, '', 'Invalid/Zone'])
def test_unknown_timezone_is_not_guessed(value):
    with pytest.raises(ValueError):
        windows.windows_timezone(value)


def test_preview_has_no_host_side_effects(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / 'unused'))
    monkeypatch.setattr(windows, 'powershell', lambda _: pytest.fail('preview executed PowerShell'))
    profile = {'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja_JP.UTF-8'}}
    result = windows.apply_os(profile)
    assert result['locale'] == 'ja-JP' and not result['applied']
    assert not (tmp_path / 'unused').exists()


def test_apply_snapshot_and_partial_failure(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    before = {'timezone': 'UTC', 'locale': 'en-US', 'system_locale': 'en-US'}
    monkeypatch.setattr(windows, 'local_state', lambda: before)
    calls = []
    def run(command):
        calls.append(command)
        if command.startswith('Set-Culture'):
            raise RuntimeError('access denied')
        return ''
    monkeypatch.setattr(windows, 'powershell', run)
    result = windows.apply_os({'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja-JP'}}, True)
    assert not result['applied'] and result['timezone_applied']
    assert 'access denied' in result['culture_error']
    assert json.loads(Path(result['snapshot']).read_text()) == before
    assert not any(c.startswith('Set-WinSystemLocale') for c in calls)


def test_apply_success_and_restart(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(windows, 'powershell', lambda _: '')
    monkeypatch.setattr(windows, 'local_state', lambda: {'timezone': 'UTC', 'locale': 'en-US', 'system_locale': 'en-US'})
    result = windows.apply_os({'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja-JP'}}, True)
    assert result['applied'] and result['restart_required']


def test_permission_preflight_prevents_changes(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / 'absent'))
    def denied(_):
        raise RuntimeError('administrator required')
    monkeypatch.setattr(windows, 'powershell', denied)
    with pytest.raises(RuntimeError):
        windows.apply_os({'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja-JP'}}, True)
    assert not (tmp_path / 'absent').exists()


def test_powershell_encoding_and_errors(monkeypatch):
    monkeypatch.setattr(windows.sys, 'platform', 'win32')
    seen = []
    def run(args, **kwargs):
        seen.append(args)
        assert kwargs['encoding'] == 'utf-8'
        return SimpleNamespace(returncode=0, stdout='东京\n', stderr='')
    monkeypatch.setattr(windows.subprocess, 'run', run)
    assert windows.powershell("Write-Output '东京'") == '东京'
    decoded = base64.b64decode(seen[0][-1]).decode('utf-16-le')
    assert "Write-Output '东京'" in decoded
    assert '-NoProfile' in seen[0] and '-NonInteractive' in seen[0]
    monkeypatch.setattr(windows.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stdout='', stderr='denied'))
    with pytest.raises(RuntimeError, match='denied'):
        windows.powershell('x')


def test_check_normalizes_timezone_aliases():
    report = checker.compare(GeoResult('8.8.8.8', 'HK', timezone='Asia/Hong_Kong'),
        {'timezone': 'China Standard Time', 'locale': 'zh-HK', 'system_locale': 'zh-HK'})
    assert report['ok']
    report = checker.compare(GeoResult('8.8.8.8', 'JP', timezone='Asia/Tokyo'),
        {'timezone': 'UTC', 'locale': 'ja-JP', 'system_locale': 'en-US'})
    assert not report['ok'] and not report['checks']['system_locale']


@pytest.mark.parametrize('actual,code', [('Tokyo Standard Time', 0), ('UTC', 1)])
def test_check_exit_codes(monkeypatch, tmp_path, actual, code):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(checker, 'exit_ip', lambda: '8.8.8.8')
    monkeypatch.setattr(checker, 'ipwho_provider', lambda ip: GeoResult(ip, 'JP', timezone='Asia/Tokyo'))
    monkeypatch.setattr(windows, 'local_state', lambda: {'timezone': actual, 'locale': 'ja-JP', 'system_locale': 'ja-JP'})
    assert checker.main() == code
    assert (tmp_path / 'check_consistency.log').exists()


def test_check_network_error_is_logged(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(checker, 'exit_ip', lambda: (_ for _ in ()).throw(OSError('offline')))
    assert checker.main() == 2
    assert 'offline' in (tmp_path / 'check_consistency.log').read_text()


def test_proxy_direct_does_not_inherit_environment(monkeypatch):
    monkeypatch.setenv('HTTPS_PROXY', 'http://unexpected:1234')
    seen = []
    monkeypatch.setattr(network.urllib.request, 'build_opener', lambda handler: seen.append(handler.proxies))
    network.opener('')
    network.opener('http://expected:7890')
    assert seen == [{}, {'http': 'http://expected:7890', 'https': 'http://expected:7890'}]


def test_scheduled_task_quoting_and_identity(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / "路径 O'Brien"))
    monkeypatch.setenv('R0ENV_PROXY', '')
    monkeypatch.setenv('USERNAME', 'tester')
    monkeypatch.setattr(windows.sys, 'executable', "C:\\some path\\O'Brien\\python.exe")
    calls = []
    monkeypatch.setattr(windows, 'powershell', lambda script: calls.append(script))
    assert windows.install_timer()['interval_seconds'] == 300
    command = calls[0]
    assert "O''Brien" in command
    assert '-LogonType Interactive' in command and '-RunLevel Limited' in command
    assert 'New-TimeSpan -Minutes 5' in command and '-Force' in command
    assert json.loads((windows.data_dir() / 'timer.json').read_text())['proxy'] == ''


def test_dispatch_and_explicit_ip(monkeypatch):
    calls = []
    monkeypatch.setattr(auto, 'main', lambda args: calls.append(args) or 0)
    assert windows_cli.main([]) == 0
    assert calls[-1] == ['--auto']
    assert windows_cli.main(['apply', '--ip', '8.8.8.8']) == 0
    assert '--auto' not in calls[-1] and '--execute' in calls[-1]
    assert windows_cli.main(['cr']) == 0
    assert calls[-1][-2:] == ['--engine', 'chromium']
    assert windows_cli.main(['2001:4860:4860::8888']) == 0
    assert calls[-1][:2] == ['--ip', '2001:4860:4860::8888']
    assert windows_cli.main(['preview', '--execute']) == 2
    assert windows_cli.main(['nonsense']) == 2


def test_browser_options_preserve_proxy(monkeypatch):
    monkeypatch.setenv('R0ENV_PROXY', 'http://127.0.0.1:7890')
    profile = {'browser': {'engine': 'firefox', 'locale': 'ja-JP', 'timezone_id': 'Asia/Tokyo'},
               'network': {'dns': {'mode': 'doh', 'fallback': 'deny', 'servers': ['https://dns.google/dns-query']}}}
    engine, options, context = launch_options(profile)
    assert engine == 'firefox' and context['timezone_id'] == 'Asia/Tokyo'
    assert options['proxy']['server'] == 'http://127.0.0.1:7890'
    assert 'network.proxy.type' not in options['firefox_user_prefs']
    assert options['firefox_user_prefs']['network.trr.mode'] == 3
    profile['browser']['engine'] = 'chromium'
    _, options, _ = launch_options(profile)
    assert '--force-webrtc-ip-handling-policy=disable_non_proxied_udp' in options['args']


def test_full_preview_offline(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(auto, 'ipwho_provider', lambda ip: GeoResult(ip, 'JP', timezone='Asia/Tokyo'))
    monkeypatch.setattr(windows, 'powershell', lambda _: pytest.fail('preview must not execute'))
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path / 'absent'))
    assert windows_cli.main(['preview', '--ip', '8.8.8.8', '--proxy=']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['profile']['os']['locale'] == 'ja-JP'
    assert result['adapters']['os_locale']['timezone'] == 'Tokyo Standard Time'
    assert not (tmp_path / 'absent').exists()


def test_restore_escapes_data(monkeypatch, tmp_path):
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps({'timezone': 'UTC', 'locale': 'en-US', 'system_locale': 'ja-JP'}))
    calls = []
    monkeypatch.setattr(windows, 'powershell', lambda command: calls.append(command))
    assert windows.restore(path)['rolled_back']
    assert "Set-WinSystemLocale -SystemLocale 'ja-JP'" in calls[0]


def test_apply_saves_profile_without_claiming_browser_applied(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(auto, 'ipwho_provider', lambda ip: GeoResult(ip, 'JP', timezone='Asia/Tokyo'))
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(windows, 'powershell', lambda _: '')
    monkeypatch.setattr(windows, 'local_state', lambda: {'timezone': 'UTC', 'locale': 'en-US', 'system_locale': 'en-US'})
    assert windows_cli.main(['apply', '--ip', '8.8.8.8', '--direct']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['adapters']['os_locale']['applied']
    for key in ('dns', 'webrtc', 'browser'):
        assert not report['adapters'][key]['apply']['applied']
    assert json.loads((tmp_path / 'profile.json').read_text())['resolution']['country'] == 'JP'
    assert network.proxy_url() == ''


def test_scheduled_check_restores_proxy_and_directory(monkeypatch, tmp_path):
    settings = tmp_path / 'timer.json'
    settings.write_text(json.dumps({'proxy': ''}))
    monkeypatch.setenv('R0ENV_PROXY', 'http://unexpected:7890')
    def check():
        assert network.proxy_url() == ''
        assert windows.data_dir() == tmp_path
        return 1
    monkeypatch.setattr(checker, 'main', check)
    assert windows_cli.main(['_scheduled_check', str(settings)]) == 1


@pytest.mark.parametrize('option', ['--exec', '--exe', '--execut'])
def test_preview_rejects_execution_abbreviations(monkeypatch, option):
    monkeypatch.setattr(auto, 'run_adapters', lambda *a, **kw: pytest.fail('preview attempted execution'))
    with pytest.raises(SystemExit) as error:
        windows_cli.main(['preview', '--ip', '8.8.8.8', option])
    assert error.value.code == 2


def test_explicit_ip_and_auto_are_rejected(monkeypatch):
    monkeypatch.setattr(auto, 'detect_exit_ip', lambda *a: pytest.fail('ambiguous target'))
    with pytest.raises(SystemExit) as error:
        windows_cli.main(['apply', '--auto', '--ip', '8.8.8.8'])
    assert error.value.code == 2


@pytest.mark.parametrize('proxy', ['', 'http://custom:8888'])
@pytest.mark.parametrize('engine', ['firefox', 'chromium'])
def test_profile_proxy_survives_new_process(monkeypatch, proxy, engine):
    monkeypatch.setenv('R0ENV_PROXY', proxy)
    monkeypatch.setattr(auto, 'ipwho_provider', lambda ip: GeoResult(ip, 'JP', timezone='Asia/Tokyo'))
    profile = auto.build_profile('8.8.8.8', engine)
    monkeypatch.delenv('R0ENV_PROXY')
    _, options, _ = launch_options(profile)
    if proxy:
        assert options['proxy']['server'] == proxy
    else:
        assert 'proxy' not in options
        if engine == 'firefox':
            assert options['firefox_user_prefs']['network.proxy.type'] == 0
        else:
            assert '--no-proxy-server' in options['args']


def test_status_shows_host_even_when_proxy_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    (tmp_path / 'profile.json').write_text(json.dumps({'browser': {'engine': 'chromium'}}))
    monkeypatch.setattr(windows_cli, 'exit_ip', lambda: (_ for _ in ()).throw(OSError('offline')))
    monkeypatch.setattr(windows, 'local_state', lambda: {'timezone': 'UTC'})
    assert windows_cli.main(['status']) == 2
    report = json.loads(capsys.readouterr().out)
    assert report['system']['timezone'] == 'UTC'
    assert report['egress']['error'] == 'offline'
    assert report['engine'] == 'chromium'


def test_invalid_install_argument_cannot_install_task(monkeypatch):
    monkeypatch.setattr(windows, 'install_timer', lambda: pytest.fail('unexpected installation'))
    assert windows_cli.main(['install', '--typo']) == 2


def test_legacy_profile_equals_form(monkeypatch):
    seen = []
    monkeypatch.setattr(windows_cli, 'legacy', lambda args: seen.append(args) or 0)
    assert windows_cli.main(['apply', '--profile=test.json', '--target=host', '--confirm=T']) == 0
    assert seen


def test_relative_data_dir_becomes_absolute(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('R0ENV_CONFIG_DIR', 'settings')
    assert windows.data_dir() == tmp_path / 'settings'


def test_apply_timeout_keeps_snapshot_in_report(monkeypatch, tmp_path):
    monkeypatch.setenv('R0ENV_CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(windows, 'local_state', lambda: {'timezone': 'UTC', 'locale': 'en-US', 'system_locale': 'en-US'})
    def run(command):
        if command.startswith('Set-Culture'):
            raise subprocess.TimeoutExpired('powershell.exe', 90)
        return ''
    monkeypatch.setattr(windows, 'powershell', run)
    result = windows.apply_os({'os': {'timezone': 'Asia/Tokyo', 'locale': 'ja-JP'}}, True)
    assert not result['applied']
    assert 'culture_error' in result
    assert Path(result['snapshot']).exists()
