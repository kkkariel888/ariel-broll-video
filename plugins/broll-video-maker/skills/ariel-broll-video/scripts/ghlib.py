#!/usr/bin/env python3
"""我的 GitHub 库：用户在 GitHub 上看中的整套风格库，存一个链接 + 一两句风格描述 + 3 张预览图（只用 Python 自带库 + git）。

  ghlib.py add <GitHub 链接> --desc "风格大致是：……" [--name 显示名] [--count "84 种风格"]
  ghlib.py list

add 会：下载仓库到 ~/.broll-video-maker/imports/（和 dna.py license 同一个地方）→ 查许可证 →
从仓库自己的介绍页（README）里抓前 3 张预览图（跳过徽章小图）→ 存进 ~/.broll-video-maker/github/<作者>__<仓库>/。
标黄页第 4 步「我的 GitHub 库」就读这里。--desc 由 AI 读完 README 写：一两句大白话，说这个库的画面大致长什么样、适合讲什么。
最后一行：STATUS=ok / STATUS=fail
"""
import datetime, json, os, pathlib, re, shutil, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dna  # noqa: E402  复用 dna.py 的下载和许可证判断

GH = dna.HOME / 'github'
IMG = re.compile(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?[^)]*\)|<img[^>]+src=["\']([^"\']+)["\']', re.I)
BADGE = re.compile(r'shields\.io|badge|badgen|travis-ci|codecov|\.svg(\?|$)|star-history|contrib\.rocks|visitor', re.I)
EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
MAX = 12 * 1024 * 1024


def key_of(url):
    m = re.match(r'(?:https?://)?github\.com/([^/\s]+)/([^/\s#?]+)', url)
    if not m:
        sys.exit('只认 GitHub 链接（github.com/作者/仓库）\nSTATUS=fail')
    return m.group(1), m.group(2).removesuffix('.git')


def previews(local, owner, repo, dst, n=3):
    readme = next((f for f in sorted(local.iterdir()) if f.name.lower().startswith('readme')), None)
    if not readme:
        return []
    text = readme.read_text(encoding='utf-8', errors='ignore')
    got, seen = [], set()
    for m in IMG.finditer(text):
        src = (m.group(1) or m.group(2) or '').strip()
        if not src or src in seen or BADGE.search(src):
            continue
        seen.add(src)
        ext = os.path.splitext(urllib.parse.urlparse(src).path)[1].lower()
        if ext not in EXTS:
            continue
        out = dst / f'{len(got) + 1}{ext}'
        try:
            if re.match(r'https?://', src):
                req = urllib.request.Request(src, headers={'User-Agent': 'broll-ghlib'})
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = r.read(MAX + 1)
            else:   # 仓库里的相对路径：直接从下载好的仓库里拿
                fp = (local / urllib.parse.unquote(src.lstrip('./'))).resolve()
                if not str(fp).startswith(str(local.resolve())) or not fp.is_file():
                    continue
                data = fp.read_bytes()
            if len(data) > MAX or len(data) < 2048:
                continue
            out.write_bytes(data)
            got.append(out.name)
        except Exception:
            continue
        if len(got) >= n:
            break
    return got


def add(url, desc, name=None, count=''):
    owner, repo = key_of(url)
    lic = dna.license_check(f'https://github.com/{owner}/{repo}')
    local = pathlib.Path(lic['local'])
    d = GH / f'{owner}__{repo}'
    pv = d / 'previews'
    shutil.rmtree(pv, ignore_errors=True)
    pv.mkdir(parents=True, exist_ok=True)
    got = previews(local, owner, repo, pv)
    old = {}
    if (d / 'repo.json').exists():
        old = json.loads((d / 'repo.json').read_text(encoding='utf-8'))
    rj = {'repo': f'{owner}/{repo}', 'url': f'https://github.com/{owner}/{repo}', 'name': name or old.get('name') or repo,
          'desc': desc or old.get('desc', ''), 'count': count or old.get('count', ''), 'verdict': lic['verdict'], 'why': lic['why'],
          'license': '、'.join(lic['found']) or '没写', 'local': str(local),
          'saved': old.get('saved') or datetime.date.today().isoformat()}
    (d / 'repo.json').write_text(json.dumps(rj, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"已存进我的 GitHub 库：{rj['name']}（{rj['url']}）")
    print(f"许可证：{rj['license']} → {rj['verdict']}（{rj['why']}）")
    print(f"预览图：{len(got)} 张" + ('' if got else '（介绍页里没找到图，页面上先用文字卡片，用它出过片后换成样图）'))
    print('STATUS=ok')


def list_all():
    if not GH.exists():
        print('（还没存过）'); return
    for d in sorted(GH.iterdir()):
        f = d / 'repo.json'
        if f.exists():
            r = json.loads(f.read_text(encoding='utf-8'))
            print(f"{r['repo']}｜{r.get('name')}｜{r.get('verdict')}｜{r.get('desc', '')[:80]}｜本地：{r.get('local')}")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return
    if a[0] == 'add' and len(a) >= 2:
        opt = lambda k: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else ''
        add(a[1], opt('--desc'), opt('--name') or None, opt('--count'))
    elif a[0] == 'list':
        list_all()
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
