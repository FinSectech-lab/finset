# r0env2：r0env 的 Windows 版本

> v0.2.0 预览版：用于环境一致性配置，不是全机流量接管或零泄漏工具。建议以 GitHub Pre-release 发布。

适用于 Windows 10/11、Windows PowerShell 5.1、Python 3.10+。源项目位于相邻的 `r0env` 目录，本目录是独立的 Windows 版本。保留出口 IP 查询、profile 预览、时区/区域切换、浏览器配置、一致性检查、定时巡检、日志和原 Python CLI。

## Windows 实机验收

新增 `acceptance.cmd`：打开实际安装的 Edge/Chrome/Firefox，测量系统/浏览器出口、语言、时区和 WebRTC，并生成报告。详细步骤和未验证范围见 [ACCEPTANCE.md](ACCEPTANCE.md)。该脚本是实测入口，不代表全机一键调整已完成。

## 安装

1. 将整个 `r0env2` 文件夹复制到 Windows 的固定位置，例如 `C:\Tools\r0env2`。路径允许空格和中文。
2. 安装 Python 3.10 或更高版本（包含 Python Launcher；本轮实测 Python 3.12 x64），并安装 [微软 Visual C++ x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)。缺少 `msvcp140_1.dll` 会导致浏览器无法启动；已有运行库可选择修复。
3. 在该目录的 PowerShell 中运行 ` .\install.cmd `。安装会创建 Windows 虚拟环境、安装依赖及 Firefox/Chromium、添加当前用户 PATH，并创建每 5 分钟巡检的计划任务。
4. 新开终端运行 `r0env help` 或 `r0env2 help`。若 PATH 中存在旧版同名程序，可用完整路径 `C:\Tools\r0env2\r0env.cmd`。

只安装主机检查、不下载浏览器或不注册任务：

```powershell
.\install.cmd -SkipBrowsers -SkipTimer
```

不要复制 Linux 的 `.venv`。首次安装需要联网下载 Python 包和 Playwright 浏览器。pip/浏览器下载如需代理，先设置 `$env:HTTPS_PROXY = 'http://127.0.0.1:7890'`。

## 使用

```powershell
r0env                          # 预览，绝不修改系统
r0env 8.8.8.8                  # 指定 IPv4/IPv6 预览
r0env preview --output plan.json
r0env apply                    # 自动获取出口并应用；需管理员终端
r0env apply --ip 8.8.8.8        # 指定目标 IP 应用
r0env ff                       # Firefox 配置
r0env cr                       # Chromium 配置
r0env browser                  # 打开隔离浏览器，读取 apply 保存的配置
r0env status
r0env check
r0env log
r0env timer
r0env install                  # 安装/更新当前用户巡检任务
r0env uninstall                # 只移除巡检任务
r0env restore 'C:\path\snapshot-....json'  # 恢复主机设置，管理员终端
```

别名保留：`p`、`go`、`firefox`、`chromium`、`s`、`c`。

