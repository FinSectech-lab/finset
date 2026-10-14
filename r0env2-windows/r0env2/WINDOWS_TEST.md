# Windows 实机验收

尚未在真实 Windows 主机执行以下检查。

1. 在含空格和中文的路径运行 install.cmd；新开终端检查 r0env/r0env2 help。
2. 在代理软件选择节点，运行 preview；确认 Windows 时区映射正确，预览前后系统设置不变。
3. 普通终端运行 apply，确认报告管理员权限不足且不修改系统。
4. 同一用户的管理员终端运行 apply，检查 snapshot/profile 文件和 PowerShell Get-TimeZone、Get-Culture、Get-WinSystemLocale 的结果；按需重启后 check 应返回 0。
5. 手动改变时区，check 应返回 1；停止代理，check 应返回 2 并有错误日志。
6. ff/cr 后运行 browser，在隔离窗口确认 navigator.language、Intl.DateTimeFormat().resolvedOptions().timeZone、视口和代理出口。用实际 ICE/DNS 测试验证网络属性，不能仅凭配置视为无泄漏。
7. install 后查看 timer；等待至少 7 分钟，log 应有新的检查记录。再次 install 不应创建重复任务；注销再登录后检查任务继续运行。
8. restore 指定的快照，确认原时区/用户区域/系统 locale 恢复；需要时重启。
9. uninstall.ps1 后检查任务和 PATH 项已移除，日志/快照仍保留。
