# r0env3 — macOS 预览版

按代理出口地区生成环境配置，调整系统时区与当前用户区域，并运行独立 Firefox/Chromium 浏览器。命令继续使用 r0env。Linux、Windows 版本不受此独立目录影响。

**状态：0.1.2 预览版。开发环境为 Linux；没有执行真实 Mac 的安装、系统设置、LaunchAgent 或浏览器验收。请勿宣传为已通过 macOS 实机验证或全机无泄漏。**

## 要求

- macOS 14 Sonoma 或更新版本（当前 Playwright 浏览器要求），Intel 或 Apple Silicon。实际兼容性需在对应 Mac 测试。
- Python 3.10+，推荐 Python 3.12；可从 python.org 安装适合 Mac 的版本。
- 可用的 HTTP/混合代理，例如 Clash/mihomo；本工具不提供节点。
- 修改系统时区需要管理员 sudo 权限。不要 sudo 运行整个安装脚本或 r0env。

## 1. 下载与准备

从 GitHub Release 下载 `r0env3-macos.zip` 并解压；如果使用仓库的 Code → Download ZIP，请进入其中的 macOS 源码目录。将文件夹放在固定位置，例如 `~/Applications/r0env3`。以下示例假设使用此路径；你的目录叫 `macos` 或在其他位置时，请替换路径。

在 Mac 打开“终端”（可按 Command + 空格，搜索 Terminal），执行：

```bash
python3 --version
```

