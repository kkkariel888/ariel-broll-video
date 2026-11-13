#!/usr/bin/env python3
"""Lemo-Opuscar 风格库：下载 / 更新 / 列目录 / 取某个风格的说明。只用 Python 自带库 + git。

Lemo-Opuscar（github.com/lemomo-ai/lemo-opuscar，作者 Lemomo / LemoLab）的风格说明是 CC BY-NC 4.0，
另外授权「读它、照它、改它来做你自己的片子（商用也行）」。所以本 skill 不带它的任何内容，
只在用户自己的电脑上现下载、现读，用来给用户这期视频做画面。

  lemo.py ensure                 下载或更新到 ~/lemo-opuscar（和 Lemo 自己的 skill 用同一个位置），最后一行打印 LIB=<路径>
  lemo.py catalog [--out f.json] 列出能用的风格（去掉需要 AI 生图的），给 Agent 挑
  lemo.py style <slug>           打印这个风格 STYLE.md 的路径
  lemo.py demo <slug>            补下载这个风格的演示片源码（只用来参考写法）
  lemo.py mine                   列出用户自己的风格（~/lemo-my-styles/）
"""
import json, os, pathlib, re, shutil, subprocess, sys, time

REPO = os.environ.get('LEMO_OPUSCAR_REPO', 'https://github.com/lemomo-ai/lemo-opuscar.git')
LIB = pathlib.Path(os.environ.get('LEMO_OPUSCAR_HOME', pathlib.Path.home() / 'lemo-opuscar'))
MINE = pathlib.Path(os.environ.get('LEMO_MY_STYLES', pathlib.Path.home() / 'lemo-my-styles'))
SPARSE = ['/*', '!/styles/*/demo/', '!/styleboard/', '!/docs/readme/', '!/docs/cover.jpg', '!/styles/*/poster.jpg']
CREDIT = 'Lemo-Opuscar by Lemomo (LemoLab) · https://github.com/lemomo-ai/lemo-opuscar · 风格说明 CC BY-NC 4.0（另有制作自己影片的额外许可），代码 MIT'

def git(*a, cwd=None, check=True):
    r = subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-400:])
    return r.stdout.strip()

def is_lib(p):
    return (p / 'AGENTS.md').exists() and (p / 'styles').is_dir()

def ensure(retries=3):
    if not shutil.which('git'):
        sys.exit('✗ 没有 git，下载不了 Lemo 风格库。Mac：在「终端」里输入 xcode-select --install 装一下；Windows：装 Git for Windows。装好再来。')
    last = ''
    for i in range(retries):
        try:
            if is_lib(LIB) and git('config', '--get', 'lemo.managed', cwd=LIB, check=False) == 'true':
                git('fetch', '--quiet', '--depth', '1', 'origin', 'main', cwd=LIB)
                git('reset', '--quiet', '--hard', 'FETCH_HEAD', cwd=LIB)
            elif is_lib(LIB):
                pass                                   # 用户自己 clone 的，不动它
            else:
                if LIB.exists() and any(LIB.iterdir()):
                    sys.exit(f'✗ {LIB} 已经有别的东西，不是 Lemo 风格库。设置环境变量 LEMO_OPUSCAR_HOME 换个位置。')
                print(f'↓ 正在下载 Lemo 风格库到 {LIB}（第一次要几分钟）', file=sys.stderr)
                git('clone', '--quiet', '--depth', '1', '--filter=blob:none', '--sparse', '--branch', 'main', REPO, str(LIB))
                git('config', 'lemo.managed', 'true', cwd=LIB)
            if git('config', '--get', 'lemo.managed', cwd=LIB, check=False) == 'true':
                extra = [l for l in git('sparse-checkout', 'list', cwd=LIB, check=False).splitlines() if re.match(r'^/styles/[^/*]+/demo/$', l)]
                git('sparse-checkout', 'set', '--no-cone', *SPARSE, *extra, cwd=LIB, check=False)
            n = len(list((LIB / 'styles').glob('*/STYLE.md')))
            if n < 10:
                raise RuntimeError(f'只拿到 {n} 个风格，下载不完整')
            print(f'✓ Lemo 风格库就绪：{n} 个风格')
            print(f'LIB={LIB}')
            return LIB
        except RuntimeError as e:
            last = str(e)
            if LIB.exists() and not is_lib(LIB) and git('config', '--get', 'lemo.managed', cwd=LIB, check=False) != 'true':
                shutil.rmtree(LIB, ignore_errors=True)
            time.sleep(2 * (i + 1))
    sys.exit(f'✗ Lemo 风格库下载失败（试了 {retries} 次）：{last}\n'
             '  多半是网络连不上 GitHub。检查网络 / 代理后再说一声「重试」。没下载好之前不能继续选风格。')

