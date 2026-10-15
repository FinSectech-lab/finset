"""macOS host integration; elevate only the system timezone command."""
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LABEL = 'io.r0env.macos.check'


def require_macos():
    if sys.platform != 'darwin':
        raise RuntimeError('此操作需要 macOS。')


def require_user():
    require_macos()
    if os.geteuid() == 0:
        raise RuntimeError('请不要 sudo 运行整个程序；在日常账户下运行，修改时区时会单独请求 sudo。')


def data_dir():
    return Path(os.environ.get('R0ENV_CONFIG_DIR') or Path.home() / 'Library/Application Support/r0env3').expanduser().resolve()


def run(args):
    require_macos()
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'命令失败: {args[0]}')
    return result.stdout.strip()


def private_bytes(path, contents):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def private_json(path, data):
    private_bytes(path, json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))


def validate_timezone(value):
    if not isinstance(value, str) or value.startswith(('/', '-')) or '..' in value.split('/'):
        raise ValueError('无效 IANA 时区')
    ZoneInfo(value)
    return value


def normalize_locale(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z]{2,3}[-_][A-Za-z]{2}', value):
        raise ValueError('区域必须是 ja-JP/en-US 等语言-地区代码')
    language, region = value.replace('_', '-').split('-')
    return language.lower() + '_' + region.upper()


def preferences():
    return plistlib.loads(run(['/usr/bin/defaults', 'export', 'NSGlobalDomain', '-']).encode())


def local_state():
    require_user()
    target = str(Path('/etc/localtime').resolve())
    if '/zoneinfo/' not in target:
        raise RuntimeError('无法从 /etc/localtime 确认 IANA 时区，拒绝猜测。')
    prefs = preferences()
    return {'timezone': target.split('/zoneinfo/', 1)[1],
            'locale': prefs.get('AppleLocale'),
            'locale_present': 'AppleLocale' in prefs,
            'languages': prefs.get('AppleLanguages'),
            'scope': 'timezone=system; locale=current user; display language unchanged'}


def authorize():
    require_user()
    # Inherit the terminal so sudo can request a password; never capture credentials.
    if subprocess.run(['/usr/bin/sudo', '-v'], timeout=120).returncode:
        raise RuntimeError('未获得修改系统时区的权限；尚未修改设置。')


def write_timezone(value):
    run(['/usr/bin/sudo', '-n', '/usr/sbin/systemsetup', '-settimezone', validate_timezone(value)])


def apply_os(profile, execute=False):
    tz = validate_timezone(profile['os']['timezone'])
    locale = normalize_locale(profile['os']['locale'])
    report = {'timezone': tz, 'locale': locale, 'applied': False,
              'mode': 'execute' if execute else 'dry-run', 'scope': 'system timezone + current-user region'}
    if not execute:
        return report
    require_user()
    before = local_state()
    authorize()
    snapshot = data_dir() / ('snapshot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
    private_json(snapshot, {'schema': 1, 'platform': 'darwin', 'uid': os.getuid(), 'state': before})
    report['snapshot'] = str(snapshot)
    try:
        write_timezone(tz)
        run(['/usr/bin/defaults', 'write', '-g', 'AppleLocale', '-string', locale])
        actual = local_state()
        report.update(actual=actual, timezone_applied=actual['timezone'] == tz,
                      locale_applied=actual['locale'] == locale)
        report['applied'] = report['timezone_applied'] and report['locale_applied']
        report['logout_may_be_required'] = before['locale'] != locale
        if not report['applied']:
            report['error'] = '写入后读回不一致；可能被自动时区覆盖，请检查系统设置。'
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        report['error'] = str(exc)
        report['partial_changes_possible'] = True
    return report


def restore(snapshot):
    require_user()
    document = json.loads(Path(snapshot).read_text(encoding='utf-8'))
    if document.get('schema') != 1 or document.get('platform') != 'darwin' or document.get('uid') != os.getuid():
        raise ValueError('快照格式、平台或用户不匹配')
    state = document['state']
    validate_timezone(state['timezone'])
    if not isinstance(state.get('locale_present'), bool):
        raise ValueError('快照缺少 locale_present')
    if state['locale_present'] and not isinstance(state.get('locale'), str):
        raise ValueError('快照区域值无效')
    report = {'rolled_back': False, 'snapshot': str(snapshot),
              'logout_may_be_required': True, 'profile_restored': False}
    authorize()
    try:
        write_timezone(state['timezone'])
        report['timezone_command_completed'] = True
        if state['locale_present']:
            run(['/usr/bin/defaults', 'write', '-g', 'AppleLocale', '-string', state['locale']])
        elif 'AppleLocale' in preferences():
            run(['/usr/bin/defaults', 'delete', '-g', 'AppleLocale'])
        report['locale_command_completed'] = True
        actual = local_state()
        report['actual'] = actual
        report['rolled_back'] = all(actual[k] == state[k] for k in ('timezone', 'locale', 'locale_present'))
        if not report['rolled_back']:
            report['error'] = '恢复后读回不一致，请根据 actual 核对。'
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        report['error'] = str(exc)
        report['partial_changes_possible'] = True
    return report


def agent_path():
    return Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')


def timer_status():
    require_user()
    return run(['/bin/launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'])


def uninstall_timer():
    require_user()
    service = f'gui/{os.getuid()}/{LABEL}'
    # Only bootout if the service exists; do not swallow a bootout failure.
    probe = subprocess.run(['/bin/launchctl', 'print', service], capture_output=True, timeout=30)
    if probe.returncode == 0:
        run(['/bin/launchctl', 'bootout', service])
    agent_path().unlink(missing_ok=True)
    return {'uninstalled': True, 'label': LABEL}


def install_timer():
    require_user()
    from .network import proxy_url
    folder = data_dir()
    settings = folder / 'timer.json'
    path = agent_path()
    old_settings = settings.read_bytes() if settings.exists() else None
    old_agent = path.read_bytes() if path.exists() else None
    service = f'gui/{os.getuid()}/{LABEL}'
    probe = subprocess.run(['/bin/launchctl', 'print', service], capture_output=True, timeout=30)
    was_loaded = probe.returncode == 0
    if was_loaded and old_agent is None:
        raise RuntimeError('发现已加载任务但找不到本工具的 plist，拒绝覆盖未知任务。')
    document = {'Label': LABEL, 'ProgramArguments': [sys.executable, '-m', 'r0env', '_scheduled_check', str(settings)],
                'WorkingDirectory': str(Path(__file__).resolve().parent.parent),
                'StartInterval': 300, 'RunAtLoad': True,
                'StandardOutPath': str(folder / 'launchd.stdout.log'),
                'StandardErrorPath': str(folder / 'launchd.stderr.log')}
    # Stop first, but keep the old files until the new settings are ready.
    if was_loaded:
        run(['/bin/launchctl', 'bootout', service])
    try:
        private_json(settings, {'proxy': proxy_url()})
        private_bytes(path, plistlib.dumps(document))
        run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(path)])
    except Exception as exc:
        try:
            for target, contents in ((settings, old_settings), (path, old_agent)):
                if contents is None:
                    target.unlink(missing_ok=True)
                else:
                    private_bytes(target, contents)
            if was_loaded:
                run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(path)])
        except Exception as rollback_error:
            raise RuntimeError(f'新任务注册失败: {exc}；旧任务恢复也失败: {rollback_error}。请检查 timer。') from exc
        raise RuntimeError(f'新任务注册失败: {exc}；旧配置已恢复。') from exc
    return {'installed': True, 'label': LABEL, 'interval_seconds': 300,
            'requires_logged_in_user': True, 'auto_correct': False}
