[English](README.md) | 中文

# r0env3

先设好自己的代理端口。然后一条命令。出口在哪，时区、区域和浏览器就跟到哪。

[![Platform](https://img.shields.io/badge/platform-macOS%2014%2B-000000)](#先设端口)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](#安装)
[![Arch](https://img.shields.io/badge/arch-Intel%20%2F%20Apple%20Silicon-blue)](#安装)
[![Version](https://img.shields.io/badge/version-0.1.2-orange)](#为什么是-r0env3)

换节点，环境跟着变。Linux 和 Windows 各自在自己的目录里。

## 先设端口

用你代理软件实际的 HTTP 或混合端口。同一台 Mac，不需要 SSH。

只对当前终端：

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh preview
```

保存到新终端。zsh 用户把这一行加进 `~/.zshrc`，再重新打开终端：

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
```

把 `1080` 换成你的端口。Clash 或 mihomo 保持开着。`apply` 只在改系统时区时要 sudo。

## 为什么是 r0env3

- 出口 IP 自动识别国家、时区、ASN
- 系统时区切到出口所在地
- 当前用户区域跟着出口国家走
- Firefox / Chromium 隔离浏览器，带 locale、时区、视口、UA
- 每 5 分钟自动巡检，偏差写进日志
- 每次应用前自动快照，随时恢复
- 命令仍是 `r0env`。其他版本互不影响

## 安装

1. 从 GitHub Release 下载 `r0env3-macos.zip`，或用 Code → Download ZIP，进入 macOS 源码目录。
2. 放到固定位置，例如 `~/Applications/r0env3`。
3. 看 Python。要 3.10+，推荐 3.12：

```bash
python3 --version
```

没有就去 [python.org/downloads/macos](https://www.python.org/downloads/macos/) 装 universal2，装完重新打开终端。

4. 打开代理，连上节点，然后：

```bash
cd "$HOME/Applications/r0env3"
export HTTPS_PROXY="http://127.0.0.1:1080"
export R0ENV_PROXY="http://127.0.0.1:1080"
bash install.sh
./r0env.sh help
```

虚拟环境、依赖、Firefox 和 Chromium，一次装齐。可选：

```bash
bash install.sh --skip-browsers
bash install.sh --with-timer
```

装好后不要移动项目目录。换位置就重新安装。

## 第一次使用

先预览，再应用，再开浏览器。

```bash
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh preview
```

看出口 IP、国家、时区和浏览器语言。然后：

```bash
./r0env.sh apply
```

sudo 密码输入时不显示，这是正常的。它会先存快照，再设系统时区和当前用户区域，然后读回核对。记下输出里的 `snapshot` 路径。

打开隔离浏览器：

```bash
./r0env.sh browser
```

用它弹出的窗口。代理和这个终端保持开着。

Chromium：

```bash
./r0env.sh cr
./r0env.sh browser
```

切回 Firefox：

```bash
./r0env.sh ff
./r0env.sh browser
```

切换前先关掉旧的隔离浏览器。这里的 Chromium 是工具下载的那个。

## 以后每天

同一地区、已经应用过：

```bash
cd "$HOME/Applications/r0env3"
export R0ENV_PROXY="http://127.0.0.1:1080"
./r0env.sh browser
```

换地区：关掉旧浏览器，再 `preview` → `apply` → `browser`。

## 命令

前面加 `./r0env.sh`，或用 `.venv/bin/r0env`。

| 命令 | 作用 |
| --- | --- |
| `preview`、`p` | 预览 |
| `apply`、`go` | 应用时区、区域并保存配置 |
| `ff`、`firefox` | 用 Firefox 应用 |
| `cr`、`chromium` | 用 Chromium 应用 |
| `browser` | 打开隔离浏览器 |
| `status`、`s` | 系统状态和出口 |
| `check`、`c` | 一致性检查 |
| `doctor` | 系统版本、架构、DNS、代理、浏览器路径 |
| `acceptance` | 浏览器报告 |
| `install`、`uninstall` | 添加或移除 LaunchAgent |
| `timer`、`log` | 任务状态、最近 30 条日志 |
| `restore FILE` | 恢复当前用户的快照 |

还有：`resolve --ip IP`、`init`、`inspect`、`plan --profile FILE`、`rollback --snapshot FILE`。

```bash
./r0env.sh preview --proxy http://127.0.0.1:1080
./r0env.sh preview --ip 8.8.8.8 --direct
./r0env.sh restore "$HOME/Library/Application Support/r0env3/snapshot-实际文件名.json"
```

`--direct` 走直连。换节点在 Clash / mihomo 里切，环境这边自动跟上。

## 你得到什么

| 能力 | macOS 实现 |
| --- | --- |
| 时区 | `systemsetup`，只有这一步要 sudo |
| 区域 | 当前用户 AppleLocale |
| 巡检 | 登录期间每 300 秒的 LaunchAgent |
| 日志 | `~/Library/Application Support/r0env3` |
| 启动器 | `./r0env.sh` |
| 浏览器 | 隔离 Playwright，配置由 `apply` 保存 |

每次 `apply` 保存快照和 `profile.json`，权限 600。改了端口，再跑一次 `./r0env.sh install`。

## 浏览器

`./r0env.sh browser` 用已保存配置打开隔离的 Playwright 实例。

| 引擎 | 配置 |
| --- | --- |
| Firefox | locale、时区、视口、UA、关闭 WebRTC、profile 里的 DoH |
| Chromium | 隔离 context、关闭非代理 UDP |

退出即结束临时会话。恢复主机用 `restore`。

## 验收路径

```bash
./r0env.sh status
./r0env.sh check
./r0env.sh acceptance
./r0env.sh acceptance --headless --output "$HOME/Desktop/r0env-report"
```

验收会打开隔离浏览器，访问 ipwho.is，读取语言、时区和 WebRTC。见 `MACOS_TEST.md`。

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
python3 package.py
```

## 遇到这些

| 看到 | 这样处理 |
| --- | --- |
| `python3: command not found` | 安装 Python，重新打开终端 |
| 找不到 `install.sh` | 先 `cd` 到包含它的目录 |
| `Permission denied` | 用 `bash r0env.sh help` |
| `Connection refused` | 开代理，核对端口。`127.0.0.1` 是这台 Mac |
| `all GeoIP sources failed` | 代理访问不到 ipwho.is |
| 浏览器文件不存在 | `.venv/bin/python -m playwright install firefox chromium` |
| 提示先运行 apply | 在同一账户下跑 `apply` |
| 时区被改回去 | 看系统设置里的自动时区 |
| LaunchAgent 注册失败 | 跑 `doctor`，再看 `timer` |
| sudo 被拒绝 | 用日常的管理员账户 |

```bash
./r0env.sh doctor
./r0env.sh log
```
