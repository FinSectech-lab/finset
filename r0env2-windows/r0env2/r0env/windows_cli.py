"""Windows command line, including aliases from the original shell launcher."""
import ipaddress
import json
import os
from pathlib import Path
import sys
from . import auto, checker, windows
from .network import exit_ip
from .resolver import Resolver, ipwho_provider

HELP = '''r0env2 — Windows 环境一致性工具
r0env / r0env preview [--ip IP] [--proxy URL] [--output FILE]  预览
r0env IP                             指定 IPv4/IPv6 预览
r0env apply [--ip IP]                 应用 Windows 时区/区域，保存浏览器配置（管理员）
r0env ff / r0env cr                   应用并生成 Firefox / Chromium 配置
r0env browser                        用已保存的配置打开隔离浏览器；关闭窗口即退出
r0env acceptance                    Windows 实机验收，打开已安装浏览器并保存报告
r0env doctor                        只读采集 Windows 网络/浏览器环境，不表示无泄漏
r0env status / check                  当前状态 / 一致性检查（0=通过，1=不一致，2=错误）
r0env log / timer                    最近 30 条日志 / 计划任务状态
r0env install / uninstall            安装 / 移除每 5 分钟巡检任务（当前用户登录期间）
r0env restore SNAPSHOT               恢复 apply 前的 Windows 设置（管理员）
r0env init / resolve / plan / inspect / rollback / monitor  原 Python CLI 接口
r0env legacy ...                     显式使用原 Python CLI（含原 apply/check 接口）
所有日常命令支持 --direct（直连，忽略代理）。
环境变量：R0ENV_PROXY（默认 http://127.0.0.1:7890；空值直连）
          R0ENV_ENGINE（firefox/chromium）、R0ENV_CONFIG_DIR（配置和日志目录）
修改系统 locale 可能需要重启；不更换 Windows 显示语言或安装语言包。
'''


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def preview_args(args, execute=False, engine=None):
    # Explicit --ip must take priority over auto-detection.
    values = list(args)
    if '--ip' not in values and not any(a.startswith('--ip=') for a in values):
        values.insert(0, '--auto')
    if execute:
        values.append('--execute')
    elif '--execute' in values:
        raise ValueError('preview 不执行修改，请使用 apply。')
    if engine:
        values += ['--engine', engine]
    return values


def legacy(args):
    from . import cli
    old = sys.argv
    try:
        sys.argv = ['r0env', *args]
        return cli.main() or 0
    finally:
        sys.argv = old


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--direct" in argv:
        os.environ["R0ENV_PROXY"] = ""
        argv.remove("--direct")
    command, rest = (argv[0], argv[1:]) if argv else ('preview', [])
    try:
        if command in ('status', 's', 'log', 'timer', 'install', 'uninstall', 'browser', 'doctor') and rest:
            raise ValueError(f'{command} 不接受额外参数: {rest}')
        if command in ('help', '--help', '-h'):
            print(HELP)
        elif command in ('preview', 'p', 'apply', 'go', 'ff', 'firefox', 'cr', 'chromium'):
            if command == 'apply' and any(a == '--profile' or a.startswith('--profile=') for a in rest):
                return legacy(argv)
            engine = 'firefox' if command in ('ff', 'firefox') else 'chromium' if command in ('cr', 'chromium') else None
            return auto.main(preview_args(rest, execute=command not in ('preview', 'p'), engine=engine))
        elif command in ('check', 'c'):
            return legacy(argv) if rest else checker.main()
        elif command == '_scheduled_check':
            settings_path = Path(rest[0])
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
            os.environ['R0ENV_PROXY'] = settings['proxy']
            os.environ['R0ENV_CONFIG_DIR'] = str(settings_path.parent)
            return checker.main()
        elif command in ('status', 's'):
            report = {'data_dir': str(windows.data_dir())}
            failed = False
            for key, probe in [('egress', lambda: Resolver([ipwho_provider], on_conflict='first').resolve(exit_ip()).__dict__),
                               ('system', windows.local_state)]:
                try:
                    report[key] = probe()
                except Exception as exc:
                    report[key] = {'error': str(exc)}
                    failed = True
            profile_path = windows.data_dir() / 'profile.json'
            profile = json.loads(profile_path.read_text(encoding='utf-8')) if profile_path.exists() else {}
            report['engine'] = profile.get('browser', {}).get('engine', os.environ.get('R0ENV_ENGINE', 'firefox'))
            emit(report)
            return 2 if failed else 0
        elif command == 'acceptance':
            from .acceptance import main as acceptance_main
            return acceptance_main(rest)
        elif command == 'doctor':
            from .diagnostics import collect
            emit(collect())
        elif command == 'log':
            checker.show_log()
        elif command == 'timer':
            print(windows.timer_status())
        elif command == 'install':
            emit(windows.install_timer())
        elif command == 'uninstall':
            emit(windows.uninstall_timer())
        elif command == 'restore':
            if len(rest) != 1:
                raise ValueError('用法: r0env restore SNAPSHOT.json')
            emit(windows.restore(rest[0]))
        elif command == 'browser':
            from .browser_runtime import launch
            launch()
        elif command == 'legacy':
            return legacy(rest)
        elif command in ('init', 'resolve', 'plan', 'inspect', 'rollback', 'monitor'):
            return legacy(argv)
        else:
            try:
                ipaddress.ip_address(command)
            except ValueError:
                raise ValueError(f'未知命令: {command}；使用 r0env help 查看帮助') from None
            return auto.main(preview_args(['--ip', command, *rest]))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f'r0env: {exc}', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2


if __name__ == '__main__':
    raise SystemExit(main())
