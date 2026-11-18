"""Local launcher: validate setup, choose a free loopback port, open the browser."""
import argparse
import importlib.util
import socket
import subprocess
import sys
import time
import urllib.request
import json
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def choose_port(first):
    for port in range(first, min(first+20, 65536)):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('附近端口均被占用，请用 --port 指定其他端口。')


def ready(port):
    try:
        # Bypass external proxy settings for the loopback-only application.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/openapi.json', timeout=1) as response:
            return json.load(response).get('info', {}).get('title') == 'ClipAgent'
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description='启动 ClipAgent 本地剪辑工作台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='只检查环境，不启动服务')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('端口范围应为 1024–65535')
    for module in ('fastapi', 'uvicorn', 'multipart', 'av', 'imageio_ffmpeg', 'faster_whisper'):
        if importlib.util.find_spec(module) is None:
            raise RuntimeError('缺少运行依赖，请先运行「安装 ClipAgent.command」。')
    from clipagent.media import _whisper
    try:
        _whisper()
    except Exception as exc:
        raise RuntimeError('语音模型尚未就绪，请联网运行「安装 ClipAgent.command」。') from exc
    if args.check:
        print('环境检查通过：应用依赖和本地语音模型已就绪。')
        return
    from scripts import prepare_samples
    port = choose_port(args.port)
    url = f'http://127.0.0.1:{port}'
    print(f'正在启动 {url}；保持本窗口打开，按 Ctrl+C 停止。', flush=True)
    child = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT)
    try:
        deadline = time.monotonic()+30
        while time.monotonic() < deadline and child.poll() is None:
            if ready(port):
                print(f'工作台已就绪：{url}', flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
                if child.wait() != 0:
                    raise RuntimeError('服务异常退出，请查看上方输出。')
                return
            time.sleep(.25)
        raise RuntimeError('服务启动失败，请查看上方输出。')
    except KeyboardInterrupt:
        print('\n正在停止 ClipAgent…', flush=True)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'启动失败：{exc}', file=sys.stderr)
        raise SystemExit(1)
