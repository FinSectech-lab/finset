[English](README.en.md) | 简体中文
### r0env：日常环境切换与一致性检查


r0env 的环境切换目标是根据代理出口 IP 匹配系统时区、语言区域（locale）和浏览器环境，让系统环境与当前节点所在国家保持一致。日常使用时，先在 Clash / mihomo 里切到目标国家节点，再执行预览，确认识别结果后再应用。

根据目标 IP，统一检查 IP、DNS、WebRTC、浏览器指纹、系统时区和语言，并提炼为“防封号 skill.md”，定时巡查系统各项设置和属性是否符合要求

## 功能

- IP 到国家：检测出口 IP，解析国家、时区和 ASN
- 系统时区：立即生效
- 系统语言：按国家映射（CN / US / JP / KR 等）
- 浏览器指纹：支持 Firefox 和 Chromium
- WebRTC：Chromium 启动参数
- DNS：DoH / DoT / UDP / 系统，失败可拒绝回退
- 定时检查：systemd timer 每 5 分钟核对一次
- 桌面通知：环境不一致时提醒
- 两种模式：代理 / 直连，可切换

## 环境要求

- Linux（推荐 Arch / Omarchy）
- Python 3.12+
- 已在运行的代理（Clash / mihomo / sing-box / v2ray）
- sudo 权限

## 安装

第 1 步：解压

```bash
mkdir -p ~/Projects
unzip r0env-*.zip -d ~/Projects/r0env
cd ~/Projects/r0env
```

第 2 步：一键安装

```bash
bash install.sh
```

第 3 步：代理端口不是 7890 时

```bash
export R0ENV_PROXY=http://127.0.0.1:你的端口
echo 'export R0ENV_PROXY=http://127.0.0.1:你的端口' >> ~/.bashrc
source ~/.bashrc
```

## 用法

只预览当前出口，不改系统：

```bash
r0env
```

一键切换，默认 Firefox：

```bash
r0env apply
```

改用 Chromium：

```bash
r0env cr
```

看状态：

```bash
r0env status
```

一致性检查：

```bash
r0env check
```

看日志：

```bash
r0env log
```

看定时器：

```bash
r0env timer
```

帮助：

```bash
r0env help
```



## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `R0ENV_PROXY` | `http://127.0.0.1:7890` | 代理地址。空字符串表示直连 |
| `R0ENV_ENGINE` | `firefox` | 浏览器引擎，`firefox` 或 `chromium` |
| `R0ENV_PROJ` | 脚本所在目录 | 项目路径 |

## 直连

不用代理、按本机真实 IP 匹配时：

```bash
R0ENV_PROXY="" r0env apply
```

## 定时检查

安装时会自动加上 systemd timer，每 5 分钟对比出口国家和系统时区、语言是否一致。

```bash
r0env log
r0env timer
```

## 注意

- `r0env apply` 会改系统时区和语言，需要 sudo
- 已经打开的终端和程序要重启，才会用上新的语言设置
- 代理端口不是 7890 时，先设置 `R0ENV_PROXY`
- 这只同步本机环境，不能保证账号不被风控
