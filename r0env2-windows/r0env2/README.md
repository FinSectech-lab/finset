English | [中文](README.zh-CN.md)

# r0env2

Set your proxy port first. Then one command. The exit IP decides the timezone, the locale, and the browser.

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)](#set-your-port-first)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](#install)
[![Version](https://img.shields.io/badge/version-0.2.0-orange)](#why-r0env2)
[![Status](https://img.shields.io/badge/status-pre--release-yellow)](#why-r0env2)

Change the node. The environment follows.

## Set your port first

Default `7890` is only a starting point. Use the HTTP or mixed port of your actual proxy. No admin required. A normal PowerShell is enough.

This window only:

```powershell
$env:R0ENV_PROXY = "http://127.0.0.1:18080"
.\r0env.cmd preview
```

Save it for this Windows user. New terminals pick it up after you reopen PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("R0ENV_PROXY", "http://127.0.0.1:18080", "User")
```

CMD, this window:

```cmd
set R0ENV_PROXY=http://127.0.0.1:18080
r0env.cmd preview
```

CMD, save for this user:

```cmd
setx R0ENV_PROXY "http://127.0.0.1:18080"
```

Replace `18080` with your port.

- Set under `boblo`, it applies to `boblo` only. `sshuser` does not inherit it.
- Saving the port does not open the tunnel. Keep Clash running on the host, and keep the SSH forward up.
- `apply` still uses an admin PowerShell when it changes system settings.

## Why r0env2

- Exit IP resolves to country, timezone, and ASN
- System timezone switches to the exit location
- Locale maps by country: US, GB, JP, CN, DE, FR, KR, SG, HK, TW, AU, CA
- Isolated Firefox or Chromium with locale, timezone, viewport, and UA
- Inspection every 5 minutes, drift written to the log
- Snapshot before every apply, restore whenever you want
- Original Python CLI kept. Windows commands ready to run

The Linux workflow, on Windows, out of the box.

## Install

1. Copy the whole `r0env2` folder to a fixed path, for example `C:\Tools\r0env2`. Spaces and Chinese characters are fine.
2. Install Python 3.10+ (tested on 3.12 x64) and the Visual C++ x64 Redistributable.
3. In that folder:

```powershell
.\install.cmd
```

Virtual environment, dependencies, Firefox and Chromium, user PATH, and the 5-minute inspection task. One run.

4. Open a new terminal:

```powershell
r0env help
```

Host checks only:

```powershell
.\install.cmd -SkipBrowsers -SkipTimer
```

If the download needs a proxy:

```powershell
$env:HTTPS_PROXY = 'http://127.0.0.1:18080'
```

## Usage

Preview first. Apply when it looks right.

```text
r0env                          # preview, system stays untouched
r0env 8.8.8.8                  # preview a given IP
r0env preview --output plan.json
r0env apply                    # align to the exit
r0env apply --ip 8.8.8.8
r0env ff                       # Firefox profile
r0env cr                       # Chromium profile
r0env browser                  # open the isolated browser
r0env status
r0env check
r0env log
r0env timer
r0env restore 'C:\path\snapshot-....json'
```

Aliases: `p`, `go`, `firefox`, `chromium`, `s`, `c`.

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:18080'
$env:R0ENV_ENGINE = 'chromium'
r0env preview
r0env preview --direct
r0env check --direct
r0env install --direct
```

`--direct` goes direct. Switch the node in Clash or mihomo. The environment follows.

## What you get

| Capability | On Windows |
| --- | --- |
| Timezone | IANA mapped to a Windows ID, `Set-TimeZone` |
| Locale | `Set-Culture`, `Set-WinSystemLocale` |
| Inspection | Scheduled task every 5 minutes for the current user |
| Logs | `%LOCALAPPDATA%\r0env2\check_consistency.log`, last 30 lines |
| Launcher | `r0env.cmd`, `r0env2.cmd` |
| Browser | Isolated Playwright, config saved by `apply` |

`apply` from an admin terminal. Each run saves `snapshot-*.json` and `profile.json`. Change the proxy, then run `r0env install` again. The task runs while you are logged in.

| Command | Meaning |
| --- | --- |
| `check` 0 | Consistent |
| `apply` 0 | Host settings applied |

## Browser

`r0env browser` opens an isolated Playwright instance with the saved profile.

| Engine | Config |
| --- | --- |
| Firefox | Locale, timezone, viewport, UA, WebRTC off, DoH in the profile |
| Chromium | Isolated context, non-proxy UDP off |

Session is discarded when the browser exits. Original CLI still there: `init`, `resolve`, `plan`, `inspect`, `rollback`, `monitor`. Call it with `r0env legacy ...`. Restore the host with `restore`.

## Verified

Windows 10 22H2 x64, VMware, Python 3.12: exit lookup, system timezone, current-user locale, system locale after reboot, isolated Firefox exit, language, timezone, and WebRTC. See `WINDOWS_TEST.md` and `ACCEPTANCE.md`.

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\python.exe -m pytest -q
.\package.ps1
```

## If something looks wrong

| You see | Do this |
| --- | --- |
| `WinError 10061` | Start the proxy, check the port |
| `all GeoIP sources failed` | Point at a working HTTP proxy |
| Missing `msvcp140_1.dll` | Install the x64 Visual C++ runtime |
| Locale still old | Reboot, then `(Get-WinSystemLocale).Name` |
| Browser did not open | `ff` and `cr` save the profile. `browser` opens it |
| VM plus SSH tunnel | Rebuild the tunnel after reboot. `127.0.0.1` in the VM is the VM itself |
