#!/usr/bin/env python3
"""统一出图命令：一句话 + 时长 + 竖/横屏 → 关键帧图或小视频。所有风格都走这一个口子。
只用 Python 自带库 + 本机 Chrome（或 Edge/Chromium）+ ffmpeg，不用装别的。

用法：
  render.py --style line-minimal --text "复利就是利滚利" --dur 3 --aspect 9:16 --out B1.mp4
  render.py --style data-story --text "年化 8% 和 2%，十年差两倍" --dur 3 --aspect 16:9 --keyframes --label "B3 · 00:41：…" --out 关键帧/B3
风格只管长相；版式（讲原理/比数字/演示工具/讲新闻/讲结论）按这句话自动配，--layout 可以手动指定。
可选：--size 1080x1920  --fps 30  --mode text|anim  --items "一|二|三"  --emphasis "重点词"  --at 1.2（只出这一秒的一张图）
"""
import argparse, base64, json, os, pathlib, platform, random, re, shutil, socket, struct, subprocess, sys, tempfile, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent          # skill 根目录
STYLES = HERE / 'styles'
HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker'))
LABEL_H = 150

# ---------- 找风格 ----------
def find_style(s):
    p = pathlib.Path(s).expanduser()
    for d in [p, STYLES / s, HOME / 'my-styles' / s]:
        if (d / 'style.json').exists():
            return d
    sys.exit(f'找不到风格：{s}（内置风格在 {STYLES}，我的风格在 {HOME/"my-styles"}）')

def load_style(d):
    return json.loads((d / 'style.json').read_text(encoding='utf-8'))

# ---------- 每句自动配版式 ----------
LAYOUTS = ['principle', 'numbers', 'tool', 'news', 'conclusion']
LAYOUT_CN = {'principle': '讲原理', 'numbers': '比数字', 'tool': '演示工具', 'news': '讲新闻', 'conclusion': '讲结论'}
def pick_layout(text):
    """风格只管长相，版式按这句话的内容自动配。顺序：数字 > 新闻 > 工具 > 结论 > 原理。"""
    nums = re.findall(r'\d+(?:\.\d+)?\s*(%|％|倍|万|亿|元|块|美元|年|个月|天|小时|岁|次|人)?', text)
    if len(nums) >= 2 or any(u for u in nums):
        return 'numbers'
    if re.search(r'发布|宣布|官宣|上线|刚刚|最新|消息|报道|曝光|\d{1,2}\s*月\s*\d{1,2}\s*日|今天.{0,6}(公布|推出)', text):
        return 'news'
    if re.search(r'Claude|GPT|ChatGPT|Codex|Cursor|AI|App|软件|工具|插件|命令|代码|点击|打开|按钮|一键|设置|[A-Za-z]{4,}', text):
        return 'tool'
    if re.search(r'所以|总之|结论|记住|一句话|说到底|本质上|最重要|核心是|关键是', text):
        return 'conclusion'
    return 'principle'

# ---------- 拼页面 ----------
BASE_CSS = '''html,body{margin:0;padding:0;background:#000;overflow:hidden}
#stage{position:relative;overflow:hidden}
#stage>*{position:absolute}
.tex{left:0;top:0;width:100%;height:100%;pointer-events:none}
#label{position:relative;box-sizing:border-box;padding:0 40px;display:flex;align-items:center;background:#111;color:#fff;
 font:500 40px "Source Han Sans SC","Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.3;overflow:hidden}
#label span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
#label b{color:#FFD43B;margin-right:18px}'''

def build_page(st, sd, scene, label=None):
    eng = STYLES / '_engine'
    lay = (STYLES / '_layouts' / f"{scene['layout']}.js").read_text(encoding='utf-8')
    fonts = ''
    for f in (st.get('type') or {}).get('files', []):          # 风格包自带字体（可选）
        fp = sd / f['file']
        if fp.exists():
            fonts += "@font-face{font-family:'%s';src:url(data:font/%s;base64,%s);font-weight:%s}" % (
                f['family'], fp.suffix[1:], base64.b64encode(fp.read_bytes()).decode(), f.get('weight', '100 900'))
    lab = ''
    if label:
        m = re.match(r'^(\S+\s*·\s*[\d:]+)[：:]\s*(.*)$', label)
        inner = f'<span><b>{esc(m.group(1))}</b>{esc(m.group(2))}</span>' if m else f'<span>{esc(label)}</span>'
        lab = f'<div id="label" style="width:{scene["w"]}px;height:{LABEL_H}px;font-size:{max(26, min(scene["w"], scene["h"])//30)}px">{inner}</div>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{fonts}{BASE_CSS}</style></head>
