#!/usr/bin/env python3
"""逐字稿标黄 + 选风格 + 逐帧审稿 的本机页面（Claude 和 Codex 共用，只用 Python 自带库）。

用法：
  python3 highlight_server.py 字幕.srt [--suggest 建议.json] --out <用户的文件夹>/.broll [--folder <用户的文件夹>] [--port 8765]
  （也支持 .docx / .txt / .md）

页面从上到下：
  1. 仿 Word 标黄（AI 先标好建议），顶上一排 4 步：标黄 → 文字 / 动画 → 视频格式 → 风格从哪来（AI 帮我挑 / 我的素材库 / 我的 GitHub 库）→「开始做」
  2. 选风格：按来源分（参考图 DNA 提取 / GitHub / 内置风格库 / 我的素材库），每个风格「就这个 / 备选 / 加入素材库」；备选可以并排比
  3. 审稿：分镜墙，一张逐帧图配一句口播，点开放大一张张翻；只有「没问题，出片」，要改在对话里说编号
  4. 成片：小卡片，点开播放；「没问题，放进文件夹」才复制进 <用户的文件夹>/B-roll成片/
页面上每点一下都写进 <工作文件夹>/事件.jsonl ——这就是「门铃」：AI 在后台跑 wait_page.py 等它，一点就醒，不用回对话发消息。
AI 往工作文件夹写 风格排名.json / 逐帧审稿.json / 成片.json，页面每 1.5 秒自己刷新。
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


def read_srt(path, gap=1.0, max_len=120, breaks=None):
    """剪映导出的 SRT 合成段落。
    breaks（AI 按意思给的分段点：每段第一条字幕是第几条，从 1 数）有就按它分——换一个意思才换段；
    没有才退回老办法：相邻字幕停顿不到 gap 秒就并成一段，每段不超过 max_len 字。"""
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
    bset = {int(x) for x in breaks} if breaks else None
    for n, (t0, t1, text) in enumerate(cues, 1):
        new = cur is None or (n in bset if bset else ((t0 - last_end) >= gap or len(cur["text"]) + len(text) > max_len))
        if new:
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
        for r in sorted(rs):
            s, e = r[0], r[1]   # 页面存的是 [起, 止, 第几处]
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


def jload(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def jsave(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


HOME = os.environ.get("BROLL_HOME", os.path.join(os.path.expanduser("~"), ".broll-video-maker"))
MINE = os.environ.get("LEMO_MY_STYLES", os.path.join(os.path.expanduser("~"), "lemo-my-styles"))
LIB = os.environ.get("LEMO_OPUSCAR_HOME", os.path.join(os.path.expanduser("~"), "lemo-opuscar"))
GH = os.path.join(HOME, "github")   # 我的 GitHub 库：ghlib.py 存的仓库链接 + 风格描述 + 预览图
SIZES = {"9:16": "1080x1920", "16:9": "1920x1080", "3:4": "1080x1440", "1:1": "1080x1080"}
OUT_DIR = "B-roll成片"


class Project:
    """页面和 AI 之间的「门铃」：页面上每点一下，就往 事件.jsonl 记一行；AI 在后台跑 wait_page.py 等这个文件变长，一变就被叫醒。
    AI 往工作文件夹里写：风格排名.json（3×3 样图）、逐帧审稿.json（审稿表）、成片.json（交付）；页面每 1.5 秒读一次。"""

    def __init__(self, work, folder):
        self.work, self.folder = work, folder
        self.lock = threading.Lock()
        self.p = lambda name: os.path.join(work, name)

    # ---- 门铃 ----
    def ring(self, act, **kw):
        ev = {"t": round(time.time(), 3), "act": act}
        ev.update(kw)
        with open(self.p("事件.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        print(f"[页面] {act} {json.dumps(kw, ensure_ascii=False)}", flush=True)

    # ---- 页面要的全部状态 ----
    def state(self):
        st = {"mode": (jload(self.p("模式.json"), {}) or {}).get("mode"),
              "format": jload(self.p("格式.json")), "source": jload(self.p("风格来源.json")),
              "shortlist": jload(self.p("备选.json"), []) or []}
        hl = jload(self.p("标黄结果.json"), {}) or {}
        st["confirmed"], st["count"] = bool(hl.get("confirmed")), hl.get("count", 0)
        st["mine"] = self.mine()
        st["github"] = self.github()
        mine_slugs = {m["slug"] for m in st["mine"]}
        rank = jload(self.p("风格排名.json"), {}) or {}
        rows = []
        for c in rank.get("candidates", []):
            cells = []
            for x in (c.get("samples") or [])[:3]:
                cells.append("files/" + urllib.parse.quote(x) if x and os.path.exists(self.p(x)) else None)
            while len(cells) < 3:
                cells.append(None)
            rows.append({"slug": c.get("slug"), "name": c.get("name", c.get("slug")), "source": c.get("source", "lemo"),
                         "repo": c.get("repo", ""), "why": c.get("why", ""), "look": c.get("look", ""), "cells": cells,
                         "ready": all(cells), "in_mine": c.get("slug") in mine_slugs})
        st["styles"] = {"sentences": rank.get("sentences", []), "rows": rows, "drawing": rank.get("drawing", False),
                        "note": rank.get("note", "")}
        st["chosen"] = jload(self.p("风格选择.json"))
        rv = jload(self.p("逐帧审稿.json"), {}) or {}
        marks = jload(self.p("审稿结果.json"), {}) or {}
        rrows = []
        for r in rv.get("rows", []):
            frames = []
            for f in r.get("frames", []):
                f = {"img": f} if isinstance(f, str) else dict(f)
                if f.get("img") and os.path.exists(self.p(f["img"])):
                    f["src"] = "files/" + urllib.parse.quote(f["img"])
                    frames.append(f)
            rrows.append(dict(r, frames=frames))
        st["review"] = {"rows": rrows, "size": rv.get("size", "1080x1920"), "note": rv.get("note", ""), "approved": bool(marks.get("_all"))}
        out = jload(self.p("成片.json"), {}) or {}
        clips = []
        for c in out.get("clips", []):
            fp = c.get("file", "")
            if os.path.exists(self.p(fp)):
                clips.append(dict(c, url="files/" + urllib.parse.quote(fp)))
            elif os.path.exists(os.path.join(self.folder, fp)):   # 旧版写法：直接放在用户的文件夹里
                clips.append(dict(c, url="out/" + urllib.parse.quote(fp)))
        st["outputs"] = {"clips": clips, "rendering": out.get("rendering", False), "note": out.get("note", ""),
                         "exported": bool(out.get("exported")), "folder": os.path.join(os.path.basename(self.folder), OUT_DIR)}
        return st

    def mine(self):
        out = []
        if os.path.isdir(MINE):
            for d in sorted(os.listdir(MINE)):
                sj = jload(os.path.join(MINE, d, "style.json"))
                if not sj:
                    continue
                thumbs = [f"my/{urllib.parse.quote(d)}/samples/{urllib.parse.quote(x)}" for x in sorted(os.listdir(os.path.join(MINE, d, "samples")))[:3]] \
                    if os.path.isdir(os.path.join(MINE, d, "samples")) else []
                out.append({"slug": sj.get("slug", d), "name": sj.get("cn") or sj.get("name") or d, "thumbs": thumbs,
                            "style_md": sj.get("ref_style_md") or os.path.join(MINE, d, "STYLE.md"), "source": "mine",
                            "from": sj.get("source") or "dna", "repo": sj.get("repo", ""), "created": sj.get("created", ""),
                            "uses": sj.get("uses", 0)})
        out.sort(key=lambda m: m.get("created", ""), reverse=True)
        return out

    def github(self):
        out = []
        if os.path.isdir(GH):
            for d in sorted(os.listdir(GH)):
                rj = jload(os.path.join(GH, d, "repo.json"))
                if not rj:
                    continue
                pv = os.path.join(GH, d, "previews")
                thumbs = [f"ghlib/{urllib.parse.quote(d)}/previews/{urllib.parse.quote(x)}" for x in sorted(os.listdir(pv))[:3]] if os.path.isdir(pv) else []
                out.append(dict(rj, key=d, thumbs=thumbs))
        out.sort(key=lambda r: r.get("saved", ""), reverse=True)
        return out

    # ---- 页面上的每一下 ----
    def act(self, d):
        a = d.get("act")
        with self.lock:
            if a == "mode":
                m = "text" if d.get("mode") == "text" else "anim"
                jsave(self.p("模式.json"), {"mode": m}); self.ring("mode", mode=m)
            elif a == "format":
                asp = d.get("aspect") if d.get("aspect") in SIZES else "9:16"
                fm = {"aspect": asp, "size": SIZES[asp], "quality": "4k" if d.get("quality") == "4k" else "1080p"}
                jsave(self.p("格式.json"), fm); self.ring("format", **fm)
            elif a == "source":
                kind = d.get("kind") if d.get("kind") in ("ai", "mine", "github") else "ai"
                src = {"kind": kind}
                if kind == "mine":
                    m = next((x for x in self.mine() if x["slug"] == d.get("slug")), None)
                    if not m:
                        return
                    src.update(slug=m["slug"], name=m["name"])
                    self.choose(m)          # 用素材库里的风格 = 直接选定，跳过「选风格」
                elif kind == "github":
                    r = next((x for x in self.github() if x.get("repo") == d.get("repo")), None)
                    if not r:
                        return
                    src.update(repo=r["repo"], url=r.get("url", ""), name=r.get("name", r["repo"]), local=r.get("local", ""))
                if kind != "mine" and (jload(self.p("风格来源.json"), {}) or {}).get("kind") == "mine":
                    try:
                        os.remove(self.p("风格选择.json"))
                    except OSError:
                        pass
                jsave(self.p("风格来源.json"), src); self.ring("source", **src)
            elif a == "shortlist":
                sl = [x for x in (jload(self.p("备选.json"), []) or []) if x != d.get("slug")]
                if d.get("on"):
                    sl.append(d.get("slug"))
                jsave(self.p("备选.json"), sl); self.ring("shortlist", slug=d.get("slug"), on=bool(d.get("on")))
            elif a == "export":
                n = self.export()
                if n:
                    self.ring("export", count=n)
            elif a == "pick":
                rank = {c.get("slug"): c for c in (jload(self.p("风格排名.json"), {}) or {}).get("candidates", [])}
                c = rank.get(d.get("slug")) or next((x for x in self.mine() if x["slug"] == d.get("slug")), None)
                if not c:
                    return
                self.choose(c)
            elif a == "more":
                self.ring("more")
            elif a == "save_style":
                self.ring("save_style", slug=self.save_style(d.get("slug")))
            elif a == "review":
                marks = jload(self.p("审稿结果.json"), {}) or {}
                marks[d.get("no")] = {"ok": bool(d.get("ok")), "note": d.get("note", "")}
                marks.pop("_all", None)
                jsave(self.p("审稿结果.json"), marks); self.ring("review", no=d.get("no"), ok=bool(d.get("ok")), note=d.get("note", ""))
            elif a == "approve_all":
                marks = jload(self.p("审稿结果.json"), {}) or {}
                rv = jload(self.p("逐帧审稿.json"), {}) or {}
                bad = [k for k, v in marks.items() if k != "_all" and not v.get("ok")]
                for r in rv.get("rows", []):
                    if r.get("no") not in bad:
                        marks[r.get("no")] = {"ok": True, "note": ""}
                marks["_all"] = not bad
                jsave(self.p("审稿结果.json"), marks); self.ring("approve_all", changes=bad)
            elif a == "confirm":
                self.ring("confirm", count=d.get("count"))

    def choose(self, c):
        mode = (jload(self.p("模式.json"), {}) or {}).get("mode")
        choice = {"confirmed": True, "slug": c["slug"], "name": c.get("name", c["slug"]), "source": c.get("source", "lemo"),
                  "style_md": c.get("style_md", ""), "mode": mode, "samples": c.get("samples", []), "repo": c.get("repo", ""),
                  "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        jsave(self.p("风格选择.json"), choice)
        sjp = os.path.join(MINE, c["slug"], "style.json")
        if c.get("source") == "mine" and os.path.exists(sjp):   # 素材库里记一下用过几次
            sj = jload(sjp, {}) or {}
            sj["uses"] = int(sj.get("uses", 0)) + 1
            jsave(sjp, sj)
        os.makedirs(HOME, exist_ok=True)
        jsave(os.path.join(HOME, "last.json"), {k: choice[k] for k in ("slug", "name", "source", "style_md")})
        self.ring("pick", slug=c["slug"], name=choice["name"])

    def export(self):
        """「没问题，放进文件夹」：把 <工作>/成片/ 里的视频复制进 <用户的文件夹>/B-roll成片/。"""
        out = jload(self.p("成片.json"), {}) or {}
        dst = os.path.join(self.folder, OUT_DIR)
        n = 0
        for c in out.get("clips", []):
            src = self.p(c.get("file", ""))
            if not os.path.isfile(src):
                continue
            os.makedirs(dst, exist_ok=True)
            with open(src, "rb") as fi, open(os.path.join(dst, os.path.basename(src)), "wb") as fo:
                fo.write(fi.read())
            n += 1
        if n:
            out["exported"] = True
            jsave(self.p("成片.json"), out)
        return n

    def save_style(self, slug=None):
        """「加入素材库」：选风格页上任何一个风格都能存（带它的 3 张样图）；不给 slug 就存这期选定的。"""
        rank = {c.get("slug"): c for c in (jload(self.p("风格排名.json"), {}) or {}).get("candidates", [])}
        c = rank.get(slug) if slug else None
        if not c:
            c = jload(self.p("风格选择.json"))
        if not c:
            return None
        slug = re.sub(r"[^a-z0-9-]+", "-", str(c.get("slug", "style")).lower()).strip("-") or "style"
        dst = os.path.join(MINE, slug)
        os.makedirs(os.path.join(dst, "samples"), exist_ok=True)
        for i, x in enumerate(c.get("samples", [])[:3]):
            if os.path.exists(self.p(x)):
                with open(self.p(x), "rb") as fi, open(os.path.join(dst, "samples", f"{i + 1}.png"), "wb") as fo:
                    fo.write(fi.read())
        md = os.path.expanduser(c.get("style_md", ""))
        mine_src = c.get("source") in ("mine", "dna") and os.path.exists(md)
        if mine_src and os.path.abspath(md) != os.path.abspath(os.path.join(dst, "STYLE.md")):
            with open(md, encoding="utf-8") as fi, open(os.path.join(dst, "STYLE.md"), "w", encoding="utf-8") as fo:
                fo.write(fi.read())
        elif not mine_src:
            # Lemo / GitHub 的风格说明不复制，只记住在哪（作者的授权只让在本机读）
            with open(os.path.join(dst, "STYLE.md"), "w", encoding="utf-8") as fo:
                fo.write(f"# {c.get('name', slug)}\n\n> 收藏自{ {'lemo': '内置风格库', 'github': 'GitHub'}.get(c.get('source'), '')}，完整说明在：{md}\n")
        old = jload(os.path.join(dst, "style.json"), {}) or {}
        sj = {"slug": slug, "cn": c.get("name", slug), "source": c.get("source"), "repo": c.get("repo", ""),
              "created": old.get("created") or time.strftime("%Y-%m-%d"), "uses": old.get("uses", 0)}
        if not mine_src:
            sj["ref_style_md"] = md
        jsave(os.path.join(dst, "style.json"), sj)
        return slug


PLAYER = """<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#141413;overflow:hidden;height:100%;width:100%}
#w{position:absolute;left:50%;top:50%;transform-origin:0 0}iframe{border:0;display:block}
#msg{position:absolute;inset:0;display:none;align-items:center;justify-content:center;padding:12px;color:#e8e6dc;font:13px/1.6 -apple-system,sans-serif;text-align:center}</style>
<div id="w"><iframe id="f" scrolling="no"></iframe></div><div id="msg">动画没加载出来（这一段的画图工具缺了）。<br>关键帧图是对的，可以先看左边；回对话说一声「动画打不开」就好。</div><script>
const q=new URLSearchParams(location.search),[W,H]=(q.get('s')||'1080x1920').split('x').map(Number),f=document.getElementById('f'),w=document.getElementById('w');
f.width=W;f.height=H;f.src='@film/'+q.get('p');
function fit(){const k=Math.min(innerWidth/W,innerHeight/H);w.style.transform=`scale(${k}) translate(-50%,-50%)`;}
addEventListener('resize',fit);fit();
f.onload=()=>{const g=f.contentWindow,t0=performance.now();
 setTimeout(()=>{try{if(typeof g.render!=='function'){document.getElementById('msg').style.display='flex';}}catch(e){}},6000);
 (function loop(){try{if(g.READY!==false&&typeof g.render==='function'){const d=Number(g.DUR)||3;g.render(((performance.now()-t0)/1000)%d);}}catch(e){}
 requestAnimationFrame(loop);})();};
