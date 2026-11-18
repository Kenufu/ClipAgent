#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  echo '请先双击「安装 ClipAgent.command」。'
  if [ -t 0 ]; then read -r -p '按回车关闭窗口…' answer || true; fi
  exit 1
fi
.venv/bin/python -m scripts.launcher "$@" || {
  code=$?
  if [ -t 0 ]; then read -r -p '启动未完成，请查看上方说明。按回车关闭…' answer || true; fi
  exit "$code"
}
