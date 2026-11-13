#!/usr/bin/env python3
"""风格 DNA 和外部风格的工具。只用 Python 自带库 + ffmpeg + git。

  dna.py colors <参考图或视频> [--k 6]          程序量出主色（色值 + 占比 + 亮暗），比肉眼准
  dna.py cuts <参考视频>                          量出每 5 秒换几次画面（只有视频能量）
  dna.py license <GitHub 链接或本地文件夹>         下载到 ~/.broll-video-maker/imports/ 并判断许可证能不能用
  dna.py save <当期文件夹/风格草稿/xxx>            用户满意了：存进「我的风格」（~/lemo-my-styles/，和 Lemo 共用）
"""
import colorsys, datetime, json, os, pathlib, random, re, shutil, subprocess, sys

HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker'))
MINE = pathlib.Path(os.environ.get('LEMO_MY_STYLES', pathlib.Path.home() / 'lemo-my-styles'))

def need_ffmpeg():
    if not shutil.which('ffmpeg'): sys.exit('没找到 ffmpeg')

# ---------- 主色 ----------
def pixels(path, side=96):
    need_ffmpeg()
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-frames:v', '1', '-vf', f'scale={side}:{side}:flags=area',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    if not raw: sys.exit(f'读不了这张图：{path}')
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw) - 2, 3)]

def kmeans(px, k, iters=18, seed=7):
    rnd = random.Random(seed); cs = rnd.sample(px, k)
    for _ in range(iters):
        groups = [[] for _ in cs]
        for p in px:
            j = min(range(len(cs)), key=lambda i: (p[0] - cs[i][0]) ** 2 + (p[1] - cs[i][1]) ** 2 + (p[2] - cs[i][2]) ** 2)
            groups[j].append(p)
        cs = [tuple(sum(c[i] for c in g) / len(g) for i in range(3)) if g else cs[j] for j, g in enumerate(groups)]
    return [(c, len(g) / len(px)) for c, g in zip(cs, groups) if g]

