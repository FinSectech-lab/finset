# macOS 实机验收清单

当前未获得 Mac 设备，以下项目必须由真实用户/CI 验证；Linux mock 测试不替代系统验收。

1. 记录 `sw_vers`、`uname -m`、`python3 --version`。Intel/Apple Silicon 分开记录。
2. 在包含空格/中文的固定路径解压；以非 root 用户运行安装，记录依赖和浏览器版本。
3. 设置实际 HTTP 代理端口，preview 应成功且不修改时区/区域。直连不可达必须报错。
4. apply 前执行 `./r0env.sh inspect` 保存旧值；apply 输入 sudo 密码后检查快照、applied 和 actual。拒绝 sudo 时不应修改系统。
5. 用系统设置确认时区和区域；应用新进程/注销登录后核对。确认显示语言没有改变。
6. browser 启动 Firefox，打开 https://ipwho.is/，控制台执行：
   `JSON.stringify({language:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,webrtc:typeof RTCPeerConnection})`。
7. acceptance 应生成报告，失败不能被吞掉，缺少浏览器也必须保存错误报告；所有测量通过仍然是 partial。
8. install 后 timer 可查，五分钟后 log 有新记录；uninstall 后任务停止。重新登录确认任务生效；检查后台项目授权。
9. restore 应恢复旧时区和区域，原本不存在 AppleLocale 时应删除该键。另一个用户或错误平台快照必须被拒绝。检查浏览器配置没有被误称恢复。
10. Chromium 单独安装启动并记录；不能因为没有观察到 ICE 就认为无泄漏。
11. 完整防泄漏（DNS/IPv6/TUN/断线阻断）仍未实现，不在通过范围内。

自动化覆盖：预览无副作用、非法输入、sudo 拒绝、部分失败保存快照、读回不一致不报成功、用户身份校验、恢复缺失键、LaunchAgent 路径和注册失败、浏览器代理优先级、检查/验收不一致、CLI 参数严格解析、本地 HTTP 代理集成测试。
