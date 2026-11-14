#!/usr/bin/env python3
"""出图命令：把 AI 为某一处标黄现画的画面页（B3.html 之类）渲染成关键帧图或视频。
只用 Python 自带库 + 本机 Chrome（或 Edge / Chromium）+ ffmpeg，不用装别的。

画面页的约定（和 Lemo-Opuscar 的页面约定一样，所以它的工具库可以直接用）：
  window.render(t)   画出第 t 秒的样子，同样的 t 永远同样的画面（不用定时器、不用 CSS 过渡）
  window.DUR         这段画面多少秒
  window.READY=true  字体、图片都加载好了再设
  页面里可以用 /core/lib.js 这类绝对路径引用 Lemo 风格库里的工具（会从 ~/lemo-opuscar 提供）；
  画面页自己所在的文件夹挂在 /@film/ 下。

用法：
  render.py B3.html --size 1080x1920 --keyframes --label "B3 · 00:41：原话" --out 逐帧图/B3     出 开场/最满/定格 3 张
  render.py B3.html --size 1080x1920 --at 1.2 2.4 --out 逐帧图/B3                                指定时间点出图
  render.py B3.html --size 1080x1920 --out 成片/B3.mp4                                            出视频：默认 1080P 60 帧，不管原片多糊（要 4K 加 --scale 2，慢约 2.5 倍）
  render.py --compare 参考图.jpg 样图.png --out 对比.png                                            参考图和样图并排（检查有没有太像）
可选：--keytimes 0.4,1.6,2.9（关键帧时间点；不填就读页面的 window.KEYTIMES，再不行取 25% / 60% / 结尾）
"""
import argparse, base64, http.server, json, os, pathlib, platform, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time, urllib.request

LIB = pathlib.Path(os.environ.get('LEMO_OPUSCAR_HOME', pathlib.Path.home() / 'lemo-opuscar'))
LABEL_H = 150

def find_chrome():
    if os.environ.get('CHROME'):
        return os.environ['CHROME']
    cands = []
    if platform.system() == 'Darwin':
        cands = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium',
                 '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                 os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
    elif platform.system() == 'Windows':
        for base in [os.environ.get('PROGRAMFILES', ''), os.environ.get('PROGRAMFILES(X86)', ''), os.environ.get('LOCALAPPDATA', '')]:
            cands += [os.path.join(base, 'Google/Chrome/Application/chrome.exe'), os.path.join(base, 'Microsoft/Edge/Application/msedge.exe')]
    for n in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge']:
        w = shutil.which(n)
        if w: cands.append(w)
    import glob   # Linux 沙盒里常见：Playwright 自带的 Chromium
    cands += sorted(glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium*/chrome-linux*/chrome')), reverse=True)
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit('没找到 Chrome / Edge / Chromium。装一个 Chrome，或用环境变量 CHROME 指定路径。')

# ---------- 本机小服务器：/@film/ = 画面页文件夹，其余路径 = Lemo 风格库 ----------
class _H(http.server.SimpleHTTPRequestHandler):
    film = '.'
    def log_message(self, *a): pass
    def translate_path(self, path):
        from urllib.parse import unquote
        path = unquote(path.split('?', 1)[0].split('#', 1)[0])
        base, rest = (self.film, path[len('/@film/'):]) if path.startswith('/@film/') else (str(LIB), path.lstrip('/'))
        full = os.path.normpath(os.path.join(base, rest))
        return full if full.startswith(os.path.normpath(base)) else os.path.join(base, '__denied__')
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
_H.extensions_map.update({'.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2', '.wasm': 'application/wasm'})

def serve(folder):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), type('H', (_H,), {'film': str(folder)}))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