def colors(path, k=6):
    res = sorted(kmeans(pixels(path), k), key=lambda x: -x[1])
    out = []
    for (r, g, b), share in res:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        out.append({'hex': '#%02X%02X%02X' % (round(r), round(g), round(b)), 'share': round(share, 3),
                    'lightness': round(l, 2), 'saturation': round(s, 2)})
    # 强调色常常只占一小块，会被大面积底色吞掉：单独把「鲜艳」的像素拿出来再聚一次
    px = pixels(path, 160)
    vivid = [q for q in px if (lambda h, l, s: s > 0.45 and 0.18 < l < 0.82)(*colorsys.rgb_to_hls(q[0] / 255, q[1] / 255, q[2] / 255))]
    accents = []
    if len(vivid) > 20:
        for (r, g, b), share in sorted(kmeans(vivid, min(3, len(vivid) // 10)), key=lambda x: -x[1]):
            accents.append({'hex': '#%02X%02X%02X' % (round(r), round(g), round(b)), 'share_of_frame': round(share * len(vivid) / len(px), 3)})
    # 建议：占比最大的当底色；和底色反差最大的当正文色；鲜艳色里占比最大的当强调色
    bg = out[0]; acc = {'hex': accents[0]['hex']} if accents else max(out[1:] or out, key=lambda c: c['saturation'] * (1 - c['share']))
    ink = max(out, key=lambda c: abs(c['lightness'] - bg['lightness']))
    return {'colors': out, 'accents': accents, 'suggest': {'bg': bg['hex'], 'ink': ink['hex'], 'accent': acc['hex']},
            'note': '色值是程序量的；只用来定配色关系，不照搬原图的画面'}

def cuts(path):
    need_ffmpeg()
    r = subprocess.run(['ffmpeg', '-i', path, '-filter:v', "select='gt(scene,0.32)',showinfo", '-f', 'null', '-'], capture_output=True, text=True)
    ts = [float(x) for x in re.findall(r'pts_time:([\d.]+)', r.stderr)]
    d = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else (ts[-1] if ts else 0)
    return {'duration': round(dur, 2), 'cuts': len(ts), 'cuts_per_5s': round(len(ts) / dur * 5, 2) if dur else None}

# ---------- 许可证 ----------
OK = {'MIT': r'\bMIT License\b|Permission is hereby granted, free of charge', 'Apache-2.0': r'Apache License,? Version 2\.0',
      'BSD': r'BSD (2|3)-Clause|Redistribution and use in source and binary forms', 'CC0': r'CC0|No Copyright', 'ISC': r'\bISC License\b',
      'CC-BY-4.0': r'Attribution 4\.0 International(?! .*NonCommercial)'}
WARN = {'CC-BY-NC': r'NonCommercial|BY-NC', 'GPL': r'GNU (AFFERO |LESSER )?GENERAL PUBLIC LICENSE', 'CC-BY-SA': r'ShareAlike|BY-SA'}

def fetch(src):
    p = pathlib.Path(src).expanduser()
    if p.exists(): return p
    m = re.match(r'(?:https?://)?github\.com/([^/\s]+)/([^/\s#?]+)', src)
    if not m: sys.exit('只认 GitHub 链接（github.com/作者/仓库）或本地文件夹')
    owner, repo = m.group(1), m.group(2).removesuffix('.git')
    dst = HOME / 'imports' / f'{owner}__{repo}'
    if dst.exists():
        subprocess.run(['git', '-C', str(dst), 'pull', '--quiet', '--depth', '1'], capture_output=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(['git', 'clone', '--quiet', '--depth', '1', f'https://github.com/{owner}/{repo}.git', str(dst)], capture_output=True, text=True)
        if r.returncode: sys.exit(f'下载失败：{r.stderr.strip()[-300:]}')
    return dst

def license_check(src):
    d = fetch(src)
    files = [f for f in d.iterdir() if re.match(r'(LICEN[CS]E|COPYING)', f.name, re.I)] + list((d / 'LICENSES').glob('*')) if (d / 'LICENSES').exists() else \
            [f for f in d.iterdir() if re.match(r'(LICEN[CS]E|COPYING)', f.name, re.I)]
    text = '\n'.join(f.read_text(encoding='utf-8', errors='ignore') for f in files if f.is_file())
    if not text:
        readme = next((f for f in d.iterdir() if f.name.lower().startswith('readme')), None)
        sec = re.search(r'#+\s*licen[cs]e.*?\n(.+?)(\n#|\Z)', readme.read_text(encoding='utf-8', errors='ignore'), re.S | re.I) if readme else None
        text = sec.group(1) if sec else ''
    found_ok = [k for k, r in OK.items() if re.search(r, text, re.I)]
    found_warn = [k for k, r in WARN.items() if re.search(r, text, re.I)]
    if not text.strip():
        verdict, why = '不能用', '没写许可证：默认作者保留所有权利，公开不等于免费'
    elif found_warn and not found_ok:
        verdict, why = '有限制', '有 ' + '、'.join(found_warn) + ' 条款：NC 不能商用，GPL / SA 要求改动后用同样方式公开。只能在用户自己电脑上读来做片子，不能存进 skill'
    elif found_warn:
        verdict, why = '分块看', f'同时有 {"、".join(found_ok)} 和 {"、".join(found_warn)}：通常代码宽松、文档受限，要逐条看 LICENSE 原文'
    else:
        verdict, why = '可以用', f'{"、".join(found_ok)}：可以照它做，保留原作者署名'
    res = {'repo': str(src), 'local': str(d), 'license_files': [f.name for f in files], 'found': found_ok + found_warn, 'verdict': verdict, 'why': why}
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res

# ---------- 存进我的风格 ----------
def save(draft):
    d = pathlib.Path(draft)
    sj, md = d / 'style.json', d / 'STYLE.md'
    if not (sj.exists() and md.exists()): sys.exit('草稿文件夹里要有 style.json 和 STYLE.md')
    st = json.loads(sj.read_text(encoding='utf-8'))
    slug = re.sub(r'[^a-z0-9-]+', '-', (st.get('slug') or d.name).lower()).strip('-')
    dst = MINE / slug
    if dst.exists(): sys.exit(f'「我的风格」里已经有 {slug}，换个名字')
    shutil.copytree(d, dst, ignore=shutil.ignore_patterns('*.mp4', '_*'))
    st.update(slug=slug, created=st.get('created') or datetime.date.today().isoformat()); (dst / 'style.json').write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    idx = MINE / 'README.md'
    if not idx.exists(): idx.write_text('# 我的风格\n\n| 英文名 | 中文名 | slug | 基于 | 一句话 |\n|---|---|---|---|---|\n', encoding='utf-8')
    with idx.open('a', encoding='utf-8') as f:
        f.write(f"| {st.get('en','')} | {st.get('cn','')} | {slug} | {st.get('based_on','参考图')} | {st.get('line_cn','')} |\n")
    print(dst)

def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'): print(__doc__); return
    if a[0] == 'colors':
        k = int(a[a.index('--k') + 1]) if '--k' in a else 6
        print(json.dumps(colors(a[1], k), ensure_ascii=False, indent=1))
    elif a[0] == 'cuts': print(json.dumps(cuts(a[1]), ensure_ascii=False))
    elif a[0] == 'license': license_check(a[1])
    elif a[0] == 'save': save(a[1])
    else: print(__doc__)

if __name__ == '__main__':
    main()
