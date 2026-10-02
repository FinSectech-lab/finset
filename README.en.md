# r0env

Automatically match system timezone, locale, and browser fingerprint to the country of your proxy exit IP.

## Features

- 🌍 **IP → Country**: Detect exit IP and resolve country, timezone, ASN
- 🕐 **System timezone**: Real execution, takes effect immediately
- 🗣 **System locale**: Auto-mapped by country (CN / US / JP / KR, etc.)
- 🌐 **Browser fingerprint**: Firefox and Chromium supported
- 🛡 **WebRTC leak protection**: Chromium launch args
- 📡 **DNS modes**: DoH / DoT / UDP / system, with fallback deny
- 🔄 **Scheduled inspection**: systemd timer checks consistency every 5 minutes
- 🔔 **Desktop alerts**: notification when environment is inconsistent
- 🎛 **Dual mode**: proxy / direct, freely switchable

## Requirements

- Linux (Arch / Omarchy recommended)
- Python 3.12+
- A running proxy (Clash / mihomo / sing-box / v2ray)
- sudo privileges

## Installation

Step 1: Extract

```bash
mkdir -p ~/Projects
unzip r0env-*.zip -d ~/Projects/r0env
cd ~/Projects/r0env
```

Step 2: One-shot install

```bash
bash install.sh
```

Step 3: If proxy port is not 7890

```bash
export R0ENV_PROXY=http://127.0.0.1:YOUR_PORT
echo 'export R0ENV_PROXY=http://127.0.0.1:YOUR_PORT' >> ~/.bashrc
source ~/.bashrc
```

## Usage

Preview profile of current exit (no system change):

```bash
r0env
```

One-shot switch (default Firefox):

```bash
r0env apply
```

Switch with Chromium:

```bash
r0env cr
```

Show status:

```bash
r0env status
```

Consistency check:

```bash
r0env check
```

Inspect logs:

```bash
r0env log
```

Timer status:

```bash
r0env timer
```

Help:

```bash
r0env help
```

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `R0ENV_PROXY` | `http://127.0.0.1:7890` | Proxy address. Empty string = direct. |
| `R0ENV_ENGINE` | `firefox` | Browser engine (firefox / chromium) |
| `R0ENV_PROJ` | script directory | Project path |

## Direct Mode

If no proxy is needed, use your real local IP:

```bash
R0ENV_PROXY="" r0env apply
```

## Scheduled Inspection

A systemd timer is installed automatically, checking exit country vs system timezone/locale every 5 minutes.

View logs:

```bash
r0env log
```

View timer:

```bash
r0env timer
```

## Notes

- `r0env apply` modifies system timezone and locale, requires sudo
- Already-open terminals and apps need restart to inherit new locale
- If your proxy port is not 7890, set `R0ENV_PROXY`
- This tool is intended for authorized testing environments only

## License

MIT
