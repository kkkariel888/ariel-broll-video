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
  render.py 样图.html --at 0 --out 风格样图/a_1.png                                              静态定格图（样图）：页面不用写 render(t)，画好设 window.READY=true
  render.py --compare 参考图.jpg 样图.png --out 对比.png                                            参考图和样图并排（检查有没有太像）
可选：--keytimes 0.4,1.6,2.9（关键帧时间点；不填就读页面的 window.KEYTIMES，再不行取 25% / 60% / 结尾）

批量（并行，省时间）：
  render.py --batch 任务.json --jobs 3 --report 出图结果.json
  任务.json 是数组，每个就是一次上面的命令：{"page":"风格样图/a_1.html","keyframes":true,"at":[2.4],"out":"风格样图/a_1.png","label":"…","size":"1080x1920"}
  不写 keyframes / at 就出视频。每做完一个打印一行「完成 3/9：…」（做完一个就能先给用户看），最后一行 STATUS=ok / STATUS=有问题
自动质检（默认开，--no-qa 关）：在关键帧时间点查「字出界 / 字被裁掉 / 字太小 / 图片糊 / 整张空白」，
  有问题打印「质检：…」，批量时写进报告的 qa 里——AI 先自己修好再给用户看。
"""
import argparse, base64, http.server, json, os, pathlib, platform, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time, urllib.request

LIB = pathlib.Path(os.environ.get('LEMO_OPUSCAR_HOME', pathlib.Path.home() / 'lemo-opuscar'))
BROLL_HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker'))
# 页面里的绝对路径：/@fonts/ = 下载好的字体（fonts.py get），/@kits/ = 每个风格存下来的画图工具，/@film/ = 画面页所在文件夹，其余 = Lemo 风格库
SHARED = {'/@fonts/': BROLL_HOME / 'fonts', '/@kits/': BROLL_HOME / 'kits'}
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
        pre = next((p for p in SHARED if path.startswith(p)), None)
        if pre: base, rest = str(SHARED[pre]), path[len(pre):]
        elif path.startswith('/@film/'): base, rest = self.film, path[len('/@film/'):]
        else: base, rest = str(LIB), path.lstrip('/')
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

QA_JS = r"""(()=>{const W=innerWidth,H=innerHeight,minFs=Math.min(W,H)/45,bad=[];
const vis=el=>{for(let p=el;p&&p!==document.documentElement;p=p.parentElement){const c=getComputedStyle(p);
  if(c.display==='none'||c.visibility==='hidden'||+c.opacity<0.05)return false;}return true;};
const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
while(n=tw.nextNode()){const s=n.textContent.trim(); if(!s)continue; const el=n.parentElement; if(!el||!vis(el))continue;
  const r=document.createRange(); r.selectNodeContents(n); const rs=[...r.getClientRects()].filter(b=>b.width>0); if(!rs.length)continue;
  const fs=parseFloat(getComputedStyle(el).fontSize), t=s.slice(0,14);
  if(rs.some(b=>b.left<-2||b.top<-2||b.right>W+2||b.bottom>H+2)){bad.push('字出界：'+t);continue;}
  if(fs<minFs){bad.push('字太小（'+Math.round(fs)+'px，至少 '+Math.ceil(minFs)+'px）：'+t);continue;}
  for(let p=el;p&&p!==document.body;p=p.parentElement){const c=getComputedStyle(p);
    if(c.overflow!=='visible'&&(p.scrollWidth>p.clientWidth+2||p.scrollHeight>p.clientHeight+2)&&/(hidden|clip)/.test(c.overflow)){bad.push('字被裁掉：'+t);break;}}}
for(const im of document.images){ if(!vis(im)||!im.complete)continue; const b=im.getBoundingClientRect();
  if(b.width>200&&im.naturalWidth&&im.naturalWidth<b.width*0.6) bad.push('图片糊（原图 '+im.naturalWidth+'px 放到 '+Math.round(b.width)+'px）：'+(im.getAttribute('src')||'').split('/').pop().slice(0,24));}
return [...new Set(bad)].slice(0,8);})()"""

def blank(png):
    """整张几乎一个颜色 = 空白 / 没画出来。"""
    if not shutil.which('ffmpeg'): return False
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'image2pipe', '-i', '-', '-vf', 'scale=64:64,format=gray', '-f', 'rawvideo', '-'],
                       input=png, capture_output=True)
    px = r.stdout
    if len(px) < 64: return False
    m = sum(px) / len(px)
    return (sum((x - m) ** 2 for x in px) / len(px)) ** 0.5 < 3

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

def render(page, size='1080x1920', out=None, keyframes=False, at=None, keytimes=None, fps=60, label=None, quiet=False, scale=None, qa=None):
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
        if not fn and not (at or keyframes):
            raise RuntimeError('页面没有 window.render(t)，出不了视频（静态的定格图页面只能出图：加 --at）')
        dur = float(cdp.js('window.DUR') or 3.0)
        def draw(t):
            if not fn: return   # 静态定格图（样图）：页面画好就是那一张
            cdp.js(f'(async()=>{{const r=window.{fn}({max(0.0, min(dur, t))}); if(r&&r.then) await r; return 1}})()', wait=True)
            if cdp.errors: raise RuntimeError('页面出错：' + '；'.join(map(str, cdp.errors))[:800])
        def check(t, png=None):
            if qa is None: return
            for x in (cdp.js(QA_JS) or []):
                qa.append(f'{t:.1f}s {x}')
            if png is not None and blank(png): qa.append(f'{t:.1f}s 整张几乎空白（没画出来？）')
        if keyframes or at:
            out = pathlib.Path(out or page.with_suffix(''))
            if at: times, names = [float(x) for x in at], [f'{float(x):.2f}s' for x in at]
            else:
                times = [float(x) for x in keytimes.split(',')] if keytimes else (cdp.js('window.KEYTIMES') or [dur * 0.25, dur * 0.6, dur - 0.04])
                names = ['开场', '最满', '定格'] if len(times) == 3 else [f'{t:.2f}s' for t in times]
            single = out.suffix.lower() in ('.png', '.jpg') and len(times) == 1
            (out.parent if single else out).mkdir(parents=True, exist_ok=True)
            frames = []
            for i, t in enumerate(times):
                draw(t); png = cdp.shot(w, h); check(t, png); frames.append((out if single else out / f'{i + 1}_{names[i]}.png', png))
            for p, png in frames:
                if label: png = with_label(cdp, png, w, h, label, tmp)
                p.write_bytes(png); results.append(str(p))
        else:
            if not shutil.which('ffmpeg'): raise RuntimeError('没找到 ffmpeg，出不了视频（关键帧图可以出：加 --keyframes）')
            out = pathlib.Path(out or page.with_suffix('.mp4')); out.parent.mkdir(parents=True, exist_ok=True)
            if qa is not None:
                for t in (cdp.js('window.KEYTIMES') or [dur * 0.25, dur * 0.6, dur - 0.04]):
                    draw(float(t)); check(float(t), cdp.shot(w, h))
            part = out.with_name('.' + out.stem + '.part' + out.suffix)   # 渲染完才改名，页面上不会出现半截视频
            n = max(1, round(dur * fps))
            ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'png', '-i', '-',
                                   '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', str(fps), '-movflags', '+faststart', str(part)],
                                  stdin=subprocess.PIPE)
            for f in range(n):
                draw(f / fps); ff.stdin.write(cdp.shot(w, h))
                if not quiet and f % int(fps) == 0: print(f'  {f}/{n} 帧', file=sys.stderr)
            ff.stdin.close(); ff.wait()
            if ff.returncode: raise RuntimeError('ffmpeg 合成失败')
            os.replace(part, out)
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

def batch(jobs_path, n, report, do_qa=True):
    """并行做一批（风格样图 9 张、每个画面的关键帧、所有成片），做完一个打印一个。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    base = pathlib.Path(jobs_path).resolve().parent
    jobs = json.load(open(jobs_path, encoding='utf-8'))
    def one(i, j):
        q = [] if do_qa else None
        pg = j['page'] if os.path.isabs(j['page']) else str(base / j['page'])
        out = j.get('out'); out = out if not out or os.path.isabs(out) else str(base / out)
        t0 = time.time()
        try:
            res = render(pg, j.get('size', '1080x1920'), out, j.get('keyframes', False), j.get('at'), j.get('keytimes'),
                         j.get('fps', 60), j.get('label'), quiet=True, scale=j.get('scale'), qa=q)
            return dict(j, i=i, ok=True, files=res, qa=q or [], seconds=round(time.time() - t0, 1))
        except BaseException as e:   # sys.exit 也接住，别让一个坏页面拖垮整批
            return dict(j, i=i, ok=False, error=str(e)[:500], qa=q or [], seconds=round(time.time() - t0, 1))
    done = []
    with ThreadPoolExecutor(max_workers=max(1, n)) as ex:
        futs = [ex.submit(one, i, j) for i, j in enumerate(jobs)]
        for f in as_completed(futs):
            r = f.result(); done.append(r)
            tag = '完成' if r['ok'] and not r['qa'] else ('质检有问题' if r['ok'] else '失败')
            print(f"{tag} {len(done)}/{len(jobs)}：{r['page']} → {', '.join(r.get('files', [])) or r.get('error', '')}"
                  + (f"｜质检：{'；'.join(r['qa'])}" if r['qa'] else ''), flush=True)
    done.sort(key=lambda r: r.pop('i'))
    if report:
        json.dump(done, open(report, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    bad = [r for r in done if not r['ok'] or r['qa']]
    print('STATUS=' + ('ok' if not bad else '有问题'))
    return done

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page', nargs='?'); ap.add_argument('--size', default='1080x1920'); ap.add_argument('--fps', type=float, default=60)
    ap.add_argument('--scale', type=float, help='放大倍数：默认 1（1080P）；2 = 4K（1080x1920 → 2160x3840），慢约 2.5 倍')
    ap.add_argument('--keyframes', action='store_true'); ap.add_argument('--at', nargs='+'); ap.add_argument('--keytimes')
    ap.add_argument('--label'); ap.add_argument('--out'); ap.add_argument('--compare', nargs=2, metavar=('参考图', '样图'))
    ap.add_argument('--batch', help='任务.json：一批并行做'); ap.add_argument('--jobs', type=int, default=3, help='同时做几个（默认 3）')
    ap.add_argument('--report', help='批量结果写到这个 json'); ap.add_argument('--no-qa', action='store_true', help='关掉自动质检')
    a = ap.parse_args()
    if a.batch:
        batch(a.batch, a.jobs, a.report, not a.no_qa); return
    if a.compare:
        return compare(a.compare[0], a.compare[1], a.out or '对比.png')
    if not a.page: ap.error('要给画面页，比如 B3.html')
    fps = int(a.fps) if float(a.fps).is_integer() else a.fps
    q = None if a.no_qa else []
    for r in render(a.page, a.size, a.out, a.keyframes, a.at, a.keytimes, fps, a.label, scale=a.scale, qa=q):
        print(r)
    for x in (q or []):
        print('质检：' + x)

if __name__ == '__main__':
    main()
