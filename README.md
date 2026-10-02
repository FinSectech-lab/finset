### r0env：日常环境切换与一致性检查


r0env 的环境切换目标是根据代理出口 IP 匹配系统时区、语言区域（locale）和浏览器环境，让系统环境与当前节点所在国家保持一致。日常使用时，先在 Clash / mihomo 里切到目标国家节点，再执行预览，确认识别结果后再应用。

根据目标 IP，统一检查 IP、DNS、WebRTC、浏览器指纹、系统时区和语言，并提炼为“防封号 skill.md”，定时巡查系统各项设置和属性是否符合要求

#### 日常常用命令

预览：检测当前出口 IP，生成完整 profile，但不改系统。

```bash
r0env
```

一键切换：检测出口 IP → 切系统时区 → 切 locale → 生成浏览器指纹（默认 Firefox）。

```bash
r0env apply
```

看状态：显示当前出口 IP、系统时区、系统语言、当前浏览器引擎。

```bash
r0env status
```

#### 切换浏览器引擎

强制使用 Firefox 引擎执行切换（等同于默认 apply）。

```bash
r0env ff
```

#### 检查与定时巡检

一致性检查：对比出口 IP 的国家与系统时区 / locale 是否一致，输出 OK 或 FAIL。

```bash
r0env check
```

查看 systemd 自动巡检日志（最近 30 条）。

```bash
r0env log
```

查看 systemd timer 状态：下次触发、上次触发、是否激活。

```bash
r0env timer
```

安装 systemd 定时巡检（每 5 分钟自动运行一次 check）。

```bash
r0env install
```

查看所有命令用法。

```bash
r0env help
```

#### 指定 IP 预览

不想自动检测当前出口 IP 时，可以直接指定 IP 查询国家并生成 profile：

```bash
r0env 8.8.8.8
```

#### 完整流程示例

1. 在 Clash / mihomo 里切到目标国家节点。
2. 先预览，确认目标国家识别正确：

   ```bash
   r0env
   ```

3. 执行切换，应用系统环境配置：

   ```bash
   r0env apply
   ```

4. 查看状态并验证一致性：

   ```bash
   r0env status
   r0env check
   ```
