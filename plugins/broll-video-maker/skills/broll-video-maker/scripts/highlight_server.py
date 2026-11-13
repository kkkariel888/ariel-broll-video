#!/usr/bin/env python3
"""逐字稿标黄小助手 —— Claude 和 Codex 共用。

只用 Python 自带的库，不需要另外安装任何东西。

用法：
  python3 highlight_server.py 字幕.srt [--suggest 建议.json] [--out 项目文件夹] [--port 8765]
  （也支持 .docx / .txt / .md）

做的事：
  1. 读 Word 逐字稿（也支持 .txt / .md），保留你在 Word 里已经标的黄色。
  2. 把 AI 建议标黄的句子（--suggest，一个 JSON 字符串数组）也标上。
  3. 在本机开一个网页（打印出地址），AI 在侧边浏览器里打开给你标。
  4. 你每改一下都自动保存；点「确认标黄」后，在项目文件夹里写出：
       标黄结果.json      —— AI 读这个继续干活
       标黄逐字稿.docx    —— 带黄色高亮的 Word 版，你可以直接用 Word 打开
  5. 确认后页面接着让你选风格（文字多/动画多 → 样图 → 就这个/换一个/用上次那个），
     读 Agent 写的 风格排名.json，自己调 render.py 出样图，选好写出 风格选择.json
"""
import argparse, json, os, re, socket, sys, time, urllib.parse, zipfile, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "highlighter.html")


# ---------- 读逐字稿 ----------
def read_docx(path):
    blocks = []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    for p in root.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        sval = (style.get(W + "val") or "") if style is not None else ""
        is_head = bool(re.search(r"heading|title|标题", sval, re.I))
        text, hl, start = "", [], None
        for r in p.iter(W + "r"):
            rpr = r.find(W + "rPr")
            h = rpr.find(W + "highlight") if rpr is not None else None
            on = h is not None and (h.get(W + "val") or "none") != "none"
            piece = ""
            for c in r:
                if c.tag == W + "t":
                    piece += c.text or ""
                elif c.tag == W + "tab":
                    piece += " "
            if not piece:
                continue
            if on and start is None:
                start = len(text)
            if not on and start is not None:
                hl.append([start, len(text)]); start = None
            text += piece
        if start is not None:
            hl.append([start, len(text)])
        if not text.strip():
            continue
        blocks.append({"type": "h" if is_head else "p", "text": text, "hl": [] if is_head else hl, "sug": []})
    return blocks


def read_text(path):
    blocks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = line.rstrip("\n")
            if not t.strip():
                continue
            m = re.match(r"^#+\s*(.*)", t)
            blocks.append({"type": "h", "text": m.group(1)} if m else {"type": "p", "text": t, "hl": [], "sug": []})
    return blocks


def _ts(t):
    h, m, rest = t.strip().split(":")
    sec, ms = (rest.replace(".", ",").split(",") + ["0"])[:2]
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms.ljust(3, "0")[:3]) / 1000


def _label(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}" if sec < 3600 else f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def read_srt(path, gap=1.0, max_len=120):
    """剪映导出的 SRT：相邻字幕停顿不到 gap 秒就并成一段，每段不超过 max_len 字。"""
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read().replace("\r\n", "\n")
    cues = []
    for chunk in re.split(r"\n\s*\n", raw.strip()):
        lines = [l for l in chunk.split("\n") if l.strip()]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None:
            continue
        a, b = lines[ti].split("-->")
        text = "".join(l.strip() for l in lines[ti + 1:])
        if text:
            cues.append((_ts(a), _ts(b.split()[0]), text))
    blocks, cur, last_end = [], None, None
    for t0, t1, text in cues:
        if cur is None or (t0 - last_end) >= gap or len(cur["text"]) + len(text) > max_len:
            cur = {"type": "p", "text": "", "hl": [], "sug": [], "cues": [], "time": _label(t0)}
            blocks.append(cur)
        elif cur["text"]:
            cur["text"] += " "
        s0 = len(cur["text"]); cur["text"] += text
        cur["cues"].append([s0, len(cur["text"]), round(t0, 3), round(t1, 3)])
        last_end = t1
    return blocks


