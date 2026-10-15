English | [中文](README.zh-CN.md)

# r0env3

Set your proxy port first. Then one command. The exit IP decides the timezone, the locale, and the browser.

[![Platform](https://img.shields.io/badge/platform-macOS%2014%2B-000000)](#set-your-port-first)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](#install)
[![Arch](https://img.shields.io/badge/arch-Intel%20%2F%20Apple%20Silicon-blue)](#install)
[![Version](https://img.shields.io/badge/version-0.1.2-orange)](#why-r0env3)

Change the node. The environment follows. Linux and Windows stay in their own directories.

## Set your port first

Use the HTTP or mixed port of your actual proxy. Same Mac, no SSH needed.

This terminal only:

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh preview
```

Save it for new terminals. zsh users add this to `~/.zshrc`, then reopen Terminal:

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
```

Replace `1080` with your port. Keep Clash or mihomo running. `apply` asks for sudo only when it changes the system timezone.

## Why r0env3

- Exit IP resolves to country, timezone, and ASN
- System timezone switches to the exit location
- Current-user locale follows the exit country
- Isolated Firefox or Chromium with locale, timezone, viewport, and UA
- Inspection every 5 minutes, drift written to the log
- Snapshot before every apply, restore whenever you want
- Original command stays `r0env`. Other versions stay untouched

## Install

1. Download `r0env3-macos.zip` from the GitHub Release, or use Code → Download ZIP and open the macOS source folder.
2. Put it somewhere fixed, for example `~/Applications/r0env3`.
3. Check Python. Need 3.10+, 3.12 recommended:

```bash
python3 --version
```

Missing it? Install the macOS universal2 package from [python.org/downloads/macos](https://www.python.org/downloads/macos/), then reopen Terminal.

4. Open the proxy, connect a node, then:

```bash
cd "$HOME/Applications/r0env3"
export HTTPS_PROXY="http://127.0.0.1:1080"
export R0ENV_PROXY="http://127.0.0.1:1080"
bash install.sh
./r0env.sh help
```

Virtual environment, dependencies, Firefox and Chromium. One run. Optional:

```bash
bash install.sh --skip-browsers
bash install.sh --with-timer
```

Keep the project folder where you installed it. Move it, reinstall.

## First run

Preview, then apply, then open the browser.

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh preview
```

Check exit IP, country, timezone, and browser language. Then:

```bash
./r0env.sh apply
```

Sudo password is hidden while you type. That is normal. It saves a snapshot, sets the system timezone and the current-user locale, then reads them back. Note the `snapshot` path in the output.

Open the isolated browser:

```bash
./r0env.sh browser
```

Use the window it opens. Keep the proxy and that terminal running.

Chromium:

```bash
./r0env.sh cr
./r0env.sh browser
```

Back to Firefox:

```bash
./r0env.sh ff
./r0env.sh browser
```

Close the old isolated browser before switching. Chromium here is the one the tool downloads.

## Everyday use

Same region, already applied:

```bash
cd "$HOME/Applications/r0env3"
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh browser
```

New region: close the old browser, then `preview` → `apply` → `browser`.

## Commands

Prefix with `./r0env.sh`, or use `.venv/bin/r0env`.

| Command | What it does |
| --- | --- |
| `preview`, `p` | Preview |
| `apply`, `go` | Apply timezone, locale, and save the profile |
| `ff`, `firefox` | Apply with Firefox |
| `cr`, `chromium` | Apply with Chromium |
| `browser` | Open the isolated browser |
| `status`, `s` | System state and exit |
| `check`, `c` | Consistency check |
| `doctor` | macOS version, arch, DNS, proxy, browser paths |
| `acceptance` | Browser report |
| `install`, `uninstall` | Add or remove the LaunchAgent |
| `timer`, `log` | Task status, last 30 log lines |
| `restore FILE` | Restore a snapshot for this user |

Also: `resolve --ip IP`, `init`, `inspect`, `plan --profile FILE`, `rollback --snapshot FILE`.

```bash
./r0env.sh preview --proxy http://127.0.0.1:1080
./r0env.sh preview --ip 8.8.8.8 --direct
./r0env.sh restore "$HOME/Library/Application Support/r0env3/snapshot-实际文件名.json"
```

`--direct` goes direct. Switch the node in Clash or mihomo. The environment follows.

## What you get

| Capability | On macOS |
| --- | --- |
| Timezone | `systemsetup`, sudo only for this step |
| Locale | Current-user AppleLocale |
| Inspection | LaunchAgent every 300 seconds while you are logged in |
| Logs | `~/Library/Application Support/r0env3` |
| Launcher | `./r0env.sh` |
| Browser | Isolated Playwright, profile saved by `apply` |

Each `apply` saves a snapshot and `profile.json` with mode 600. Change the port, then run `./r0env.sh install` again.

## Browser

`./r0env.sh browser` opens an isolated Playwright instance with the saved profile.

| Engine | Config |
| --- | --- |
| Firefox | Locale, timezone, viewport, UA, WebRTC off, DoH in the profile |
| Chromium | Isolated context, non-proxy UDP off |

Session ends when the browser closes. Restore the host with `restore`.

## Verified path

```bash
./r0env.sh status
./r0env.sh check
./r0env.sh acceptance
./r0env.sh acceptance --headless --output "$HOME/Desktop/r0env-report"
```

Acceptance opens the isolated browser, hits ipwho.is, and reads language, timezone, and WebRTC. See `MACOS_TEST.md`.

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
python3 package.py
```

## If something looks wrong

| You see | Do this |
| --- | --- |
| `python3: command not found` | Install Python, reopen Terminal |
| `install.sh` not found | `cd` into the folder that contains it |
| `Permission denied` | `bash r0env.sh help` |
| `Connection refused` | Start the proxy, check the port. `127.0.0.1` is this Mac |
| `all GeoIP sources failed` | Proxy cannot reach ipwho.is |
| Browser binary missing | `.venv/bin/python -m playwright install firefox chromium` |
| Asked to run apply first | Run `apply` under this same account |
| Timezone snaps back | Check automatic timezone in System Settings |
| LaunchAgent failed | Run `doctor`, check `timer` |
| Sudo rejected | Use your everyday admin account |

```bash
./r0env.sh doctor
./r0env.sh log
```