<body><div id="stage"></div>{lab}
<script>{(eng/'motion.js').read_text(encoding='utf-8')}</script>
<script>{(eng/'kit.js').read_text(encoding='utf-8')}</script>
<script>window.STYLE={json.dumps(st, ensure_ascii=False)};window.SCENE={json.dumps(scene, ensure_ascii=False)};</script>
<script>{lay}
(function(){{const s=document.createElement('style');s.textContent=window.LAYOUT.css||'';document.head.appendChild(s);}})();
window.__ERR=[];window.addEventListener('error',e=>window.__ERR.push(String(e.message)));
try{{K.start();}}catch(e){{window.__ERR.push(String(e&&e.stack||e));}}</script></body></html>'''

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ---------- 找 Chrome ----------
def find_chrome():
    if os.environ.get('CHROME'):
        return os.environ['CHROME']
    cands = []
    sysname = platform.system()
    if sysname == 'Darwin':
        cands = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                 '/Applications/Chromium.app/Contents/MacOS/Chromium',
                 '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                 os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
    elif sysname == 'Windows':
        for base in [os.environ.get('PROGRAMFILES', ''), os.environ.get('PROGRAMFILES(X86)', ''), os.environ.get('LOCALAPPDATA', '')]:
            cands += [os.path.join(base, 'Google/Chrome/Application/chrome.exe'), os.path.join(base, 'Microsoft/Edge/Application/msedge.exe')]
    for n in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge']:
        w = shutil.which(n)
        if w:
            cands.append(w)
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit('没找到 Chrome / Edge / Chromium。装一个 Chrome，或用环境变量 CHROME 指定路径。')

# ---------- 极简 WebSocket + Chrome 调试协议 ----------
class CDP:
    def __init__(self, chrome, w, h):
        self.tmp = tempfile.mkdtemp(prefix='broll-chrome-')
        args = [chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
                '--mute-audio', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-pings', '--disable-default-apps', '--force-color-profile=srgb', '--font-render-hinting=none', '--allow-file-access-from-files',
                f'--user-data-dir={self.tmp}', '--remote-debugging-port=0', f'--window-size={w},{h}', 'about:blank']
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            args.insert(1, '--no-sandbox')
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        port = None; t0 = time.time()
        while time.time() - t0 < 30:
            p = pathlib.Path(self.tmp) / 'DevToolsActivePort'
            if p.exists():
                lines = p.read_text().split()
                if lines:
                    port = int(lines[0]); break
            time.sleep(0.05)
        if not port:
            self.close(); sys.exit('Chrome 启动失败（30 秒没响应）')
        for _ in range(100):
            try:
                tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=2).read())
                page = [t for t in tabs if t.get('type') == 'page']
                if page:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        url = page[0]['webSocketDebuggerUrl']
        self._connect(url); self.id = 0

    def _connect(self, url):
        m = re.match(r'ws://([^/:]+):(\d+)(/.*)', url)
        self.sock = socket.create_connection((m.group(1), int(m.group(2))), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {m.group(3)} HTTP/1.1\r\nHost: {m.group(1)}:{m.group(2)}\r\nUpgrade: websocket\r\n'
                           f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.sock.recv(4096)
        if b' 101 ' not in buf.split(b'\r\n')[0]:
            sys.exit('连不上 Chrome 调试口')
        self.rest = buf.split(b'\r\n\r\n', 1)[1]

    def _recv_exact(self, n):
        while len(self.rest) < n:
            chunk = self.sock.recv(max(65536, n - len(self.rest)))
            if not chunk:
                raise ConnectionError('Chrome 断开了')
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _recv_msg(self):
        data = b''
        while True:
            b1, b2 = self._recv_exact(2)
            op, ln = b1 & 0x0F, b2 & 0x7F
            if ln == 126: ln = struct.unpack('>H', self._recv_exact(2))[0]
            elif ln == 127: ln = struct.unpack('>Q', self._recv_exact(8))[0]
            mask = self._recv_exact(4) if b2 & 0x80 else None
            payload = self._recv_exact(ln)
            if mask:
                payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
            if op == 9:      # ping → pong
                self._send(payload, 10); continue
            if op == 8:
                raise ConnectionError('Chrome 关闭了连接')
            data += payload
            if b1 & 0x80:
                return data.decode('utf-8')

    def _send(self, payload, op=1):
        hdr = bytes([0x80 | op]); n = len(payload)
        hdr += bytes([0x80 | n]) if n < 126 else (bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else bytes([0x80 | 127]) + struct.pack('>Q', n))
        mask = os.urandom(4)
        self.sock.sendall(hdr + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload)))

    def call(self, method, **params):
        self.id += 1; my = self.id
        self._send(json.dumps({'id': my, 'method': method, 'params': params}).encode())
        while True:
            msg = json.loads(self._recv_msg())
            if msg.get('id') == my:
                if 'error' in msg:
                    raise RuntimeError(f"{method}: {msg['error'].get('message')}")
                return msg.get('result', {})

    def js(self, expr, wait=False):
        r = self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=wait)
        if 'exceptionDetails' in r:
            raise RuntimeError('页面脚本出错：' + json.dumps(r['exceptionDetails'], ensure_ascii=False)[:600])
        return r.get('result', {}).get('value')

    def shot(self, w, h):
        r = self.call('Page.captureScreenshot', format='png', fromSurface=True, captureBeyondViewport=False,
                      clip={'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1})
        return base64.b64decode(r['data'])

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        try:
            self.proc.terminate(); self.proc.wait(timeout=5)
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        shutil.rmtree(self.tmp, ignore_errors=True)

# ---------- 主流程 ----------
def parse_size(aspect, size):
    if size:
        w, h = [int(x) for x in size.lower().split('x')]; return w, h
    return (1080, 1920) if aspect in ('9:16', 'v', '竖') else (1920, 1080)

def render(style, text, dur=3.0, aspect='9:16', size=None, fps=30, mode='anim', items=None, emphasis=None,
           out=None, keyframes=False, label=None, at=None, chrome=None, quiet=False, layout=None):
    sd = find_style(style); st = load_style(sd)
    w, h = parse_size(aspect, size)
    layout = layout or pick_layout(text)
    if layout not in LAYOUTS:
        sys.exit(f'版式只能是：{"、".join(LAYOUTS)}')
    scene = {'text': text, 'dur': float(dur), 'w': w, 'h': h, 'mode': mode, 'layout': layout,
             'items': [x for x in (items or '').split('|') if x.strip()] if isinstance(items, str) else (items or []),
             'emphasis': emphasis or ''}
    page_h = h + (LABEL_H if label else 0)
    html = build_page(st, sd, scene, label)
    tmpd = tempfile.mkdtemp(prefix='broll-page-'); hp = pathlib.Path(tmpd) / 'scene.html'
    hp.write_text(html, encoding='utf-8')
    cdp = CDP(chrome or find_chrome(), w, page_h)
    results = []
    try:
        cdp.call('Emulation.setDeviceMetricsOverride', width=w, height=page_h, deviceScaleFactor=1, mobile=False)
        cdp.call('Page.enable')
        cdp.call('Page.navigate', url=hp.as_uri())
        for _ in range(200):
            if cdp.js('document.readyState') == 'complete': break
            time.sleep(0.05)
        cdp.js('document.fonts.ready.then(()=>1)', wait=True)
        errs = cdp.js('window.__ERR')
        if errs:
            raise RuntimeError('模板出错：' + '；'.join(errs)[:800])
        out = pathlib.Path(out or f'{sd.name}.mp4')
        if at is not None or keyframes:
            times = [float(at)] if at is not None else cdp.js('window.KEYTIMES')
            names = ['开场', '最满', '定格'] if at is None else ['']
            if out.suffix.lower() == '.png' and len(times) == 1:
                paths = [out]
            else:
                out.mkdir(parents=True, exist_ok=True)
                paths = [out / f'{i+1}{("_"+names[i]) if names[i] else ""}.png' for i in range(len(times))]
            for t, p in zip(times, paths):
                cdp.js(f'seek({max(0.0, min(float(dur), t))})')
                p.write_bytes(cdp.shot(w, page_h)); results.append(str(p))
        else:
            if not shutil.which('ffmpeg'):
                raise RuntimeError('没找到 ffmpeg，出不了视频（关键帧图可以出：加 --keyframes）')
            out.parent.mkdir(parents=True, exist_ok=True)
            n = max(1, round(float(dur) * fps))
            ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'png', '-i', '-',
                                   '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', str(fps),
                                   '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
            for f in range(n):
                cdp.js(f'seek({f / fps})')
                ff.stdin.write(cdp.shot(w, h))
                if not quiet and f % fps == 0:
                    print(f'  {f}/{n} 帧', file=sys.stderr)
            ff.stdin.close(); ff.wait()
            if ff.returncode: raise RuntimeError('ffmpeg 合成失败')
            results.append(str(out))
        errs = cdp.js('window.__ERR')
        if errs:
            raise RuntimeError('模板出错：' + '；'.join(errs)[:800])
    finally:
        cdp.close(); shutil.rmtree(tmpd, ignore_errors=True)
    return results

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--style', required=True); ap.add_argument('--text', required=True)
    ap.add_argument('--dur', type=float, default=3.0); ap.add_argument('--aspect', default='9:16')
    ap.add_argument('--size'); ap.add_argument('--fps', type=float, default=30)
    ap.add_argument('--mode', default='anim', choices=['anim', 'text'])
    ap.add_argument('--items'); ap.add_argument('--emphasis')
    ap.add_argument('--keyframes', action='store_true'); ap.add_argument('--at', type=float)
    ap.add_argument('--label'); ap.add_argument('--out')
    ap.add_argument('--layout', choices=LAYOUTS, help='不填就按这句话自动配：principle 讲原理 / numbers 比数字 / tool 演示工具 / news 讲新闻 / conclusion 讲结论')
    ap.add_argument('--which-layout', action='store_true', help='只打印这句会配到哪个版式')
    a = ap.parse_args()
    if a.which_layout:
        l = pick_layout(a.text); print(l, LAYOUT_CN[l]); return
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    for r in render(a.style, a.text, a.dur, a.aspect, a.size, fps, a.mode, a.items, a.emphasis, a.out, a.keyframes, a.label, a.at, layout=a.layout):
        print(r)

if __name__ == '__main__':
    main()