def apply_suggestions(blocks, sugs):
    for s in sugs:
        s = s.strip()
        if not s:
            continue
        for b in blocks:
            if b["type"] != "p":
                continue
            i = b["text"].find(s)
            if i >= 0:
                b["sug"].append([i, i + len(s)])
                b["hl"].append([i, i + len(s)])
                break
        else:
            print(f"[提示] 建议句没在逐字稿里找到，已跳过：{s[:30]}", file=sys.stderr)


# ---------- 写出带高亮的 Word ----------
def write_docx(path, title, blocks, ranges):
    def run(t, hl=False, bold=False, size=None):
        props = '<w:rFonts w:eastAsia="Microsoft YaHei"/>'
        if bold: props += "<w:b/>"
        if size: props += f'<w:sz w:val="{size}"/>'
        if hl: props += '<w:highlight w:val="yellow"/>'
        return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'

    body = [f"<w:p>{run(title, bold=True, size=36)}</w:p>"]
    pi = 0
    for b in blocks:
        if b["type"] == "h":
            body.append(f"<w:p>{run(b['text'], bold=True, size=28)}</w:p>")
            continue
        t, rs, out, pos = b["text"], (ranges[pi] if pi < len(ranges) else []), [], 0
        for s, e in sorted(rs):
            if s > pos: out.append(run(t[pos:s]))
            out.append(run(t[s:e], hl=True)); pos = e
        if pos < len(t): out.append(run(t[pos:]))
        body.append("<w:p>" + "".join(out) + "</w:p>")
        pi += 1
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + "".join(body) + "</w:body></w:document>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>")
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    os.replace(tmp, path)


# ---------- 本机网页 ----------
def free_port(want):
    for p in [want] + list(range(want + 1, want + 50)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p)); return p
            except OSError:
                continue
    raise SystemExit("找不到空闲端口")