需要 Python 3.10 或更新版本，推荐 3.12。没有安装时，前往 [Python 官方 macOS 下载页](https://www.python.org/downloads/macos/)，安装对应版本的 macOS universal2 installer，完成后重新打开终端检查。

打开自己的代理软件，连接节点，确认 **HTTP 或混合端口**。下面以 7890 为例；如果实际是 1080，把命令里的 7890 改成 1080。代理在同一台 Mac 上运行时不需要 SSH。

## 2. 安装（首次使用）

进入包含 `install.sh` 的目录：

```bash
cd "$HOME/Applications/r0env3"
```

设置当前终端使用的代理，然后安装：

```bash
export HTTPS_PROXY="http://127.0.0.1:7890"
export R0ENV_PROXY="http://127.0.0.1:7890"
bash install.sh
```

`HTTPS_PROXY` 用于下载依赖；`R0ENV_PROXY` 用于出口查询和浏览器代理选择。不需要代理下载依赖时，可省略 HTTPS_PROXY。

等待安装成功后执行：

```bash
./r0env.sh help
```

安装创建 `.venv`、安装 Python 依赖并下载 Firefox/Chromium。不自动修改系统时区、不添加全局 PATH、不覆盖其他版本的 r0env。安装后不要移动或删除项目目录；换位置后应重新创建虚拟环境安装。

可选安装方式：

```bash
bash install.sh --skip-browsers     # 暂不下载浏览器
bash install.sh --with-timer        # 同时安装定时巡检；默认不安装巡检
```

**不要执行 `sudo bash install.sh` 或 `sudo ./r0env.sh ...`。** 程序需要保持在日常登录账户下运行，只会在修改系统时区时单独请求 sudo。

## 3. 第一次使用：预览 → 应用 → 浏览器

### 第一步：预览，不修改系统

保持代理开启，在项目目录执行：

```bash
export R0ENV_PROXY="http://127.0.0.1:7890"
./r0env.sh preview
```

检查输出中的出口 IP、国家、时区和浏览器语言是否符合预期。如果查询失败，先看下面的常见问题，不要继续 apply。

`--ip 8.8.8.8` 仅用于指定地理查询目标，不会把真实出口变成 8.8.8.8。日常使用通常不需要指定 IP。

### 第二步：应用设置

```bash
./r0env.sh apply
```

需要时会出现 sudo 密码提示，输入当前 Mac 管理员账户的登录密码；输入时不显示字符是正常现象。

程序保存修改前的快照，设置系统时区和当前用户区域格式，随后读回核对。成功后保存浏览器配置。请记下输出中的 `snapshot` 路径。

- 当前用户区域通过 AppleLocale 设置，不等同 Windows 系统区域或 Linux LANG。
- 不更换 macOS 显示语言。已有应用可能需重启，部分区域变化可能需注销后登录。
- 自动时区可能覆盖手动设置；如果读回不一致，在系统设置的日期与时间中检查自动时区选项。
- `applied: false` 或出现 error 时，不能认为成功；可能已部分修改，请保留快照。失败不会覆盖之前保存的浏览器配置。

### 第三步：打开隔离浏览器

```bash
./r0env.sh browser
```

默认打开独立 Firefox。请在弹出的浏览器中使用网页，而不是自行打开的 Safari 或 Chrome。

保持代理软件和启动浏览器的终端开启。关闭浏览器会结束临时会话，**不会自动恢复系统时区和区域**。临时浏览器会话不用于长期保存登录状态。

选择 Chromium 时先执行下面两条（第一条也会应用主机设置）：

```bash
./r0env.sh cr
./r0env.sh browser
```

切回 Firefox：

```bash
./r0env.sh ff
./r0env.sh browser
```

请先关闭旧隔离浏览器，再切换配置。Chromium 是程序下载的浏览器，不是用户已有的 Google Chrome。

## 4. 以后每天怎么用

同一代理地区、配置已经应用过：

```bash
cd "$HOME/Applications/r0env3"
export R0ENV_PROXY="http://127.0.0.1:7890"
./r0env.sh browser
```

换到不同地区节点后：先关闭旧隔离浏览器，然后重新运行 `preview` → `apply` → `browser`。

`export` 只对当前终端及其子进程有效。希望新终端默认使用该端口时，使用 zsh 的用户可编辑自己的 `~/.zshrc`，加入一行：

```bash
export R0ENV_PROXY="http://127.0.0.1:7890"
```

保存后重新打开终端。使用其他 shell 时应修改对应配置文件。这个设置不会自动开启代理软件；更换代理端口后需要同步修改。若只运行 browser 且没有设置环境变量，它会使用 apply 保存的代理地址。

## 5. 命令速查

以下命令前面均加 `./r0env.sh`，也可使用 `.venv/bin/r0env`。没有自动安装全局 `r0env` 命令。

| 命令 | 作用 |
| --- | --- |
| 无参数、preview、p | 预览 |
| apply、go | 应用系统时区、用户区域并保存配置 |
| ff、firefox | 同 apply，选择 Firefox；不直接打开浏览器 |
| cr、chromium | 同 apply，选择 Chromium；不是修改已有 Chrome |
| browser | 打开隔离浏览器 |
| status、s | 当前系统状态与出口 |
| check、c | 系统时区和用户区域一致性检查 |
| doctor | 只读诊断 macOS 版本、架构、DNS、代理和浏览器安装位置 |
| acceptance | 验证隔离浏览器，输出报告 |
| install、uninstall | 安装/删除用户 LaunchAgent，非软件本体安装/删除 |
| timer、log | 巡检任务状态、最近 30 条日志 |
| restore FILE | 恢复同一用户的 macOS 设置快照 |
| resolve --ip IP | GeoIP 查询 |
| init [IP] | 预览兼容入口 |
| inspect | 读取主机状态 |
| plan --profile FILE | 读取 JSON/YAML 配置，生成预览 |
| rollback --snapshot FILE | restore 的别名，仅接受 macOS 快照 |

不保留 Linux/Windows 的未实现 legacy apply/monitor 占位接口；实际巡检由 install 管理。旧平台快照不可用于 Mac。没有全机紧急断网命令。

preview/apply/ff/cr 支持 `--ip`、`--proxy`、`--engine firefox|chromium`、`--output`。`--direct` 显式选择直连；其他命令通过 R0ENV_PROXY 设置代理。browser 默认使用保存的代理地址，环境变量可覆盖。命令行参数不支持缩写。

```bash
./r0env.sh preview --proxy http://127.0.0.1:1080
./r0env.sh preview --ip 8.8.8.8 --direct
./r0env.sh restore "$HOME/Library/Application Support/r0env3/snapshot-实际文件名.json"
```

指定 IP 的查询仍需访问 ipwho.is。该查询源不可用会失败，当前无备用源。代理连接被拒绝时先检查端口和代理是否启动，不要关闭证书验证。

## 6. 定时巡检与恢复

默认数据目录为 `~/Library/Application Support/r0env3`，可通过 `R0ENV_CONFIG_DIR` 设置。profile、快照、任务代理配置以权限 600 保存，可能包含代理凭据，不要上传 GitHub。

```bash
./r0env.sh install
./r0env.sh timer
./r0env.sh log
./r0env.sh uninstall
```

LaunchAgent 位于 `~/Library/LaunchAgents/io.r0env.macos.check.plist`，使用当前 Python 解释器和绝对路径，每 300 秒检查一次，仅在用户 GUI 登录期间运行；休眠期间不会按时执行。只检查不自动纠正。代理参数在安装任务时保存，改变端口/数据目录后需重新 install。系统可能要求允许后台项目；若 bootstrap 失败请运行 doctor 并检查任务状态。

restore 仅恢复系统时区和原用户 AppleLocale（原来不存在则删除该键），不覆盖整个偏好文件，不恢复 browser profile、不修改网络。应在应用时的同一用户下运行，过程中单独请求 sudo。检查 rolled_back 和读回 actual，失败不要视为恢复完成。

`bash uninstall.sh` 仅删除任务，保留源码、快照、浏览器缓存和系统设置。需要撤销主机设置时请先 restore，再自行删除程序目录。

## 7. 检查实际效果

查看主机状态和一致性：

```bash
./r0env.sh status
./r0env.sh check
```

check 只检查出口地区与主机时区、用户区域，不是完整防泄漏检测。

自动验收隔离浏览器：

```bash
./r0env.sh acceptance
./r0env.sh acceptance --headless --output "$HOME/Desktop/r0env-report"
```

验收使用与 browser 相同的保存配置/代理，真实启动隔离浏览器，访问 ipwho.is，读取 navigator.language、languages、Intl 时区和 RTCPeerConnection 是否存在，同时核对主机时区与区域。

Firefox 禁用 WebRTC；Chromium 仅配置禁用非代理 UDP 策略，不能用接口存在与否证明不泄漏。因此 Chromium 的 WebRTC 项为未验证。

报告明确保留未验证项：系统 DNS、IPv6、代理断开阻断、全机路由和用户原有浏览器。无检测失败也只给 partial，不能给“全机通过”。验收退出码：0 保留、1 检测不一致、2 执行错误、3 部分完成且仍有未验证项。check 返回 0 一致/1 不一致/2 错误；apply 返回 0 设置读回一致/1 部分失败/2 前置失败。

已有 Safari/Edge/Chrome/Firefox 不会自动被修改，WebKit 不等于 Safari，本版没有 Safari 自动化配置功能。Firefox 配置了 DoH，但没有据此声称系统 DNS 无泄漏。不会设置全机代理、TUN、PF 防火墙或断线阻断。

## 8. 常见问题

| 现象 | 处理方法 |
| --- | --- |
| `python3: command not found` | 安装 Python 并重新打开终端 |
| 找不到 install.sh 或 r0env.sh | 先 cd 到包含这些文件的项目目录 |
| `Permission denied` 无法执行脚本 | 使用 `bash r0env.sh help`；安装成功会为启动脚本添加执行权限 |
| `Connection refused` / 连接被拒绝 | 确认代理已运行，并核对 HTTP/混合端口；127.0.0.1 指当前 Mac |
| `all GeoIP sources failed` / 超时 | 当前 GeoIP 只有 ipwho.is 一个来源；检查代理能否访问它，换查询 IP 通常不能解决网站不可达 |
| 浏览器可执行文件不存在 | 执行 `.venv/bin/python -m playwright install firefox chromium`；需要下载代理时先 export HTTPS_PROXY |
| 提示先运行 apply | 当前用户还没有成功保存 profile；在同一账户下运行 apply |
| 时区被改回去 / applied 为 false | 核对系统自动时区、sudo 权限以及错误输出；不要只看计划字段 |
| `check` 不一致 | 看 expected 与 actual；若只是应用没有刷新区域，可重新打开应用或注销登录 |
| `acceptance` 输出 partial、退出码 3 | 已完成有限探测，但仍有未验证项目，不是全机无泄漏通过 |
| sudo 不允许或密码错误 | 请在拥有管理员权限的日常账户操作；不要改用 sudo 启动整个程序 |
| LaunchAgent 注册失败 | 在 GUI 登录的日常账户运行，检查 timer 和系统后台项目权限；出现回退失败时需人工检查 |

进一步排错：

```bash
./r0env.sh doctor
./r0env.sh log
```

诊断输出可能包含网络地址和用户名，分享前检查隐私。遇到 SSL 证书错误应修复证书或代理配置，不要通过禁用验证绕过。

## 9. 开发、打包与发布

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
python3 package.py
```

打包使用源码白名单，排除虚拟环境、缓存、profile、快照、报告和日志，生成父目录中的 ZIP 和 SHA256。单独仓库可使用附带的 `.github/workflows/macos.yml`；如果放在旧仓库 `macos/` 子目录，需将 workflow 调整到仓库根目录并设置工作目录。CI 文件存在不代表 CI 已运行。

详细手工验收见 [MACOS_TEST.md](MACOS_TEST.md)。建议标记 GitHub Pre-release，待真实 Mac 验证后再扩大支持声明。

参考：[Apple systemsetup](https://support.apple.com/en-bw/guide/remote-desktop/apd95406b8d/mac)、[Apple LaunchAgent](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)、[Playwright 系统要求](https://playwright.dev/python/docs/intro)。

## 0.1.1 复查记录

- 拒绝同时指定 --direct 和 --proxy，避免用户要求直连却仍走代理。
- apply 未全部成功时保留旧 profile，不覆盖原隔离浏览器配置。快照仍可用于恢复部分系统修改。
- restore 中途失败时报告已完成命令、错误和可能的部分修改，不输出恢复成功。
- 37 项自动化测试通过（Linux，系统调用模拟；包含本地 HTTP 代理实际请求）。没有真实 Mac 验收结论。

与 Windows 版的差异：核心出口/预览/系统区域/隔离浏览器/巡检/恢复入口已移植，但 AppleLocale 仅是用户区域偏好，不等同 Windows 系统区域或 Linux LANG。Mac 验收目前只覆盖隔离浏览器，未移植 Windows 已安装 Edge/Chrome/Firefox 页面回传、系统直连出口及 IPv4/IPv6 对比测试。旧 CLI 命令不保证参数完全兼容。自动化测试通过不能证明不同 Mac 版本上的 systemsetup、defaults、launchctl 已实测生效。

## 0.1.2 二次复查

- 配置、快照与任务文件改为权限 600 的临时文件写入后原子替换，失败保留旧文件。
- 更新 LaunchAgent 注册失败时恢复旧配置；此前正在运行的旧任务尝试重新注册。回退失败明确报错。
- macOS 40 项、Windows 66 项自动化测试通过；Linux 原版 6 项通过、1 项失败（BrowserAdapter.verify 返回值与测试要求不一致）。三者测试数量和范围不同，不代表完成度百分比。
- 以上均在 Linux 环境执行，Mac 系统命令使用模拟；未获得 Mac 实机证据。详细功能差异见 [COMPARISON.md](COMPARISON.md)。
