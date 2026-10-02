---
name: r0env-multi-region-automation
description: 在已授权的主机、容器或虚拟机中，根据目标 IP 生成并应用多地域网络与浏览器测试 profile，随后执行周期巡检、自动纠正或告警。
---

# r0env 多地域网络环境测试与浏览器自动化管理

## 目标

输入一个目标 IP，工具必须完成：

1. 查询该 IP 的国家/地区、行政区、城市、ASN/ISP、时区和语言候选。
2. 根据批准的地区 profile，为本机或指定容器/虚拟机生成一致性配置计划。
3. 按权限执行出口代理、DNS、WebRTC、浏览器上下文和操作系统区域设置切换。
4. 通过定时巡检判断实际状态是否仍符合 profile；可配置为自动纠正或仅告警。
5. 每次变更都可审计、可验证、可回滚。

只允许用于自有或明确授权的测试环境。代理和地区设置用于区域兼容性、隐私泄漏和自动化测试，不得用于绕过访问控制、规避风控或伪造未授权身份。

## 总体架构

```text
CLI/API
  -> Target Manager（本机/Docker/Kubernetes/VM）
  -> IP Resolver（GeoIP、ASN、时区、语言）
  -> Profile Engine（地区 profile + 差异计划）
  -> Adapters
       Egress/Proxy
       DNS
       WebRTC
       Browser/Playwright
       OS Locale
  -> Verify -> Scheduler -> Audit/Alert
```

核心状态流：`resolve -> plan -> snapshot -> apply -> verify -> monitor -> rollback`。

每个适配器必须实现：

```python
class Adapter(Protocol):
    def discover(self, target) -> ObservedState: ...
    def plan(self, observed, desired) -> Diff: ...
    def snapshot(self, target) -> Snapshot: ...
    def apply(self, diff, target) -> ApplyResult: ...
    def verify(self, desired, target) -> VerificationResult: ...
    def rollback(self, snapshot, target) -> RollbackResult: ...
```

## 目录设计

```text
r0env/
  cli.py                 # resolve/plan/apply/check/rollback/inspect
  models.py              # Pydantic schema
  resolver.py            # GeoIP、ASN、时区、语言
  profiles.py            # YAML profile 加载、继承、签名校验
  state.py               # 快照、幂等状态、锁
  scheduler.py           # systemd/cron/APScheduler 调度
  audit.py               # JSON、SQLite、Prometheus、告警
  adapters/
    egress.py            # 代理、路由、kill-switch、出口验证
    dns.py               # systemd-resolved、NetworkManager、容器 DNS
    webrtc.py            # Chromium 策略、ICE 候选验证
    browser.py           # Playwright context/profile
    os_locale.py         # TZ、locale、键盘布局
    docker.py            # Docker exec/env/network
    kubernetes.py        # Pod/ConfigMap/Secret/Job
    vm.py                # SSH/WinRM/guest-agent
```

## 依赖选择

- Python 3.12+、`pydantic-settings`、`ruamel.yaml`、`typer`、`structlog`。
- GeoIP：MaxMind GeoIP2/GeoLite2 本地数据库；第二来源仅用于交叉验证。
- 网络：`httpx`、`dnspython`；出口检测从目标容器/VM 内发起。
- 浏览器：Playwright Python，固定 Chromium 版本；使用独立临时用户目录。
- 运行时：Docker SDK、官方 Kubernetes Python client；主机设置通过 NetworkManager/systemd-resolved 或平台 API。
- 巡检：systemd timer/Cron；多实例使用 APScheduler 或 Kubernetes CronJob。
- 质量：pytest、respx/pytest-httpx、mypy、ruff、pip-audit、SBOM。

## 命令接口

```bash
r0env resolve --ip 8.8.8.8
r0env plan --target host --profile profiles/us-ca.yaml
r0env apply --target container:browser --profile profiles/us-ca.yaml --confirm CASE-123
r0env inspect --target container:browser
r0env check --target container:browser --profile profiles/us-ca.yaml
r0env rollback --target container:browser --snapshot latest
r0env monitor --config config.yaml
```

`plan` 必须无副作用；`apply` 必须先生成快照；出口、DNS、系统设置等高影响操作需要显式确认；验证失败时自动回滚或进入告警状态。

## 配置项清单

