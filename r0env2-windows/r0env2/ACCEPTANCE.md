# Windows 一键实机验收

此脚本是“全机调整并验证”工作的实测入口，**不是已经完成全机防泄漏的一键修复器**。它读取本机实际状态并进行网络探测，不自动修改网络、关闭浏览器或停止代理。

## 运行

1. 将新版 ZIP 解压到 Windows 固定目录；尚未安装时先执行 `install.cmd`。只做本次验收可执行 `install.cmd -SkipBrowsers -SkipTimer`，无需下载 Playwright 浏览器。
2. 在 Clash/mihomo 中选好目标节点，开启 TUN。验收时保持节点不变。
3. 默认 HTTP/mixed 端口为 7890；如果你的端口不同，在 PowerShell 中设置，例如 `$env:R0ENV_PROXY='http://127.0.0.1:7897'`。
4. 执行 ` .\acceptance.cmd `。它会打开发现的 Edge、Chrome、Firefox 中的测试页面。不要关闭这些页面；浏览器若提示选择用户配置，选择你平时使用的那个。每个安装路径只测试一个会话，不遍历所有账户或便携版。
5. 等待约 1–3 分钟。报告在 `acceptance-results\时间戳\report.txt` 和 `report.json`。
6. 提供这两个报告供下一步适配分析。报告含公网/局域网 IP、网卡、浏览器路径等环境信息，不包含浏览器密码、历史记录、Cookie 或代理密码；分享前可查看内容。

如果不方便双击：`r0env acceptance --output .\acceptance-results --timeout 120`。

若没有已保存的 profile，语言/时区目标比较会显示未验证。已有的 `r0env apply` 可以生成 profile，但它仍只修改时区/区域，不能据此认为全机网络已完成配置。

## 实际测量范围

- Windows 版本、系统时区、用户区域和系统 locale 的实际读取值。
- 网卡、默认路由和 DNS 服务器配置（仅作为环境证据，不用配置推断无泄漏）。
- 通过显式 HTTP 代理访问 ipify 得到 IPv4/IPv6 基准。
- `curl.exe` 禁用 curl 配置和应用代理，发起 IPv4/IPv6 请求，验证这两次系统网络请求是否经 TUN 到达相同出口。
- 实际安装的浏览器打开本机页面，使用该浏览器会话的真实 navigator/Intl 值、HTTP 网络栈和 RTCPeerConnection。没有启动临时 profile，也没有覆盖时区/语言/代理让测试“通过”。
- 浏览器 IP 请求访问 ipify；STUN 请求访问 Cloudflare。页面结果通过带随机令牌的回环 HTTP 地址回传本机，不发送到项目作者服务器。

## 结果解释

- `pass`：仅该项本次测量符合预期，不代表全部应用、协议、配置均安全。
- `fail`：发现不一致或可能绕行。不同出口也可能来自节点多出口，需核实，不直接把所有不同地址认定为 ISP 泄漏。
- `unverified`：证据不足。超时、服务不可达、CORS/插件拦截、IPv6 请求失败、空 ICE 结果均不算通过。

退出码：0=所有列出的项目通过；1=存在失败项；2=没有失败但仍有未验证项，或执行不完整。

**本版本总体结论不会是“全部无泄漏”**：以下项目必须保留未验证，直至补足实机证据：

- DNS 泄漏：需要权威 DNS 观察端或物理网卡抓包；仅列出 DNS 服务器或看到 TUN 已打开不够。
- 代理断连阻断：需要受控停止代理后测试是否能直连；此脚本不会自动打断你的网络。
- 所有程序和浏览器配置的覆盖：有限目标地址和单个浏览器会话不可能证明全部覆盖。

当前还没有给日常 Edge/Chrome/Firefox 写入强制策略，也没有自动调整 mihomo 配置。收到 Windows 报告后才能针对真实安装和网络环境继续接入，并进行前后对比；不要把本验收脚本当成这些功能已完成。

来源：[ipify IPv4/IPv6 API](https://www.ipify.org/)、[Cloudflare STUN](https://developers.cloudflare.com/realtime/turn/)、[mihomo TUN](https://wiki.metacubex.one/config/inbound/tun/)。
