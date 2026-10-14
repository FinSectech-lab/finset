English | [中文](README.zh-CN.md)

# r0env2

Windows version of r0env.

v0.2.0 preview: environment consistency configuration. It is not a full-machine traffic takeover or a zero-leak tool. Recommended as a GitHub Pre-release.

For Windows 10/11, Windows PowerShell 5.1, and Python 3.10+. The original project is in the adjacent `r0env` directory. This directory is a separate Windows version. It keeps exit-IP lookup, profile preview, timezone and locale switching, browser configuration, consistency checks, scheduled inspection, logs, and the original Python CLI.

## Windows acceptance

New `acceptance.cmd`: opens the actually installed Edge, Chrome, or Firefox, measures system and browser exit IP, language, timezone, and WebRTC, and writes a report. Steps and unverified scope are in `ACCEPTANCE.md`. This script is the live-test entry point. It does not mean one-click full-machine adjustment is finished.

## Install

1. Copy the whole `r0env2` folder to a fixed Windows path, for example `C:\Tools\r0env2`. Spaces and Chinese characters in the path are allowed.
2. Install Python 3.10 or newer, including the Python Launcher. This round was tested with Python 3.12 x64. Also install the Microsoft Visual C++ x64 Redistributable. Missing `msvcp140_1.dll` stops the browser from starting. If the runtime is already installed, choose Repair.
3. In that folder, run `.\install.cmd` in PowerShell. It creates a Windows virtual environment, installs dependencies and Firefox/Chromium, adds the current user to PATH, and creates a scheduled task that inspects every 5 minutes.
4. Open a new terminal and run `r0env help` or `r0env2 help`. If an older program with the same name is already on PATH, use `C:\Tools\r0env2\r0env.cmd`.

Host checks only, without downloading browsers or registering the task:

```powershell
.\install.cmd -SkipBrowsers -SkipTimer
```

Do not copy the Linux `.venv`. The first install needs network access for Python packages and Playwright browsers. If pip or the browser download needs a proxy:

```powershell
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
```

## Usage

```text
r0env                          # preview, never changes the system
r0env 8.8.8.8                  # preview a given IPv4/IPv6
r0env preview --output plan.json
r0env apply                    # fetch the exit and apply; needs an admin terminal
r0env apply --ip 8.8.8.8       # apply for a given target IP
r0env ff                       # Firefox configuration
r0env cr                       # Chromium configuration
r0env browser                  # open an isolated browser with the saved apply config
r0env status
r0env check
r0env log
r0env timer
r0env install                  # install or update the current-user inspection task
r0env uninstall                # remove only the inspection task
r0env restore 'C:\path\snapshot-....json'  # restore host settings, admin terminal
```

Aliases kept: `p`, `go`, `firefox`, `chromium`, `s`, `c`.

