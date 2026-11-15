#!/usr/bin/env python3
"""每个风格的「画图工具」：第一次用这个风格时写一次，存起来，以后样图和正式画面都直接用，不再从零写。

存在 ~/.broll-video-maker/kits/<slug>/（只在这台电脑上，不分发）：
  kit.js   ES 模块：配色、字体加载、质感 / 背景、常用零件（标题、数字、箭头、卡片……）的画法
  KIT.md   20 行以内的要点：配色、字体、质感、构图、动效、禁忌，加上 kit.js 里每个函数一句话
画面页里：import * as K from '/@kits/<slug>/kit.js'（render.py 和标黄页面都会提供这个地址）

  kit.py status <slug> [<slug> ...] --style-md <路径> [...]   每个风格：ready（能直接用）/ missing（要写）/ stale（风格说明改过，要重写）
  kit.py save <slug> <文件夹> --style-md <路径>               把 <文件夹>/kit.js 和 KIT.md 存进去（记下风格说明的指纹）
  kit.py path <slug>                                           打印存放的文件夹
"""
import argparse, hashlib, json, os, pathlib, shutil, sys

HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker')) / 'kits'


def finger(style_md):
    p = pathlib.Path(os.path.expanduser(style_md or ''))
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12] if p.is_file() else ''


def status(slug, style_md):
    d = HOME / slug
    if not ((d / 'kit.js').exists() and (d / 'KIT.md').exists()):
        return 'missing'
    meta = json.loads((d / 'meta.json').read_text(encoding='utf-8')) if (d / 'meta.json').exists() else {}
    f = finger(style_md)
    return 'stale' if f and meta.get('style_md_sha') != f else 'ready'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'save', 'path']); ap.add_argument('args', nargs='+')
    ap.add_argument('--style-md', nargs='*', default=[])
    a = ap.parse_args()
    if a.cmd == 'path':
        print(HOME / a.args[0]); return
    if a.cmd == 'status':
        mds = a.style_md + [''] * (len(a.args) - len(a.style_md))
        for slug, md in zip(a.args, mds):
            st = status(slug, md)
            print(f'{slug}\t{st}\t' + (str(HOME / slug / 'KIT.md') if st == 'ready' else ''))
        return
    slug, src = a.args[0], pathlib.Path(a.args[1])
    for f in ('kit.js', 'KIT.md'):
        if not (src / f).is_file():
            sys.exit(f'{src} 里没有 {f}')
    d = HOME / slug; d.mkdir(parents=True, exist_ok=True)
    for f in ('kit.js', 'KIT.md'):
        shutil.copy2(src / f, d / f)
    (d / 'meta.json').write_text(json.dumps({'slug': slug, 'style_md': a.style_md[0] if a.style_md else '',
                                             'style_md_sha': finger(a.style_md[0] if a.style_md else '')}, ensure_ascii=False), encoding='utf-8')
    print(d)


if __name__ == '__main__':
    main()
