#!/bin/bash
set -u

PROJ=$(cd "$(dirname "$0")" && pwd)
USER=$(whoami)
UID_NUM=$(id -u)
PROXY=${R0ENV_PROXY:-http://127.0.0.1:7890}
PY=$PROJ/.venv/bin/python

echo "=== r0env 安装 ==="
echo "项目目录: $PROJ"
echo "用户名: $USER"
echo "UID: $UID_NUM"
echo "代理地址: $PROXY"
echo ""

echo "[0/6] 检查代理..."
if ! curl -s --max-time 5 -x "$PROXY" https://ipwho.is/ > /dev/null 2>&1; then
    echo "⚠️ 代理 $PROXY 不通。"
    read -p "   是否继续？(y/N) " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 1
fi

if [ -d "$PROJ/.venv" ]; then
    echo "[1/6] 虚拟环境已存在"
    read -p "   是否重建？(y/N) " ans
    if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
        rm -rf "$PROJ/.venv"
        python3 -m venv "$PROJ/.venv"
    fi
else
    echo "[1/6] 创建虚拟环境..."
    python3 -m venv "$PROJ/.venv"
fi

echo "[2/6] 安装依赖..."
"$PROJ/.venv/bin/pip" install -q -e "$PROJ" || { echo "❌ 失败"; exit 1; }

echo "[3/6] 写入全局命令..."
if [ -f /usr/local/bin/r0env ]; then
    sudo cp /usr/local/bin/r0env /usr/local/bin/r0env.bak.$(date +%s)
fi

TMPL=$(mktemp)
cat > "$TMPL" << 'TEMPLATE'
#!/bin/bash
PROJ=__PROJ__
PROXY=${R0ENV_PROXY-__PROXY__}
ENGINE=${R0ENV_ENGINE:-firefox}
PY=$PROJ/.venv/bin/python

if [ -n "$PROXY" ]; then
    export http_proxy=$PROXY
    export https_proxy=$PROXY
fi
export R0ENV_PROXY=$PROXY
export R0ENV_ENGINE=$ENGINE

case "$1" in
  apply|go) shift; $PY $PROJ/apply_auto.py --auto --execute "$@" ;;
  ff|firefox) $PY $PROJ/apply_auto.py --auto --execute --engine firefox ;;
  cr|chromium) $PY $PROJ/apply_auto.py --auto --execute --engine chromium ;;
  preview|p) shift; $PY $PROJ/apply_auto.py --auto "$@" ;;
  check|c) $PY $PROJ/check_consistency.py ;;
  status|s)
    echo "=== 出口 IP ==="
    $PY -c "
import json,urllib.request,os
p=os.environ.get('R0ENV_PROXY','')
if p:
    o=urllib.request.build_opener(urllib.request.ProxyHandler({'http':p,'https':p}))
else:
    o=urllib.request.build_opener()
try:
    d=json.loads(o.open('https://ipwho.is/',timeout=8).read())
    print(f\"{d['ip']} -> {d['country_code']} / {d.get('timezone','?')}\")
except Exception as e:
    print(f'检测失败: {e}')
"
    echo ""
    echo "=== 系统时区 ==="
    timedatectl | grep "Time zone" 2>/dev/null || echo "timedatectl 不可用"
    echo ""
    echo "=== 系统语言 ==="
    cat /etc/locale.conf 2>/dev/null || echo "无 locale.conf"
    echo ""
    echo "=== 当前引擎 ==="
    echo "R0ENV_ENGINE=$R0ENV_ENGINE"
    ;;
  log) journalctl -u r0env-check.service -n 30 --no-pager ;;
  timer) systemctl list-timers | grep r0env ;;
  install) bash $PROJ/install_timer.sh ;;
  help|--help|-h|"")
    cat << 'HELP'
r0env - 多地域环境自动化

用法:
  r0env          预览
  r0env apply    一键切换（Firefox）
  r0env ff       Firefox
  r0env cr       Chromium
  r0env status   看状态
  r0env check    一致性检查
  r0env log      巡检日志
  r0env timer    定时器状态
  r0env install  安装定时巡检

环境变量:
  R0ENV_PROXY   代理（空字符串 = 直连）
  R0ENV_ENGINE  引擎（firefox | chromium）
  R0ENV_PROJ    项目路径
HELP
    ;;
  *)
    if [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      $PY $PROJ/apply_auto.py --ip "$1" "${@:2}"
    else
      echo "未知命令: $1"; echo "试试: r0env help"
      exit 1
    fi
    ;;
esac
TEMPLATE

sed "s|__PROJ__|$PROJ|g" "$TMPL" | sudo tee /usr/local/bin/r0env > /dev/null
sudo chmod +x /usr/local/bin/r0env
rm -f "$TMPL"

echo "[4/6] 写入 systemd service..."
if [ -f /etc/systemd/system/r0env-check.service ]; then
    sudo cp /etc/systemd/system/r0env-check.service /etc/systemd/system/r0env-check.service.bak.$(date +%s)
fi

if command -v notify-send > /dev/null 2>&1; then
    NOTIFY_CMD='|| notify-send -u critical "r0env 环境不一致" "请检查代理"'
else
    NOTIFY_CMD=''
fi

sudo tee /etc/systemd/system/r0env-check.service > /dev/null << EOF
[Unit]
Description=r0env consistency check
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJ
Environment="http_proxy=$PROXY"
Environment="https_proxy=$PROXY"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$UID_NUM/bus"
ExecStart=/bin/bash -c '$PROJ/.venv/bin/python $PROJ/check_consistency.py $NOTIFY_CMD'
EOF

echo "[5/6] 写入 systemd timer..."
sudo tee /etc/systemd/system/r0env-check.timer > /dev/null << 'EOF'
[Unit]
Description=Run r0env every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Unit=r0env-check.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable r0env-check.timer > /dev/null 2>&1
sudo systemctl restart r0env-check.timer

echo "[6/6] 验证..."
sleep 2
systemctl is-active r0env-check.timer > /dev/null && echo "✓ timer 已激活" || echo "❌ timer 未激活"
echo ""
echo "=== 完成 ==="
echo "试试: r0env help"
echo "试试: r0env status"
echo "直连: R0ENV_PROXY=\"\" r0env status"
