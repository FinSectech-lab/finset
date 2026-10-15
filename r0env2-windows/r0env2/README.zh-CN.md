[English](README.md) | 中文

# r0env2

先设好自己的代理端口。然后一条命令。出口在哪，时区、区域和浏览器就跟到哪。

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)](#先设端口)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](#安装)
[![Version](https://img.shields.io/badge/version-0.2.0-orange)](#为什么是-r0env2)
[![Status](https://img.shields.io/badge/status-pre--release-yellow)](#为什么是-r0env2)

换节点，环境跟着变。预览、应用、巡检，一次到位。

## 先设端口

默认 `7890` 只是起点。用你代理软件实际的 HTTP 或混合端口。不需要管理员，普通 PowerShell 就能设。

只对当前窗口：

```powershell
$env:R0ENV_PROXY = "http://127.0.0.1:18080"
.\r0env.cmd preview
```

保存到当前 Windows 账户。关掉再开 PowerShell 就能直接用：

```powershell
[Environment]::SetEnvironmentVariable("R0ENV_PROXY", "http://127.0.0.1:18080", "User")
```

CMD，当前窗口：

```cmd
set R0ENV_PROXY=http://127.0.0.1:18080
r0env.cmd preview
```

CMD，保存到当前用户：

```cmd
setx R0ENV_PROXY "http://127.0.0.1:18080"
```

把 `18080` 换成你的端口。

- 在 `boblo` 下设置，只对 `boblo` 生效，`sshuser` 不会同步。
- 保存端口不会自动建立 SSH 隧道。每次仍要开着主机 Clash，并保持 SSH 转发连接。
- `apply` 改系统设置时，仍用管理员 PowerShell。

## 为什么是 r0env2

- 出口 IP 自动识别国家、时区、ASN
- 系统时区切到出口所在地
- 区域按国家映射：US、GB、JP、CN、DE、FR、KR、SG、HK、TW、AU、CA
- Firefox / Chromium 隔离浏览器，带 locale、时区、视口、UA
- 每 5 分钟自动巡检，偏差写进日志
- 每次应用前自动快照，随时恢复
- 原版 Python CLI 全保留，Windows 命令直接用

Linux 版的能力，Windows 上开箱就能跑。

## 安装

1. 把整个 `r0env2` 放到固定路径，例如 `C:\Tools\r0env2`。空格和中文都行。
2. 安装 Python 3.10+（实测 3.12 x64）和 Visual C++ x64 运行库。
3. 在该目录执行：

```powershell
.\install.cmd
```

虚拟环境、依赖、Firefox/Chromium、当前用户 PATH、5 分钟巡检任务，一次装齐。

4. 新开终端：

```powershell
r0env help
```

只要主机检查：

```powershell
.\install.cmd -SkipBrowsers -SkipTimer
```

下载需要代理时：

```powershell
$env:HTTPS_PROXY = 'http://127.0.0.1:18080'
```

## 使用

先看，再切。

```text
r0env                          # 预览，不动系统
r0env 8.8.8.8                  # 指定 IP 预览
r0env preview --output plan.json
r0env apply                    # 一键对齐出口
r0env apply --ip 8.8.8.8
r0env ff                       # Firefox 配置
r0env cr                       # Chromium 配置
r0env browser                  # 打开隔离浏览器
r0env status
r0env check
r0env log
r0env timer
r0env restore 'C:\path\snapshot-....json'
```

别名：`p`、`go`、`firefox`、`chromium`、`s`、`c`。

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:18080'
$env:R0ENV_ENGINE = 'chromium'
r0env preview
r0env preview --direct
r0env check --direct
r0env install --direct
```

`--direct` 走直连。换节点在 Clash / mihomo 里切，环境这边自动跟上。

## 你得到什么

| 能力 | Windows 实现 |
| --- | --- |
| 时区 | IANA 映射到 Windows ID，`Set-TimeZone` |
| 区域 | `Set-Culture`、`Set-WinSystemLocale` |
| 巡检 | 当前用户每 5 分钟计划任务 |
| 日志 | `%LOCALAPPDATA%\r0env2\check_consistency.log`，最近 30 条 |
| 启动器 | `r0env.cmd`、`r0env2.cmd` |
| 浏览器 | 隔离 Playwright，配置由 `apply` 保存 |

`apply` 用管理员终端。每次保存 `snapshot-*.json` 和 `profile.json`。改了代理，再跑一次 `r0env install`。任务在登录期间运行。

| 命令 | 含义 |
| --- | --- |
| `check` 返回 0 | 一致 |
| `apply` 返回 0 | 主机设置已应用 |

## 浏览器

`r0env browser` 用已保存配置打开隔离的 Playwright 实例。

| 引擎 | 配置 |
| --- | --- |
| Firefox | locale、时区、视口、UA、关闭 WebRTC、profile 里的 DoH |
| Chromium | 隔离 context、关闭非代理 UDP |

退出即丢弃临时会话。原 CLI 仍在：`init`、`resolve`、`plan`、`inspect`、`rollback`、`monitor`。用 `r0env legacy ...` 调用。恢复主机用 `restore`。

## 已验证

Windows 10 22H2 x64、VMware、Python 3.12：出口查询、系统时区、当前用户区域、重启后的系统区域，以及隔离 Firefox 的出口、语言、时区和 WebRTC。见 `WINDOWS_TEST.md` 和 `ACCEPTANCE.md`。

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\python.exe -m pytest -q
.\package.ps1
```

## 遇到这些

| 看到 | 这样处理 |
| --- | --- |
| `WinError 10061` | 开代理，核对端口 |
| `all GeoIP sources failed` | 换一个可用的 HTTP 代理 |
| 缺少 `msvcp140_1.dll` | 安装 x64 Visual C++ 运行库 |
| 区域还是旧的 | 重启后查 `(Get-WinSystemLocale).Name` |
| 浏览器没打开 | `ff` 和 `cr` 只保存配置，`browser` 才打开 |
| 虚拟机加 SSH 隧道 | 重启后重建隧道。虚拟机里的 `127.0.0.1` 是虚拟机自己 |