</script>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--suggest", help="AI 建议标黄的句子，JSON 字符串数组")
    ap.add_argument("--out", default=None, help="工作文件夹（中间文件都放这里，建议用 <用户的文件夹>/.broll）")
    ap.add_argument("--folder", default=None, help="用户的文件夹（成片放这里；默认是工作文件夹的上一层）")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--paras", default=None, help="AI 按意思给的分段点 JSON：每段第一条字幕是第几条（从 1 数）。不填就找 <工作文件夹>/分段.json")
    ap.add_argument("--check-paras", action="store_true", help="只打印每两段的交界处（上一段结尾｜下一段开头），给 AI 自查有没有把一句话切成两半，不开页面")
    a = ap.parse_args()

    src = os.path.abspath(a.transcript)
    low = src.lower()
    pfile = a.paras or os.path.join(os.path.abspath(a.out or os.path.dirname(src)), "分段.json")
    breaks = None
    if low.endswith(".srt") and os.path.exists(pfile):
        try:
            breaks = [int(x) for x in json.load(open(pfile, encoding="utf-8"))]
        except Exception as e:
            print(f"[提示] 分段.json 读不了（{e}），先按停顿分段", file=sys.stderr)
    blocks = read_docx(src) if low.endswith(".docx") else read_srt(src, breaks=breaks) if low.endswith(".srt") else read_text(src)
    if a.check_paras:
        ps = [b for b in blocks if b["type"] == "p"]
        print(f"共 {len(ps)} 段（{'按分段.json' if breaks else '没有分段.json，按停顿分的'}）")
        for i, b in enumerate(ps, 1):
            print(f"第{i}段 {b.get('time', '')}  {len(b['text'])} 字  开头：{b['text'][:18]}")
        print("\n—— 交界处（｜左边是上一段结尾，右边是下一段开头；读起来是同一句话就是切错了，把分段点挪开）——")
        for i in range(1, len(ps)):
            print(f"第{i}/{i + 1}段：…{ps[i - 1]['text'][-16:]} ｜ {ps[i]['text'][:16]}…")
        return
    if a.suggest:
        with open(a.suggest, encoding="utf-8") as f:
            apply_suggestions(blocks, json.load(f))
    title = os.path.splitext(os.path.basename(src))[0]
    work = os.path.abspath(a.out or os.path.dirname(src))
    folder = os.path.abspath(a.folder or os.path.dirname(work))
    os.makedirs(work, exist_ok=True)
    state_path = os.path.join(work, "标黄结果.json")
    docx_path = os.path.join(work, "标黄逐字稿.docx")

    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read().replace("__DATA__", json.dumps({"title": title, "blocks": blocks}, ensure_ascii=False))
    lock = threading.Lock()
    proj = Project(work, folder)
    BH = HOME
    roots = {"files/": work, "out/": folder, "my/": MINE, "ghlib/": GH, "@film/": work,
             "@fonts/": os.path.join(BH, "fonts"), "@kits/": os.path.join(BH, "kits")}

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

        def file(self, base, rel):
            fp = os.path.normpath(os.path.join(base, urllib.parse.unquote(rel)))
            if not fp.startswith(os.path.normpath(base)) or not os.path.isfile(fp):
                return self.send(404, "not found", "text/plain")
            ext = os.path.splitext(fp)[1].lower()
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".jpeg": "image/jpeg", ".mp4": "video/mp4", ".html": "text/html; charset=utf-8",
                     ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
                     ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf", ".wasm": "application/wasm"}.get(ext, "application/octet-stream")
            with open(fp, "rb") as f:
                self.send(200, f.read(), ctype)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self.send(200, page, "text/html; charset=utf-8")
            if path == "/api/all":
                return self.send(200, json.dumps(proj.state(), ensure_ascii=False), "application/json; charset=utf-8")
            if path == "/api/state":
                return self.send(200, open(state_path, encoding="utf-8").read() if os.path.exists(state_path) else "{}", "application/json; charset=utf-8")
            if path == "/player":
                return self.send(200, PLAYER, "text/html; charset=utf-8")
            for pre, base in roots.items():
                if path.startswith("/" + pre):
                    return self.file(base, path[len(pre) + 1:])
            # 画面页里 /core/lib.js 这类绝对路径：从 Lemo 风格库提供（和 render.py 一样）
            return self.file(LIB, path.lstrip("/"))

        def do_POST(self):
            path = self.path.split("?")[0]
            n = int(self.headers.get("Content-Length", "0"))
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except Exception:
                return self.send(400, '{"ok":false}', "application/json")
            if path == "/api/act":
                proj.act(data)
                return self.send(200, json.dumps(proj.state(), ensure_ascii=False), "application/json; charset=utf-8")
            if path != "/api/save":
                return self.send(404, "not found", "text/plain")
            with lock:
                was = (jload(state_path, {}) or {}).get("confirmed")
                jsave(state_path, data)
                if data.get("confirmed"):
                    write_docx(docx_path, title, blocks, data.get("ranges", []))
                    if not was:
                        proj.ring("confirm", count=data.get("count", 0))
            self.send(200, '{"ok":true}', "application/json")

    port = free_port(a.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"标黄页面已启动：http://127.0.0.1:{port}/", flush=True)
    print(f"工作文件夹：{work}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
