"""macOS CLI. Application mutations are always explicit."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
from . import auto, checker, macos
from .network import exit_ip
from .resolver import Resolver, ipwho_provider

HELP = '''r0env3 — macOS 预览版
r0env / preview / p [--ip IP] [--proxy URL] [--direct] [--output FILE]  只预览
r0env IP                         指定 IP 预览，不改变真实出口
r0env apply / go                  修改系统时区、当前用户区域，保存配置和快照
r0env ff / firefox               同 apply，选择 Firefox
r0env cr / chromium              同 apply，选择 Chromium
r0env browser                    启动已保存配置的隔离浏览器
r0env status / s                 读取系统状态和出口
r0env check / c                  检查出口地区与时区、用户区域一致性
r0env doctor                     只读系统/网络诊断
r0env acceptance [--output DIR] [--headless]  验收隔离浏览器并保存报告
r0env install / uninstall        添加/删除每 5 分钟的当前用户 LaunchAgent
r0env timer / log                任务状态 / 最近 30 条日志
r0env restore SNAPSHOT           恢复同一用户快照中的时区和区域
r0env resolve --ip IP            GeoIP 查询
r0env init [IP]                  兼容入口：预览
r0env inspect                   兼容入口：只读系统状态
r0env plan --profile FILE        只读 JSON/YAML 配置预览
r0env rollback --snapshot FILE   restore 的别名（只接受 macOS 快照）
环境变量 R0ENV_PROXY 默认 http://127.0.0.1:7890；R0ENV_ENGINE 默认 firefox
R0ENV_CONFIG_DIR 默认 ~/Library/Application Support/r0env3
不要 sudo 运行整个程序；apply/restore 仅在修改系统时区时请求 sudo。
巡检不自动修复；不修改显示语言、系统 DNS、全机路由和已安装浏览器。
'''


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def preview_args(args, execute=False, engine=None):
    values = list(args)
    if not any(a == '--ip' or a.startswith('--ip=') for a in values):
        values.insert(0, '--auto')
    if '--execute' in values and not execute:
        raise ValueError('preview 不执行修改，请使用 apply。')
    if execute:
        values.append('--execute')
    if engine:
        values += ['--engine', engine]
    return values


def doctor():
    macos.require_user()
    result = {}
    for name, args in {'version': ['/usr/bin/sw_vers'], 'architecture': ['/usr/bin/uname', '-m'],
                       'dns': ['/usr/sbin/scutil', '--dns'], 'proxy': ['/usr/sbin/scutil', '--proxy']}.items():
        try:
            result[name] = macos.run(args)
        except Exception as exc:
            result[name] = {'error': str(exc)}
    result['browser_apps'] = [str(p) for base in (Path('/Applications'), Path.home() / 'Applications')
                              for name in ('Safari.app', 'Google Chrome.app', 'Microsoft Edge.app', 'Firefox.app')
                              if (p := base / name).exists()]
    result['note'] = '诊断信息不是无泄漏证明；分享前检查网络/用户名等隐私。'
    return result


def main(argv=None):
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if '--direct' in args and any(a == '--proxy' or a.startswith('--proxy=') for a in args):
        print('r0env: --direct 与 --proxy 不能同时使用', file=sys.stderr)
        return 2
    if '--direct' in args:
        os.environ['R0ENV_PROXY'] = ''
        args.remove('--direct')
    cmd, rest = (args[0], args[1:]) if args else ('preview', [])
    try:
        if cmd in ('help', '--help', '-h'):
            print(HELP)
        elif cmd in ('preview', 'p', 'apply', 'go', 'ff', 'firefox', 'cr', 'chromium'):
            engine = 'firefox' if cmd in ('ff', 'firefox') else 'chromium' if cmd in ('cr', 'chromium') else None
            return auto.main(preview_args(rest, cmd not in ('preview', 'p'), engine))
        elif cmd == 'acceptance':
            from .acceptance import main as accept
            return accept(rest)
        elif cmd == '_scheduled_check':
            if len(rest) != 1:
                raise ValueError('缺少任务配置路径')
            path = Path(rest[0])
            os.environ['R0ENV_PROXY'] = json.loads(path.read_text())['proxy']
            os.environ['R0ENV_CONFIG_DIR'] = str(path.parent)
            return checker.main()
        elif cmd in ('restore', 'rollback'):
            if cmd == 'rollback':
                parser = argparse.ArgumentParser(allow_abbrev=False)
                parser.add_argument('--snapshot', required=True)
                rest = [parser.parse_args(rest).snapshot]
            if len(rest) != 1:
                raise ValueError('用法: r0env restore SNAPSHOT.json')
            result = macos.restore(rest[0]); emit(result)
            return 0 if result['rolled_back'] else 1
        elif cmd in ('resolve', 'plan'):
            parser = argparse.ArgumentParser(allow_abbrev=False)
            parser.add_argument('--ip' if cmd == 'resolve' else '--profile', required=True)
            opts = parser.parse_args(rest)
            if cmd == 'resolve':
                emit(Resolver([ipwho_provider], on_conflict='first').resolve(opts.ip).__dict__)
            else:
                import yaml
                emit({'dry_run': True, 'profile': yaml.safe_load(Path(opts.profile).read_text())})
        elif cmd == 'init':
            if len(rest) > 1:
                raise ValueError('用法: r0env init [IP]')
            return auto.main(preview_args(['--ip', rest[0]] if rest else []))
        elif cmd in ('status', 's', 'check', 'c', 'log', 'timer', 'install', 'uninstall', 'doctor', 'browser', 'inspect'):
            if rest:
                raise ValueError(f'{cmd} 不接受额外参数；使用 R0ENV_PROXY 环境变量设置代理')
            if cmd in ('check', 'c'):
                return checker.main()
            if cmd in ('status', 's'):
                report = {'data_dir': str(macos.data_dir())}
                for name, probe in [('system', macos.local_state), ('egress', exit_ip)]:
                    try: report[name] = probe()
                    except Exception as exc: report[name] = {'error': str(exc)}
                emit(report)
                return 2 if any(isinstance(v, dict) and 'error' in v for v in report.values()) else 0
            if cmd == 'log': checker.show_log()
            elif cmd == 'timer': print(macos.timer_status())
            elif cmd == 'install': emit(macos.install_timer())
            elif cmd == 'uninstall': emit(macos.uninstall_timer())
            elif cmd == 'doctor': emit(doctor())
            elif cmd == 'inspect': emit(macos.local_state())
            elif cmd == 'browser':
                macos.require_user()
                from .browser_runtime import launch
                launch()
        else:
            try: ipaddress.ip_address(cmd)
            except ValueError: raise ValueError(f'未知命令 {cmd}，运行 r0env help 查看帮助') from None
            return auto.main(preview_args(['--ip', cmd, *rest]))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f'r0env: {exc}', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2
