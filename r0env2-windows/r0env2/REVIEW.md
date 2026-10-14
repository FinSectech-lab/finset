# Windows 迁移复查（2026-10-13）

已修复：

- argparse 允许参数缩写，preview --exec 可能进入执行模式；关闭缩写并补回归测试。
- --auto 与 --ip 同时传入时静默忽略指定 IP；改为拒绝冲突参数。
- apply 选择的代理/直连状态没有传递到后续浏览器进程；保存至 profile，浏览器使用保存值，允许环境变量和 --direct 覆盖。
- 浏览器直连明确关闭 Firefox/Chromium 系统代理继承。
- PowerShell 5.1 调用 Python -c 的嵌套引号风险；版本检查改为无需嵌套字符串。
- status 网络失败时不显示主机信息，且总显示默认引擎；分别查询，并读取已保存引擎。
- install 等命令静默忽略未知参数；改为报错，不执行操作。
- 兼容原 Python CLI 的 --profile=FILE 写法。
- 相对配置目录用于计划任务时可能指向错误位置；生成绝对路径。
- 主机命令超时或启动失败后未返回部分执行信息；保留错误、执行状态和恢复快照路径。

验证：47 项 pytest 测试通过，pip check 无依赖冲突，Python 编译检查通过；压缩包逐文件比对并校验 CRC。

限制：本轮在 Linux 上完成，未执行真实 Windows PowerShell、修改 Windows 设置、注册 Windows 计划任务或启动 Windows 浏览器；Windows CI 尚未运行。因此不能认定已经通过 Windows 实机验收。原版 DNS/WebRTC/浏览器的占位功能与 Windows 实际范围详见 README.md。

浏览器代理参数参考：https://playwright.dev/python/docs/api/class-browsertype