```yaml
api_version: v1
case_id: CASE-123
target:
  type: container            # host | container | vm
  id: browser-test
authorization:
  operator: team@example.com
  allowed_targets: [container:browser-test]
resolution:
  target_ip: 8.8.8.8
  sources: [maxmind-local, secondary-api]
  min_confidence: 0.85
  on_conflict: require_approval
region:
  country: US
  subdivision: CA
  timezone: America/Los_Angeles
  locale: en_US.UTF-8
  languages: [en-US, en]
network:
  egress:
    mode: socks5
    endpoint: secret://proxy/us-ca
    username: secret://proxy/user
    password: secret://proxy/password
    expected_asn: [ASXXXX]
    ipv6: block_or_proxy
    kill_switch: true
  dns:
    mode: doh                    # system | udp | dot | doh
    servers: [https://dns.example/dns-query]
    fallback: deny
browser:
  engine: chromium
  version: pinned
  user_agent: profile-value
  locale: en-US
  timezone_id: America/Los_Angeles
  viewport: {width: 1365, height: 768, device_scale_factor: 1}
  languages: [en-US, en]
  webrtc:
    ip_handling: proxy_only
    allow_udp: false
    stun_servers: []
  canvas_webgl:
    mode: deterministic-test-profile
    hardware_acceleration: false
os:
  timezone: America/Los_Angeles
  locale: en_US.UTF-8
  keyboard_layout: us
inspection:
  interval_seconds: 300
  timeout_seconds: 20
  auto_correct: [dns, browser_context]
  alert_only: [egress, webrtc, os_locale]
  consecutive_failures: 2
  probes: [egress, dns, webrtc, browser, os]
rollback:
  snapshot_before_apply: true
  max_duration_seconds: 120
audit:
  sink: sqlite:///var/lib/r0env/audit.db
  retain_days: 30
```

凭据只能通过 Secret Manager 或受限环境变量注入，不能写入 YAML、命令行或日志。

## 关键实现步骤

### 1. IP 地区识别

校验 IPv4/IPv6、拒绝私网和保留地址的自动切换；记录来源、数据库版本、置信度、ASN、时区、时间戳和原始响应摘要。多个来源冲突时停止自动 apply。

### 2. 出口 IP / 代理

代理适配器只接受 profile 中声明的 HTTP(S)/SOCKS5 端点。切换前保存原代理和路由，启用 kill-switch，分别从目标环境验证 IPv4、IPv6、ASN 和 HTTPS 连通性；代理失效时阻断流量或告警。

### 3. DNS

为主机、容器和 VM 分别实现 systemd-resolved、NetworkManager、Docker DNS 和 guest-agent 适配。验证实际查询服务器、DoH/DoT 证书、回退路径和泄漏；`fallback: deny` 时解析失败必须阻断而不是使用运营商 DNS。

### 4. WebRTC

Chromium 通过受支持的 IP handling policy、代理和权限配置限制真实地址暴露；巡检页面必须收集 host、srflx、relay ICE candidates。出现未授权地址时失败并告警。浏览器版本差异必须记录，不能假设所有引擎参数一致。

### 5. 浏览器 profile

Playwright 创建隔离 context，设置 UA、语言、`timezone_id`、视口、DPR、颜色方案和权限。Canvas/WebGL 使用固定、可复现的测试 profile 或关闭硬件加速，不使用随机噪声伪造身份。验证浏览器参数与系统 profile 内部一致。

### 6. 操作系统时区与语言

容器优先通过 `TZ`、locale 包和启动环境设置；VM/主机通过平台 API 设置。每次修改保存原值，限制作用域，避免重启无关服务。设置完成后读取系统实际值验证，而非只检查配置文件。

### 7. 定时巡检

巡检按 `inspection.interval_seconds` 运行：采集实际状态，规范化时区/语言/IP，逐字段比较 `match/mismatch/unknown`。允许自动纠正的字段执行后必须重新验证；高影响字段默认只告警。连续失败达到阈值时熔断、退避并生成事件。

## 验收标准

- 输入目标 IP 能得到国家/地区、时区、ASN 和置信度。
- `plan` 能列出代理、DNS、WebRTC、浏览器和 OS 的字段级差异。
- `apply` 对本机、指定容器或 VM 执行 profile 切换，并保存快照。
- 目标环境内的出口 IP、DNS、ICE candidates、UA、语言、时区、分辨率、Canvas/WebGL 和 OS locale 均可验证。
- 定时巡检能自动纠正允许字段，对高影响差异告警，并在连续失败时停止修复。
- 任一阶段失败可回滚；所有变更、验证、告警和回滚均进入审计记录。
- 依赖锁定、最小权限、密钥隔离、IPv6 泄漏检测和供应链扫描纳入 CI。