# ---------- 极简 WebSocket + Chrome 调试协议 ----------
class CDP:
    def __init__(self, chrome, w, h, scale=1):
        self.errors = []; self.scale = scale
        self.tmp = tempfile.mkdtemp(prefix='broll-chrome-')
        args = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
                '--mute-audio', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-pings',
                '--disable-default-apps', '--force-color-profile=srgb', '--font-render-hinting=none',
                f'--user-data-dir={self.tmp}', '--remote-debugging-port=0', f'--window-size={w},{h}', 'about:blank']
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            args.insert(1, '--no-sandbox')
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port, t0 = None, time.time()
        while time.time() - t0 < 30 and not port:
            p = pathlib.Path(self.tmp) / 'DevToolsActivePort'
            if p.exists() and p.read_text().split():
                port = int(p.read_text().split()[0])
            time.sleep(0.05)
        if not port:
            self.close(); sys.exit('Chrome 启动失败（30 秒没响应）')
        page = []
        for _ in range(100):
            try:
                page = [t for t in json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=2).read()) if t.get('type') == 'page']
                if page: break
            except Exception:
                pass
            time.sleep(0.1)
        self._connect(page[0]['webSocketDebuggerUrl']); self.id = 0

    def _connect(self, url):
        m = re.match(r'ws://([^/:]+):(\d+)(/.*)', url)
        self.sock = socket.create_connection((m.group(1), int(m.group(2))), timeout=300)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {m.group(3)} HTTP/1.1\r\nHost: {m.group(1)}:{m.group(2)}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.sock.recv(4096)
        self.rest = buf.split(b'\r\n\r\n', 1)[1]

    def _exact(self, n):
        while len(self.rest) < n:
            c = self.sock.recv(max(65536, n - len(self.rest)))
            if not c: raise ConnectionError('Chrome 断开了')
            self.rest += c
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _recv(self):
        data = b''
        while True:
            b1, b2 = self._exact(2); op, ln = b1 & 15, b2 & 127
            if ln == 126: ln = struct.unpack('>H', self._exact(2))[0]
            elif ln == 127: ln = struct.unpack('>Q', self._exact(8))[0]
            mask = self._exact(4) if b2 & 128 else None
            pl = self._exact(ln)
            if mask: pl = bytes(c ^ mask[i % 4] for i, c in enumerate(pl))
            if op == 9: self._send(pl, 10); continue
            if op == 8: raise ConnectionError('Chrome 关闭了连接')
            data += pl
            if b1 & 128: return data.decode('utf-8')

    def _send(self, pl, op=1):
        n = len(pl); hdr = bytes([128 | op])
        hdr += bytes([128 | n]) if n < 126 else (bytes([128 | 126]) + struct.pack('>H', n) if n < 65536 else bytes([128 | 127]) + struct.pack('>Q', n))
        mask = os.urandom(4)
        self.sock.sendall(hdr + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(pl)))

    def call(self, method, **params):
        self.id += 1; my = self.id
        self._send(json.dumps({'id': my, 'method': method, 'params': params}).encode())
        while True:
            msg = json.loads(self._recv())
            if msg.get('id') == my:
                if 'error' in msg: raise RuntimeError(f"{method}: {msg['error'].get('message')}")
                return msg.get('result', {})
            if msg.get('method') == 'Runtime.exceptionThrown':
                d = msg['params']['exceptionDetails']; self.errors.append((d.get('exception') or {}).get('description') or d.get('text'))

    def js(self, expr, wait=False):
        r = self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=wait)
        if 'exceptionDetails' in r:
            raise RuntimeError('页面脚本出错：' + json.dumps(r['exceptionDetails'], ensure_ascii=False)[:600])
        return r.get('result', {}).get('value')

    def size(self, w, h):
        self.call('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=self.scale, mobile=False)

    def shot(self, w, h):
        return base64.b64decode(self.call('Page.captureScreenshot', format='png', fromSurface=True, captureBeyondViewport=False,
                                          clip={'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1})['data'])

    def goto(self, url, wait_ready=True):
        self.call('Page.navigate', url=url)
        for _ in range(400):
            if self.js('document.readyState') == 'complete': break
            time.sleep(0.05)
        self.js('document.fonts.ready.then(()=>1)', wait=True)
        if wait_ready:
            t0 = time.time()
            while not self.js('window.READY===true || (typeof window.READY==="undefined" && (typeof window.render==="function" || typeof window.seek==="function"))'):
                if time.time() - t0 > 180: raise RuntimeError('等了 3 分钟页面还没 READY（字体或图片没加载完？）')
                if self.errors: raise RuntimeError('页面出错：' + '；'.join(map(str, self.errors))[:800])
                time.sleep(0.1)

    def close(self):
        try: self.sock.close()
        except Exception: pass
        try: self.proc.terminate(); self.proc.wait(timeout=5)
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        shutil.rmtree(self.tmp, ignore_errors=True)

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def with_label(cdp, png, w, h, label, tmpdir):
    """审稿用：在图下面加一条「B3 · 00:41：原话」，标注不进成片。"""
    m = re.match(r'^(\S+\s*·\s*[\d:]+)[：:]\s*(.*)$', label)
    inner = f'<b>{esc(m.group(1))}</b>{esc(m.group(2))}' if m else esc(label)
    fs = max(26, min(w, h) // 30)
    p = pathlib.Path(tmpdir) / 'label.html'
    p.write_text(f'''<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#111}}img{{display:block}}
#l{{width:{w}px;height:{LABEL_H}px;box-sizing:border-box;padding:0 40px;display:flex;align-items:center;color:#fff;
font:500 {fs}px "Source Han Sans SC","Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.3}}
#l span{{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}b{{color:#FFD43B;margin-right:18px}}</style>
<img src="data:image/png;base64,{base64.b64encode(png).decode()}" width="{w}" height="{h}"><div id="l"><span>{inner}</span></div>''', encoding='utf-8')
    cdp.size(w, h + LABEL_H); cdp.goto(p.as_uri(), wait_ready=False)
    out = cdp.shot(w, h + LABEL_H); cdp.size(w, h)
    return out

def render(page, size='1080x1920', out=None, keyframes=False, at=None, keytimes=None, fps=60, label=None, quiet=False, scale=None):
    page = pathlib.Path(page).resolve()
    if not page.exists(): sys.exit(f'找不到画面页：{page}')
    w, h = [int(x) for x in size.lower().split('x')]
    srv = serve(page.parent)
    url = f'http://127.0.0.1:{srv.server_address[1]}/@film/{page.name}'
    if scale is None: scale = 1   # 默认 1080P；--scale 2 = 4K（慢约 2.5 倍）
    cdp = CDP(find_chrome(), w, h, scale)
    tmp = tempfile.mkdtemp(prefix='broll-'); results = []
    try:
        cdp.call('Runtime.enable'); cdp.call('Page.enable'); cdp.size(w, h)
        cdp.goto(url)
        fn = 'render' if cdp.js('typeof window.render==="function"') else 'seek' if cdp.js('typeof window.seek==="function"') else None
        if not fn: raise RuntimeError('页面没有 window.render(t)')
        dur = float(cdp.js('window.DUR') or 3.0)
        def draw(t):
            cdp.js(f'(async()=>{{const r=window.{fn}({max(0.0, min(dur, t))}); if(r&&r.then) await r; return 1}})()', wait=True)
            if cdp.errors: raise RuntimeError('页面出错：' + '；'.join(map(str, cdp.errors))[:800])
        if keyframes or at:
            out = pathlib.Path(out or page.with_suffix(''))
            if at: times, names = [float(x) for x in at], [f'{float(x):.2f}s' for x in at]
            else:
                times = [float(x) for x in keytimes.split(',')] if keytimes else (cdp.js('window.KEYTIMES') or [dur * 0.25, dur * 0.6, dur - 0.04])
                names = ['开场', '最满', '定格'] if len(times) == 3 else [f'{t:.2f}s' for t in times]
            single = out.suffix.lower() in ('.png', '.jpg') and len(times) == 1
            if not single: out.mkdir(parents=True, exist_ok=True)
            frames = []
            for i, t in enumerate(times):
                draw(t); frames.append((out if single else out / f'{i + 1}_{names[i]}.png', cdp.shot(w, h)))
            for p, png in frames:
                if label: png = with_label(cdp, png, w, h, label, tmp)
                p.write_bytes(png); results.append(str(p))
        else:
            if not shutil.which('ffmpeg'): raise RuntimeError('没找到 ffmpeg，出不了视频（关键帧图可以出：加 --keyframes）')
            out = pathlib.Path(out or page.with_suffix('.mp4')); out.parent.mkdir(parents=True, exist_ok=True)
            n = max(1, round(dur * fps))
            ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'png', '-i', '-',
                                   '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', str(fps), '-movflags', '+faststart', str(out)],
                                  stdin=subprocess.PIPE)
            for f in range(n):
                draw(f / fps); ff.stdin.write(cdp.shot(w, h))
                if not quiet and f % int(fps) == 0: print(f'  {f}/{n} 帧', file=sys.stderr)
            ff.stdin.close(); ff.wait()
            if ff.returncode: raise RuntimeError('ffmpeg 合成失败')
            results.append(str(out))
    finally:
        cdp.close(); srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
    return results

def compare(ref, ours, out):
    """参考图和我们的样图并排（左参考、右我们），统一高度，用来检查有没有太像。"""
    if not shutil.which('ffmpeg'): sys.exit('没找到 ffmpeg')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', ref, '-i', ours, '-filter_complex',
                    '[0:v]scale=-2:960[a];[1:v]scale=-2:960[b];[a][b]hstack=inputs=2', '-frames:v', '1', out], check=True)
    print(out)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page', nargs='?'); ap.add_argument('--size', default='1080x1920'); ap.add_argument('--fps', type=float, default=60)
    ap.add_argument('--scale', type=float, help='放大倍数：默认 1（1080P）；2 = 4K（1080x1920 → 2160x3840），慢约 2.5 倍')
    ap.add_argument('--keyframes', action='store_true'); ap.add_argument('--at', nargs='+'); ap.add_argument('--keytimes')
    ap.add_argument('--label'); ap.add_argument('--out'); ap.add_argument('--compare', nargs=2, metavar=('参考图', '样图'))
    a = ap.parse_args()
    if a.compare:
        return compare(a.compare[0], a.compare[1], a.out or '对比.png')
    if not a.page: ap.error('要给画面页，比如 B3.html')
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    for r in render(a.page, a.size, a.out, a.keyframes, a.at, a.keytimes, fps, a.label, scale=a.scale):
        print(r)

if __name__ == '__main__':
    main()
