#!/bin/bash
cd "$(dirname "$0")"
OUT="r0env-$(date +%Y%m%d).zip"
rm -f "$OUT"
zip -r "$OUT" . \
  -x ".venv/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*.log" \
  -x "*.json" \
  -x "r0env.egg-info/*" \
  -x ".git/*" \
  -x ".pytest_cache/*" \
  -x "r0env-*/" \
  -x "r0env-*/*" \
  -x "skills/防封号/*" \
  -x "r0env-cli.py" \
  -x "$OUT"
echo "✓ 已打包: $OUT"
echo ""
echo "=== 包内容 ==="
unzip -l "$OUT"
