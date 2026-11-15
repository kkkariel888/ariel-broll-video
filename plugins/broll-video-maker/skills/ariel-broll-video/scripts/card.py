#!/usr/bin/env python3
"""风格要点卡：从风格说明（STYLE.md）里抽出画「一张静态样图」要的几节，不花 token，一秒出。

样图子任务只读这张卡（几 KB），不读整本风格说明、不写画图工具，所以 9 张图能同时、很快地画完。
留下：本质 / 材质与渲染 / 配色 / 字体 / 常用手法 / 坑；去掉：动效、镜头、声音、变化范围（静态样图用不上，第 5 步做动画时再读原文）。

  card.py <STYLE.md> [<STYLE.md> ...] --out <文件夹>     每个风格写 <文件夹>/<slug>.md，打印「slug → 路径 · 多少字」
  card.py <STYLE.md> --print                            直接打印到屏幕

slug 取 STYLE.md 所在文件夹的名字。没有分节标题的说明（参考图 DNA、GitHub 单文件）整份保留，只截掉超长部分。
"""
import argparse, pathlib, re, sys

KEEP = ['essence', 'what it is', 'material', 'render', 'colou', 'color', 'palette', 'type', 'font', 'typograph',
        'subtitle', 'native', 'moves', 'pitfall', 'avoid', "don't", 'composition', 'layout', 'texture',
        '本质', '材质', '质感', '配色', '颜色', '字体', '字幕', '构图', '版式', '手法', '禁忌', '不要', '坑']
DROP = ['motion', 'camera', 'sound', 'audio', 'range', 'variation', 'engine', '动效', '镜头', '声音', '运动', '节奏']
MAX_SECTION = 1600      # 每节最多保留的字数，超了截断
MAX_TOTAL = 6000


def sections(text):
    parts, title, buf = [], None, []
    for line in text.splitlines():
        m = re.match(r'^(#{2,3})\s+(.*)', line)
        if m:
            parts.append((title, buf)); title, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    parts.append((title, buf))
    return parts


def wanted(title):
    t = title.lower()
    if any(k in t for k in DROP):
        return False
    return any(k in t for k in KEEP)


def squeeze(lines):
    out = '\n'.join(l.rstrip() for l in lines).strip()
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out if len(out) <= MAX_SECTION else out[:MAX_SECTION].rsplit('\n', 1)[0] + '\n…（后面略，要细节读原文）'


def card(md):
    p = pathlib.Path(md).expanduser()
    text = p.read_text(encoding='utf-8', errors='ignore')
    head = text.splitlines()[0].lstrip('# ').strip() if text.strip() else p.parent.name
    parts = sections(text)
    kept = [(t, squeeze(b)) for t, b in parts if t and wanted(t)]
    if len(kept) < 2:                               # 没有标准分节：整份保留（截断）
        body = text.strip()
        body = body if len(body) <= MAX_TOTAL else body[:MAX_TOTAL] + '\n…（后面略）'
        return f'# {head}\n来源：{p}\n\n{body}\n'
    out = [f'# 风格要点卡：{head}', f'来源：{p}（动效、镜头、声音这几节没放进来，做动画时再读原文）', '']
    for t, b in kept:
        out += [f'## {t}', b, '']
    s = '\n'.join(out)
    return s if len(s) <= MAX_TOTAL else s[:MAX_TOTAL] + '\n…（后面略）'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('style_md', nargs='+')
    ap.add_argument('--out'); ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    if not a.out and not a.print:
        sys.exit('要加 --out <文件夹> 或 --print')
    for md in a.style_md:
        p = pathlib.Path(md).expanduser()
        if not p.is_file():
            print(f'✗ 找不到 {md}'); continue
        c = card(p)
        if a.print:
            print(c); continue
        d = pathlib.Path(a.out); d.mkdir(parents=True, exist_ok=True)
        f = d / f'{p.parent.name}.md'; f.write_text(c, encoding='utf-8')
        print(f'{p.parent.name} → {f} · {len(c)} 字（原文 {len(p.read_text(encoding="utf-8", errors="ignore"))} 字）')


if __name__ == '__main__':
    main()
