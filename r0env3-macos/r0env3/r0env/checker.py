"""Read-only comparison; never claims DNS or whole-host protection."""
import json
from collections import deque
from datetime import datetime
from . import macos
from .auto import LOCALE_MAP, DEFAULT_LOCALE
from .network import exit_ip
from .resolver import Resolver, ipwho_provider


def compare(result, actual):
    expected = {'timezone': result.timezone,
                'locale': macos.normalize_locale(LOCALE_MAP.get(result.country_code, DEFAULT_LOCALE)[1])}
    checks = {k: actual.get(k) == v for k, v in expected.items()}
    return {'ok': all(checks.values()), 'checks': checks, 'expected': expected,
            'actual': actual, 'ip': result.ip, 'country': result.country_code}


def log(message):
    line = f'[{datetime.now().isoformat(timespec="seconds")}] {message}'
    print(line)
    folder = macos.data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'check_consistency.log'
    if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
        path.replace(folder / 'check_consistency.log.1')
    with path.open('a', encoding='utf-8') as stream:
        stream.write(line + '\n')


def main():
    try:
        result = Resolver([ipwho_provider], on_conflict='first').resolve(exit_ip())
        report = compare(result, macos.local_state())
        log(json.dumps(report, ensure_ascii=False))
        return 0 if report['ok'] else 1
    except Exception as exc:
        log(f'ERROR {exc}')
        return 2


def show_log():
    path = macos.data_dir() / 'check_consistency.log'
    if not path.exists():
        print('暂无巡检日志。')
        return
    with path.open(encoding='utf-8') as stream:
        print(''.join(deque(stream, maxlen=30)), end='')