def essence(md, n=420):
    """STYLE.md 第一段引言 + §1 的第一段，给 Agent 快速判断。"""
    t = md.read_text(encoding='utf-8')
    quote = ' '.join(l.lstrip('> ').strip() for l in t.splitlines() if l.startswith('> ') and 'References' not in l)[:n]
    m = re.search(r'## 1\.[^\n]*\n+(.+?)\n\n', t, re.S)
    return quote, (m.group(1).strip()[:n] if m else '')

def catalog():
    if not is_lib(LIB):
        sys.exit('✗ 还没下载 Lemo 风格库：先跑 lemo.py ensure')
    rows = []
    for d in sorted((LIB / 'styles').iterdir()):
        if d.name.startswith('_'):
            continue                                   # 模板文件夹
        sj, md = d / 'style.json', d / 'STYLE.md'
        if not (sj.exists() and md.exists()):
            continue
        s = json.loads(sj.read_text(encoding='utf-8'))
        if 'image-generation' in (s.get('needs') or []):
            continue                                   # 需要另外的 AI 生图工具，B-roll 不用
        q, e = essence(md)
        rows.append({'slug': s['slug'], 'cn': s.get('cn'), 'en': s.get('en'), 'category': s.get('category_cn'),
                     'line': s.get('line_cn'), 'uses': s.get('uses', []), 'summary': q, 'essence': e,
                     'style_md': str(md), 'source': 'lemo'})
    for d in sorted(MINE.glob('*/')) if MINE.exists() else []:
        sj, md = d / 'style.json', d / 'STYLE.md'
        if sj.exists() and md.exists():
            s = json.loads(sj.read_text(encoding='utf-8'))
            q, e = essence(md)
            rows.append({'slug': s.get('slug', d.name), 'cn': s.get('cn'), 'en': s.get('en'), 'category': '我的风格',
                         'line': s.get('line_cn', ''), 'uses': [], 'summary': q, 'essence': e, 'style_md': str(md), 'source': 'mine'})
    return rows

def style_md(slug):
    for base in [MINE / slug, LIB / 'styles' / slug]:
        if (base / 'STYLE.md').exists():
            return base / 'STYLE.md'
    sys.exit(f'✗ 找不到风格 {slug}')

def demo(slug):
    ensure()
    git('sparse-checkout', 'add', f'/styles/{slug}/demo/', cwd=LIB)
    print(LIB / 'styles' / slug / 'demo')

def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return
    cmd = a[0]
    if cmd == 'ensure':
        ensure()
    elif cmd == 'catalog':
        rows = catalog()
        out = json.dumps({'credit': CREDIT, 'count': len(rows), 'styles': rows}, ensure_ascii=False, indent=1)
        if '--out' in a:
            pathlib.Path(a[a.index('--out') + 1]).write_text(out, encoding='utf-8'); print(f'{len(rows)} 个风格 → {a[a.index("--out") + 1]}')
        else:
            for r in rows:
                print(f"{r['slug']:<24}{r['cn']:<10}{r['category']:<8}{r['line']}")
    elif cmd == 'style':
        print(style_md(a[1]))
    elif cmd == 'demo':
        demo(a[1])
    elif cmd == 'mine':
        for r in [r for r in catalog() if r['source'] == 'mine']:
            print(r['slug'], r['cn'])
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
