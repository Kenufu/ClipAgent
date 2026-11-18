#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
finish() { code=$?; if [ "$code" -ne 0 ]; then echo '安装未完成，请保留上方错误信息。联网后可再次运行本文件。'; fi; if [ -t 0 ]; then read -r -p '按回车关闭窗口…' answer || true; fi; }
trap finish EXIT
echo 'ClipAgent 本地安装：首次需要联网下载依赖和语音模型。'
py=''
for candidate in python3.12 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3,12))' 2>/dev/null; then py="$candidate"; break; fi
done
if [ -z "$py" ]; then
  echo '请先从 https://www.python.org/downloads/macos/ 安装 Python 3.12，再运行本文件。'
  exit 1
fi
if [ -f /etc/ssl/cert.pem ]; then
  export PIP_CERT="${PIP_CERT:-/etc/ssl/cert.pem}"
  export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/cert.pem}"
fi
if [ ! -x .venv/bin/python ]; then "$py" -m venv .venv; fi
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3,12), "现有 .venv 不是 Python 3.12，请在新的解压目录安装。"'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m scripts.setup_local
echo '安装完成。以后双击「启动 ClipAgent.command」即可打开工作台。'
