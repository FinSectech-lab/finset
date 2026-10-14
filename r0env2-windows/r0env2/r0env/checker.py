"""Exit country versus Windows timezone and culture consistency check."""
from collections import deque
from datetime import datetime
import json
from . import windows
from .auto import LOCALE_MAP, DEFAULT_LOCALE
from .network import exit_ip
from .resolver import Resolver, ipwho_provider


def log(message):
    line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}'
    print(line)
    folder = windows.data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'check_consistency.log'
    if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
        path.replace(folder / 'check_consistency.log.1')
    with path.open('a', encoding='utf-8') as stream:
        stream.write(line + '\n')


def compare(result, actual):
    expected_tz = windows.windows_timezone(result.timezone)
    expected_locale = LOCALE_MAP.get(result.country_code, DEFAULT_LOCALE)[1]
    checks = {'timezone': actual['timezone'] == expected_tz,
              'locale': actual['locale'].lower() == expected_locale.lower(),
              'system_locale': actual['system_locale'].lower() == expected_locale.lower()}
    return {'ok': all(checks.values()), 'checks': checks,
            'expected': {'timezone': expected_tz, 'locale': expected_locale, 'system_locale': expected_locale},
            'actual': actual, 'ip': result.ip, 'country': result.country_code}


def main():
    try:
        result = Resolver([ipwho_provider], on_conflict='first').resolve(exit_ip())
        report = compare(result, windows.local_state())
        log(json.dumps(report, ensure_ascii=False))
        log('OK 一致性检查通过' if report['ok'] else 'FAIL 环境不一致；系统 locale 刚修改时可能需要重启')
        return 0 if report['ok'] else 1
    except Exception as exc:
        log(f'ERROR {exc}')
        return 2


def show_log():
    path = windows.data_dir() / 'check_consistency.log'
    if not path.exists():
        print('暂无巡检日志，请先运行 r0env check。')
        return
    with path.open(encoding='utf-8') as stream:
        print(''.join(deque(stream, maxlen=30)), end='')
