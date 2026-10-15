# 三版实际能力对比（2026-10-15）

范围：本地 r0env（Linux）、r0env2（Windows）、r0env3（macOS）源码；非发行历史和机器全局配置审计。

| 项目 | Linux 原版 | Windows | macOS 0.1.2 |
| --- | --- | --- | --- |
| 出口/GeoIP/地区配置 | 有 | 有，用户实测 | 有，待 Mac 实测 |
| 时区/区域 | timedatectl、LANG | Windows 时区、用户 culture、系统 locale，用户实测 | systemsetup、用户 AppleLocale，写后读回，待实测 |
| 实际隔离浏览器启动 | 适配器主要生成计划，无对应 browser 启动入口 | Firefox/Chromium；Firefox 用户实测 | Firefox/Chromium；待 Mac 实测 |
| 巡检 | systemd；notify-send 可选 | 用户计划任务 | 用户 LaunchAgent；不自动修复/弹窗 |
| 恢复 | CLI 占位 | Windows 设置快照，待实测 | 用户身份检查、缺失键恢复、部分失败报告；待实测 |
| 验收 | 主要检查时区/LANG | 已安装浏览器页面采集及系统/代理 IPv4/IPv6 探测，仍有未验证项 | 隔离浏览器和主机区域检查，范围较窄 |
| 已有浏览器自动配置 | 无完整实现 | 无 | 无（包括 Safari） |
| 全机接管/系统 DNS/IPv6/断线保护 | 无完整闭环 | 无完整闭环 | 无完整闭环 |

macOS AppleLocale 是当前用户区域偏好，不是 Windows 系统区域或 Linux LANG 的完全等价物。macOS 不修改显示语言或所有用户设置。三版均依赖用户已有代理，GeoIP 单源仍可能超时。

测试：Linux 6 passed / 1 failed（verify 没有 ok 字段）；Windows 66 passed；macOS 40 passed。Linux、Windows 源码未修改。Mac 安装/浏览器/系统操作/LaunchAgent/恢复没有实机验收。现阶段不能宣称跨平台效果完全一致。

第二次复查修复：原子保存配置；任务更新失败恢复旧文件与先前加载任务。旧任务回退也可能失败，此时报告错误要求用户检查，不虚报成功。
