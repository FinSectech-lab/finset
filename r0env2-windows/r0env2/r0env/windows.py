"""Windows host integration. No subprocess is started by preview operations."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import subprocess
import sys


def data_dir():
    return Path(os.environ.get('R0ENV_CONFIG_DIR') or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'r0env2').expanduser().resolve()


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell(script):
    if sys.platform != 'win32':
        raise RuntimeError('此操作需要 Windows，请在 Windows 上运行。')
    script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(); " + script
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    result = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
                             '-EncodedCommand', encoded], capture_output=True,
                            encoding='utf-8', errors='replace', timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'PowerShell failed')
    return result.stdout.strip()


def windows_timezone(iana):
    from tzlocal.windows_tz import tz_win, win_tz
    if iana and iana in win_tz:
        return iana
    if not iana or iana not in tz_win:
        raise ValueError(f'无法映射 Windows 时区: {iana!r}')
    return tz_win[iana]


def culture_name(value):
    return value.split('.')[0].replace('_', '-')


def local_state():
    return json.loads(powershell("[ordered]@{timezone=(Get-TimeZone).Id; "
        "locale=(Get-Culture).Name; system_locale=(Get-WinSystemLocale).Name} | ConvertTo-Json -Compress"))


def apply_os(profile, execute=False):
    tz = windows_timezone(profile['os']['timezone'])
    locale = culture_name(profile['os']['locale'])
    result = {'timezone': tz, 'iana_timezone': profile['os']['timezone'],
              'locale': locale, 'applied': False, 'mode': 'execute' if execute else 'dry-run'}
    if not execute:
        return result
    # Preflight before making any changes; caller must use an elevated terminal.
    powershell("if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run apply from an administrator terminal.' }; "
               f"Get-TimeZone -Id {quote(tz)} | Out-Null; [Globalization.CultureInfo]::GetCultureInfo({quote(locale)}) | Out-Null")
    before = local_state()
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    snapshot = folder / ('snapshot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
    snapshot.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding='utf-8')
    result['snapshot'] = str(snapshot)
    for name, command in [('timezone', f'Set-TimeZone -Id {quote(tz)}'),
                          ('culture', f'Set-Culture -CultureInfo {quote(locale)}'),
                          ('system_locale', f'Set-WinSystemLocale -SystemLocale {quote(locale)}')]:
        try:
            powershell(command)
            result[name + '_applied'] = True
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            result[name + '_error'] = str(exc)
            break
    result['applied'] = all(result.get(k + '_applied') for k in ('timezone', 'culture', 'system_locale'))
    result['restart_required'] = before['system_locale'].lower() != locale.lower() and result.get('system_locale_applied', False)
    return result


def restore(snapshot):
    state = json.loads(Path(snapshot).read_text(encoding='utf-8'))
    powershell(f"Set-TimeZone -Id {quote(state['timezone'])}; Set-Culture -CultureInfo {quote(state['locale'])}; Set-WinSystemLocale -SystemLocale {quote(state['system_locale'])}")
    return {'rolled_back': True, 'snapshot': str(snapshot), 'restart_may_be_required': True}


def task_name():
    # Separate users' schedules; never run under SYSTEM (wrong locale and proxy).
    return 'r0env2-check-' + os.environ.get('USERNAME', 'user')


def install_timer():
    from .network import proxy_url
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    settings = folder / 'timer.json'
    settings.write_text(json.dumps({'proxy': proxy_url()}, ensure_ascii=False), encoding='utf-8')
    arguments = subprocess.list2cmdline(['-X', 'utf8', '-m', 'r0env', '_scheduled_check', str(settings)])
    script = f"""
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute {quote(sys.executable)} -Argument {quote(arguments)} -WorkingDirectory {quote(Path(__file__).resolve().parent.parent)}
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3)
Register-ScheduledTask -TaskName {quote(task_name())} -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
"""
    powershell(script)
    return {'installed': True, 'task': task_name(), 'interval_seconds': 300, 'requires_logged_in_user': True}


def timer_status():
    name = quote(task_name())
    return powershell(f"$task=Get-ScheduledTask -TaskName {name}; $info=Get-ScheduledTaskInfo -TaskName {name}; [ordered]@{{name=$task.TaskName; state=[string]$task.State; last_run=[string]$info.LastRunTime; next_run=[string]$info.NextRunTime; last_result=$info.LastTaskResult}} | ConvertTo-Json")


def uninstall_timer():
    powershell(f'Unregister-ScheduledTask -TaskName {quote(task_name())} -Confirm:$false')
    return {'uninstalled': True, 'task': task_name()}