# ---------------- 选风格（标黄确认后，页面上点一下就行） ----------------
class StyleFlow:
    """读 Agent 写好的 风格排名.json，用这期真句子出样图；处理「就这个 / 换一个 / 用上次那个」。"""
    def __init__(self, out_dir):
        self.dir = out_dir
        self.rank_path = os.path.join(out_dir, "风格排名.json")
        self.choice_path = os.path.join(out_dir, "风格选择.json")
        self.result_path = os.path.join(out_dir, "标黄结果.json")
        self.img_dir = os.path.join(out_dir, "风格样图")
        self.lock = threading.Lock()
        self.st = {"phase": "mode", "mode": None, "cards": [], "shown": [], "msg": "", "chosen": None, "last": None}
        if os.path.exists(self.choice_path):
            try:
                c = json.load(open(self.choice_path, encoding="utf-8"))
                if c.get("confirmed"):
                    self.st.update(phase="done", mode=c.get("mode"), chosen=c)
            except Exception:
                pass

    def _tools(self):
        import importlib
        sys.path.insert(0, HERE)
        return importlib.import_module("render"), importlib.import_module("styles_tool")

    def _ranking(self):
        if not os.path.exists(self.rank_path):
            return None
        d = json.load(open(self.rank_path, encoding="utf-8"))
        return d

    def _highlights(self):
        try:
            return json.load(open(self.result_path, encoding="utf-8")).get("result", [])
        except Exception:
            return []

    def _pick_sentence(self, style, rk):
        if rk.get("sample") and rk["sample"].get("text"):
            return rk["sample"]
        hs = self._highlights()
        if not hs:
            return {"no": "", "text": style.get("sample_text", ""), "time": "", "dur": 3}
        def good(h):
            t = h.get("text", ""); n = len(t); sc = 0
            if style.get("layout") == "numbers": sc += 50 * bool(re.search(r"\d", t))
            if style.get("layout") == "tool": sc += 30 * bool(re.search(r"[A-Za-z]", t))
            if style.get("layout") == "principle": sc += 20 * bool(re.search(r"[，,；;]|就是|所以|然后", t))
            sc += 20 - abs(n - 18)
            return sc
        h = max(hs, key=good)
        st, en = h.get("startTime"), h.get("endTime")
        dur = 3.0
        if isinstance(st, (int, float)) and isinstance(en, (int, float)) and en > st:
            dur = max(2.0, min(4.0, en - st))
        tm = ""
        if isinstance(st, (int, float)):
            tm = "%02d:%02d" % (int(st) // 60, int(st) % 60)
        return {"no": h.get("no", ""), "text": h.get("text", ""), "time": tm, "dur": dur}

    def _diff(self, a, b):
        """一句话说清 b 跟 a 哪里不同。"""
        out = []
        lum = lambda c: sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) / 765
        try:
            la, lb = lum(a["palette"]["bg"]), lum(b["palette"]["bg"])
            if abs(la - lb) > 0.3: out.append("深色底" if lb < la else "浅色底")
        except Exception:
            pass
        if a.get("surface", {}).get("kind") != b.get("surface", {}).get("kind"):
            out.append({"glass": "毛玻璃卡片", "paper": "纸片质感", "flat": "纯色块", "outline": "细线框"}.get(b.get("surface", {}).get("kind"), ""))
        fa, fb = a.get("type", {}).get("head"), b.get("type", {}).get("head")
        if fa != fb: out.append("宋体标题" if fb == "serif" else "黑体标题")
        sa, sb = a.get("motion", {}).get("speed", 1), b.get("motion", {}).get("speed", 1)
        if sb - sa > 0.15: out.append("动得更快")
        elif sa - sb > 0.15: out.append("动得更慢更稳")
        return "跟上一个比：" + "、".join(x for x in out if x) if out else "跟上一个是同一类，换了配色"

    def _pick_three(self, R):
        """挑 3 句不同版式的原话做样图：同一个风格碰上不同内容是什么样，一眼看清。"""
        rk = self._ranking() or {}
        if rk.get("samples"):
            return rk["samples"][:3]
        out, seen = [], set()
        hs = self._highlights()
        for h in sorted(hs, key=lambda h: -min(len(h.get("text", "")), 26)):
            lay = R.pick_layout(h.get("text", ""))
            if lay in seen: continue
            seen.add(lay); st, en = h.get("startTime"), h.get("endTime")
            dur = max(2.0, min(4.0, en - st)) if isinstance(st, (int, float)) and isinstance(en, (int, float)) and en > st else 3.0
            tm = "%02d:%02d" % (int(st) // 60, int(st) % 60) if isinstance(st, (int, float)) else ""
            out.append({"no": h.get("no", ""), "text": h.get("text", ""), "time": tm, "dur": dur, "layout": lay})
            if len(out) == 3: break
        for h in hs:                      # 不够 3 种版式就用剩下的句子补
            if len(out) >= 3: break
            if not any(o["text"] == h.get("text") for o in out):
                out.append({"no": h.get("no", ""), "text": h.get("text", ""), "time": "", "dur": 3.0, "layout": R.pick_layout(h.get("text", ""))})
        return out or [{"no": "", "text": "复利就是利滚利，本金生利息，利息再生利息", "time": "", "dur": 3.0, "layout": "principle"}]

    def _render_card(self, row, why):
        R, T = self._tools()
        sd = R.find_style(row["path"]); style = json.load(open(os.path.join(sd, "style.json"), encoding="utf-8"))
        rk = self._ranking() or {}
        os.makedirs(self.img_dir, exist_ok=True)
        imgs = []
        for i, sen in enumerate(self._pick_three(R)):
            label = (f'{sen["no"]} · {sen["time"]}：{sen["text"]}' if sen.get("no") else sen["text"])
            img = f'{style["id"]}_{self.st["mode"]}_{i+1}.png'
            R.render(str(sd), sen["text"], sen.get("dur", 3), rk.get("aspect", "9:16"), rk.get("size"), 30, self.st["mode"] or "anim",
                     None, None, os.path.join(self.img_dir, img), False, label, sen.get("dur", 3) - 0.04, layout=sen.get("layout"))
            imgs.append({"img": "samples/" + img, "layout": R.LAYOUT_CN.get(sen.get("layout"), ""), "no": sen.get("no", "")})
        return {"id": style["id"], "name": style["name"], "category": style.get("vibe", ""), "why": why, "img": imgs[0]["img"], "imgs": imgs,
                "path": str(sd), "score": row.get("score"), "sentence": None, "_style": style}

    def _bg(self, fn):
        def run():
            try:
                fn()
            except Exception as e:
                with self.lock:
                    self.st.update(phase="error", msg="样图没出来：" + str(e)[:300] + "。回到对话里跟 AI 说一声。")
        threading.Thread(target=run, daemon=True).start()

    def _first(self):
        rk = self._ranking()
        rows = rk.get("ranking", [])
        if not rows:
            with self.lock: self.st.update(phase="error", msg="没有上架的风格。")
            return
        r = rows[0]
        why = r.get("why") or f'这期内容和「{r["name"]}」最搭：{r.get("vibe","")}。下面 3 张用的是你这期 3 句不同类型的原话。'
        card = self._render_card(r, why)
        with self.lock:
            self.st.update(phase="choose", cards=[card], shown=[r["id"]], msg="")

    def _next(self):
        rk = self._ranking(); rows = rk.get("ranking", [])
        rest = [r for r in rows if r["id"] not in self.st["shown"]][:2]
        if not rest:
            with self.lock: self.st.update(phase="choose", msg="上架的风格都给你看过了。想要新的：把参考图发到对话里，AI 帮你提炼一个。")
            return
        prev = self.st["cards"][0]["_style"] if self.st["cards"] else {}
        cards = []
        for r in rest:
            c = self._render_card(r, "")
            c["why"] = r.get("why") or self._diff(prev, c["_style"])
            cards.append(c)
        with self.lock:
            self.st.update(phase="choose", cards=cards, shown=self.st["shown"] + [r["id"] for r in rest], msg="")

    def _choose(self, card):
        R, T = self._tools()
        choice = {"confirmed": True, "style_id": card["id"], "name": card["name"], "path": card["path"], "mode": self.st["mode"],
                  "images": [os.path.join(self.dir, x["img"].replace("samples/", "风格样图/")) for x in card.get("imgs", [])],
                  "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        tmp = self.choice_path + ".tmp"
        json.dump(choice, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2); os.replace(tmp, self.choice_path)
        try:
            T.last(card["path"])          # 记下「上次那个」（只在本机）
        except SystemExit:
            pass
        with self.lock:
            self.st.update(phase="done", chosen=choice, msg="")
        print(f"[风格已选] {card['name']} → {self.choice_path}", flush=True)

    def state(self):
        with self.lock:
            st = dict(self.st)
        if st["phase"] == "waiting" and self._ranking():
            with self.lock:
                if self.st["phase"] == "waiting":
                    self.st["phase"] = "rendering"; self._bg(self._first)
            st = dict(self.st)
        try:
            R, T = self._tools()
            lp = T.LAST
            st["last"] = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else None
        except Exception:
            st["last"] = None
        st["cards"] = [{k: v for k, v in c.items() if k != "_style"} for c in st["cards"]]
        return st

    def act(self, d):
        a = d.get("act")
        with self.lock:
            busy = self.st["phase"] == "rendering"
        if busy:
            return
        if a == "mode":
            with self.lock:
                self.st.update(mode="text" if d.get("mode") == "text" else "anim", phase="waiting", cards=[], shown=[], msg="")
        elif a == "ok":
            card = next((c for c in self.st["cards"] if c["id"] == d.get("id")), None)
            if card: self._choose(card)
        elif a == "next":
            with self.lock: self.st["phase"] = "rendering"
            self._bg(self._next)
        elif a == "last":
            def go():
                R, T = self._tools()
                if not os.path.exists(T.LAST):
                    with self.lock: self.st.update(phase="choose", msg="还没有「上次」的记录：这是第一次选。")
                    return
                lp = json.load(open(T.LAST, encoding="utf-8"))
                c = self._render_card({"path": lp["path"], "id": lp["id"]}, "上次用的就是它")
                with self.lock: self.st["cards"] = [c]
                self._choose(c)
            with self.lock: self.st["phase"] = "rendering"
            self._bg(go)
        elif a == "reopen":
            with self.lock: self.st.update(phase="choose" if self.st["cards"] else "mode", chosen=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--suggest", help="AI 建议标黄的句子，JSON 字符串数组")
    ap.add_argument("--out", default=None, help="结果写到哪个文件夹（默认逐字稿所在文件夹）")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()

    src = os.path.abspath(a.transcript)
    low = src.lower()
    blocks = read_docx(src) if low.endswith(".docx") else read_srt(src) if low.endswith(".srt") else read_text(src)
    if a.suggest:
        with open(a.suggest, encoding="utf-8") as f:
            apply_suggestions(blocks, json.load(f))
    title = os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.abspath(a.out or os.path.dirname(src))
    os.makedirs(out_dir, exist_ok=True)
    state_path = os.path.join(out_dir, "标黄结果.json")
    docx_path = os.path.join(out_dir, "标黄逐字稿.docx")

    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read().replace("__DATA__", json.dumps({"title": title, "blocks": blocks}, ensure_ascii=False))
    lock = threading.Lock()
    flow = StyleFlow(out_dir)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                self.send(200, page, "text/html; charset=utf-8")
            elif path == "/api/style":
                self.send(200, json.dumps(flow.state(), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/samples/"):
                fp = os.path.join(flow.img_dir, os.path.basename(urllib.parse.unquote(path)))
                if os.path.exists(fp):
                    with open(fp, "rb") as f:
                        self.send(200, f.read(), "image/png")
                else:
                    self.send(404, "not found", "text/plain")
            elif path == "/api/state":
                if os.path.exists(state_path):
                    with open(state_path, encoding="utf-8") as f:
                        self.send(200, f.read(), "application/json; charset=utf-8")
                else:
                    self.send(200, "{}", "application/json; charset=utf-8")
            else:
                self.send(404, "not found", "text/plain")

        def do_POST(self):
            path = self.path.split("?")[0]
            n = int(self.headers.get("Content-Length", "0"))
            if path == "/api/style":
                try:
                    flow.act(json.loads(self.rfile.read(n).decode("utf-8")))
                except Exception as e:
                    return self.send(400, json.dumps({"ok": False, "err": str(e)}), "application/json")
                return self.send(200, json.dumps(flow.state(), ensure_ascii=False), "application/json; charset=utf-8")
            if path != "/api/save":
                return self.send(404, "not found", "text/plain")
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                return self.send(400, '{"ok":false}', "application/json")
            with lock:
                tmp = state_path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, state_path)
                if data.get("confirmed"):
                    write_docx(docx_path, title, blocks, data.get("ranges", []))
                    print(f"[已确认] 共 {data.get('count', 0)} 处标黄 → {state_path}", flush=True)
            self.send(200, '{"ok":true}', "application/json")

    port = free_port(a.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"标黄页面已启动：http://127.0.0.1:{port}/", flush=True)
    print(f"结果会写到：{out_dir}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