默认使用本机 Clash/mihomo HTTP 代理 `http://127.0.0.1:7890`，默认浏览器为 Firefox：

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:7890'
$env:R0ENV_ENGINE = 'chromium'
r0env preview
r0env preview --direct         # 本次直连，明确忽略系统/环境中的其他代理
r0env check --direct
r0env install --direct         # 定时巡检也使用直连
```

`--direct` 可用于所有日常命令。Python 调用时，`R0ENV_PROXY` 空字符串也表示直连；Windows PowerShell 5.1 可能删除空环境变量，建议用 `--direct`。

IP 查询使用 HTTP/HTTPS 代理；SOCKS 地址可通过 Clash/mihomo mixed 端口提供 HTTP 接入。切换代理节点由用户在代理软件中完成。

## Windows 行为与原版对应

| 原版 | Windows 版 |
| --- | --- |
| `timedatectl set-timezone` | IANA→Windows ID 映射，`Set-TimeZone` |
| `/etc/locale.conf`、`locale-gen` | `Set-Culture`、`Set-WinSystemLocale` |
| systemd 每 5 分钟检查 | 当前用户交互登录的 Windows 计划任务 |
| journalctl / 固定 Linux 日志路径 | `%LOCALAPPDATA%\r0env2\check_consistency.log`，`log` 查看最近 30 条 |
| shell 全局启动器 | `r0env.cmd`、`r0env2.cmd` 和 Python console scripts |
| nftables 紧急阻断函数 | 同名 Windows 防火墙出站阻断规则，默认不执行 |

修改系统设置需使用**同一个 Windows 用户**的管理员终端，避免将另一个管理员账号的区域设置改掉。修改系统 locale 后可能需要重启；用户区域设置在新进程中生效。工具不自动重启、不修改 Windows 显示语言、不安装语言包。Windows 自动时区服务可能覆盖手动选择，巡检会报告偏差。

浏览器默认沿用 apply 保存的代理地址；显式设置 `R0ENV_PROXY` 或执行 `browser --direct` 可覆盖。`status` 即使出口查询失败也会显示可读取的系统设置，并显示已保存的浏览器引擎。

每次 apply 在修改前保存独立 `snapshot-*.json`，并保存 `profile.json`。`R0ENV_CONFIG_DIR` 可覆盖数据目录。计划任务记录安装时的代理地址；修改代理地址/数据目录后重新执行 `r0env install`。任务在当前用户登录期间运行，不保存密码、不以 SYSTEM 身份检查另一个用户的 locale。检查失败可在 `r0env log` 和 `r0env timer` 中查看，不弹通知。

`check` 返回码：0=一致，1=不一致，2=查询/系统错误。`apply` 返回码：0=主机设置已执行，1=部分失败，2=前置检查/其他错误。系统 locale 未重启生效前可能检查不通过。

## 浏览器、DNS 和 WebRTC 的实际范围

原项目的 Browser/WebRTC apply 只返回数据，DNS 执行没有 runner。此版本保留计划生成，明确返回 dry-run，不把生成配置当成已经修改浏览器。`apply` 的实际主机修改是时区/区域；`r0env browser` 才把已保存配置传入独立 Playwright 实例。

Firefox 使用 locale、timezone、视口、UA 配置，关闭 WebRTC，并配置 profile 中的 DoH；Chromium 使用隔离 context 和禁用非代理 UDP 策略，DNS 由代理/系统处理。退出浏览器后临时会话被丢弃。系统 DNS、已有浏览器和代理软件的设置不会被此命令修改；`check` 仅核对出口国家、时区和 locale，不代表 DNS/WebRTC 泄漏检测已通过。原来的 DNS/ICE 分析函数仍保留供 Python 调用。

国家 locale 映射与原版一致（US/GB/JP/CN/DE/FR/KR/SG/HK/TW/AU/CA），其余回退 en-US；GeoIP 精度取决于提供商。

原 Python CLI 的 `init / resolve / plan / inspect / rollback / monitor` 保留。原 `apply --target ... --profile ... --confirm ...` 与 `check --target ...` 也可使用。使用 `r0env legacy ...` 可无歧义调用原接口；其中原配置 apply/rollback 仍是未接入运行时的占位接口。真实主机恢复请使用 `restore`。

## 验证及卸载

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\python.exe -m pytest -q
.\package.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1
```

卸载脚本移除任务和用户 PATH 项，保留项目、日志、快照和系统设置。恢复系统设置需先执行 `restore`。

迁移在 Linux 上完成；66 项自动化测试已通过，Windows 系统调用在测试中使用模拟，不能替代实机验收。用户在 Windows 10 22H2 x64 VMware 虚拟机、Python 3.12 环境反馈验证了代理出口查询、系统时区、当前用户区域格式、重启后的系统区域，以及隔离 Firefox 的出口、语言、时区和 WebRTC 接口禁用。Windows 11、Chromium、计划任务、恢复流程和完整验收脚本尚未完成本轮实机验证；DNS/IPv6/断线保护不作无泄漏承诺。参见 `WINDOWS_TEST.md`。

实现参考：[Set-WinSystemLocale](https://learn.microsoft.com/en-us/powershell/module/international/set-winsystemlocale)、[Set-Culture](https://learn.microsoft.com/en-us/powershell/module/international/set-culture)、[计划任务触发器](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasktrigger)、[tzlocal 时区映射](https://github.com/regebro/tzlocal)。

## 代理端口与常见问题

普通用户在自己的 Windows 上运行代理即可，不需要 SSH。请使用代理软件实际的 HTTP/混合端口；默认 7890 不一定适用。

PowerShell 当前窗口设置：

```powershell
$env:R0ENV_PROXY = 'http://127.0.0.1:7890'
.\r0env.cmd preview
```

CMD 当前窗口设置：

```cmd
set R0ENV_PROXY=http://127.0.0.1:7890
r0env.cmd preview
```

永久保存到当前用户（新终端生效，不需要管理员）：

```cmd
setx R0ENV_PROXY "http://127.0.0.1:7890"
```

- `WinError 10061`：检查代理是否启动、端口是否正确。
- `all GeoIP sources failed`：当前默认仅使用 ipwho.is；查询站点不可达时会失败，试用可用的 HTTP 代理。指定 `--ip` 不会改变真实出口 IP。
- 下载完成但缺少 `msvcp140_1.dll`：安装或修复上述 x64 运行库，再启动浏览器。
- 系统区域仍是旧值：按输出提示重启后用 `(Get-WinSystemLocale).Name` 核对。
- `ff`/`cr` 会应用系统设置并保存配置，不会直接打开浏览器；使用 `browser` 打开。
- 配置按用户保存；请在同一账户下运行 apply 和 browser。关闭浏览器不会恢复系统设置。
- 若采用虚拟机加 SSH 代理转发，重启会断开转发，需重建隧道。虚拟机的 127.0.0.1 指向虚拟机自身。