Default proxy is the local Clash/mihomo HTTP proxy `http://127.0.0.1:7890`. Default browser is Firefox:

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:7890'
$env:R0ENV_ENGINE = 'chromium'
r0env preview
r0env preview --direct         # this run goes direct and ignores other proxy settings
r0env check --direct
r0env install --direct         # scheduled inspection also uses direct
```

`--direct` works on all ordinary commands. In Python, an empty `R0ENV_PROXY` also means direct. Windows PowerShell 5.1 may drop an empty environment variable, so prefer `--direct`.

IP lookup uses the HTTP/HTTPS proxy. A SOCKS address can be reached through the Clash/mihomo mixed port as HTTP. Changing the proxy node is done in the proxy app.

## Windows behavior vs the original

| Original | Windows |
| --- | --- |
| `timedatectl set-timezone` | IANA to Windows ID, `Set-TimeZone` |
| `/etc/locale.conf`, `locale-gen` | `Set-Culture`, `Set-WinSystemLocale` |
| systemd check every 5 minutes | Scheduled task for the current interactive user |
| `journalctl` / fixed Linux log path | `%LOCALAPPDATA%\r0env2\check_consistency.log`; `log` shows the last 30 lines |
| shell launcher | `r0env.cmd`, `r0env2.cmd`, and Python console scripts |
| nftables emergency block | Same-named Windows Firewall outbound block rules; not run by default |

Change system settings from an admin terminal of the same Windows user, so another admin account's locale is not changed. After a system locale change, a reboot may be required. User locale applies to new processes. The tool does not reboot, does not change the Windows display language, and does not install language packs. The Windows automatic timezone service can overwrite a manual choice; inspection reports the drift.

The browser uses the proxy address saved by `apply` by default. An explicit `R0ENV_PROXY` or `browser --direct` overrides it. `status` still shows readable system settings if the exit lookup fails, and shows the saved browser engine.

Each `apply` saves a separate `snapshot-*.json` before changing anything, and saves `profile.json`. `R0ENV_CONFIG_DIR` can override the data directory. The scheduled task records the proxy address at install time. After changing the proxy address or data directory, run `r0env install` again. The task runs while the current user is logged in. It does not save a password and does not check another user's locale as SYSTEM. Failed checks are visible in `r0env log` and `r0env timer`. There is no popup.

`check` exit codes: `0` consistent, `1` inconsistent, `2` lookup or system error. `apply` exit codes: `0` host settings applied, `1` partial failure, `2` precondition or other error. The check may fail until the system locale takes effect after reboot.

## Actual scope of browser, DNS, and WebRTC

In the original project, Browser/WebRTC `apply` only returns data, and DNS execution has no runner. This version keeps plan generation, explicitly returns dry-run, and does not treat generated config as an already-modified browser. The host changes from `apply` are timezone and locale. `r0env browser` is what passes the saved config into an isolated Playwright instance.

Firefox uses locale, timezone, viewport, and UA settings, disables WebRTC, and configures DoH in the profile. Chromium uses an isolated context and a policy that disables non-proxy UDP. DNS is handled by the proxy or the system. The temporary session is discarded when the browser exits. This command does not change system DNS, existing browsers, or the proxy app. `check` only compares exit country, timezone, and locale. It does not mean DNS or WebRTC leak checks have passed. The original DNS/ICE analysis functions remain available for Python calls.

Country locale mapping matches the original: US, GB, JP, CN, DE, FR, KR, SG, HK, TW, AU, CA. Everything else falls back to `en-US`. GeoIP accuracy depends on the provider.

The original Python CLI commands `init`, `resolve`, `plan`, `inspect`, `rollback`, and `monitor` remain. The original `apply --target ... --profile ... --confirm ...` and `check --target ...` also work. Use `r0env legacy ...` to call the original interface without ambiguity. The original config `apply`/`rollback` there is still a placeholder not wired to the runtime. Real host restore uses `restore`.

## Verify and uninstall

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\python.exe -m pytest -q
.\package.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1
```

The uninstall script removes the task and the user PATH entry. It keeps the project, logs, snapshots, and system settings. Restore system settings with `restore` first.

Migration was done on Linux. 66 automated tests passed. Windows system calls are mocked in tests and do not replace live acceptance. A user verified, on a Windows 10 22H2 x64 VMware VM with Python 3.12, proxy exit lookup, system timezone, current-user locale format, system locale after reboot, and isolated Firefox exit, language, timezone, and WebRTC interface disable. Windows 11, Chromium, the scheduled task, the restore flow, and the full acceptance script were not live-verified in this round. DNS, IPv6, and disconnect protection are not promised as leak-free. See `WINDOWS_TEST.md`.

Implementation references: `Set-WinSystemLocale`, `Set-Culture`, scheduled-task triggers, and tzlocal timezone mapping.

## Proxy port and common issues

A normal user only needs a proxy running on their own Windows. SSH is not required. Use the HTTP or mixed port of the actual proxy app. The default `7890` may not apply.

PowerShell, current window:

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:7890'
.\r0env.cmd preview
```

CMD, current window:

```cmd
set R0ENV_PROXY=http://127.0.0.1:7890
r0env.cmd preview
```

Save for the current user. New terminals pick it up. Admin is not required:

```cmd
setx R0ENV_PROXY "http://127.0.0.1:7890"
```

- `WinError 10061`: check that the proxy is running and the port is correct.
- `all GeoIP sources failed`: the default source is only `ipwho.is`. If that site is unreachable, try a working HTTP proxy. `--ip` does not change the real exit IP.
- Download finished but `msvcp140_1.dll` is missing: install or repair the x64 runtime above, then start the browser.
- System locale is still the old value: reboot as the output says, then check `(Get-WinSystemLocale).Name`.
- `ff` and `cr` apply system settings and save config. They do not open a browser. Use `browser` to open one.
- Config is saved per user. Run `apply` and `browser` under the same account. Closing the browser does not restore system settings.
- If you use a VM plus SSH proxy forwarding, a reboot drops the tunnel and it must be rebuilt. `127.0.0.1` inside the VM is the VM itself.

This only syncs local environment settings. It does not guarantee that an account will avoid platform risk controls.
