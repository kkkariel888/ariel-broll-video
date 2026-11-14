#!/usr/bin/env python3
"""下载风格说明里点名的免费字体（OFL 等开源许可），放到 ~/.broll-video-maker/fonts/<名字>/，再复制进画面页文件夹用。

  fonts.py get "LXGW Marker Gothic"     霞鹜漫黑
  fonts.py get "Kalam"                  其它 Google Fonts 收录的开源字体，按名字找（google/fonts 仓库的 ofl/ 目录）
  fonts.py copy "Kalam" <画面页文件夹>    复制到画面页旁边，页面里用 new FontFace(...) 加载
中文正文默认用系统的思源黑体 / 思源宋体（Noto Sans / Serif CJK），不用下载。
"""
import os, pathlib, re, shutil, subprocess, sys

HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker')) / 'fonts'
# 不在 Google Fonts 里的常用中文开源字体：仓库 + 字体所在目录
SPECIAL = {
    'lxgw marker gothic': ('https://github.com/lxgw/LxgwMarkerGothic', '/fonts/ttf/'),
    'lxgw wenkai': ('https://github.com/lxgw/LxgwWenKai', '/fonts/TTF/'),
    'jetbrains mono': ('https://github.com/JetBrains/JetBrainsMono', '/fonts/ttf/'),
    'inter': ('https://github.com/rsms/inter', '/docs/font-files/'),
}

def slug(name):
    return re.sub(r'[^a-z0-9]+', '', name.lower())

def get(name):
    key = name.lower().strip(); dst = HOME / slug(name)
    if dst.exists() and list(dst.rglob('*.[ot]tf')) + list(dst.rglob('*.woff2')):
        print(dst); return dst
    if not shutil.which('git'): sys.exit('没有 git，下载不了字体')
    repo, sub = SPECIAL.get(key, ('https://github.com/google/fonts', f'/ofl/{slug(name)}/'))
    tmp = dst.with_name(dst.name + '_git'); shutil.rmtree(tmp, ignore_errors=True)
    r = subprocess.run(['git', 'clone', '--quiet', '--depth', '1', '--filter=blob:none', '--sparse', repo, str(tmp)], capture_output=True, text=True)
    if r.returncode: sys.exit(f'字体下载失败：{r.stderr.strip()[-200:]}')
    subprocess.run(['git', '-C', str(tmp), 'sparse-checkout', 'set', '--no-cone', sub, '/OFL.txt', '/LICENSE*'], capture_output=True)
    files = [f for f in (tmp / sub.strip('/')).rglob('*') if f.suffix.lower() in ('.ttf', '.otf', '.woff2')] if (tmp / sub.strip('/')).exists() else []
    if not files:
        shutil.rmtree(tmp, ignore_errors=True); sys.exit(f'没找到字体「{name}」：检查名字（按风格说明里写的英文名）')
    dst.mkdir(parents=True, exist_ok=True)
    for f in files: shutil.copy2(f, dst / f.name)
    for lic in list(tmp.glob('OFL.txt')) + list(tmp.glob('LICENSE*')) + list((tmp / sub.strip('/')).glob('OFL.txt')):
        shutil.copy2(lic, dst / lic.name)
    shutil.rmtree(tmp, ignore_errors=True)
    print(dst); return dst

def copy(name, folder):
    src = get(name); folder = pathlib.Path(folder); folder.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.suffix.lower() in ('.ttf', '.otf', '.woff2') or f.name.startswith(('OFL', 'LICENSE')):
            shutil.copy2(f, folder / f.name); print(folder / f.name)

def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'get': get(a[1])
    elif len(a) >= 3 and a[0] == 'copy': copy(a[1], a[2])
    else: print(__doc__)

if __name__ == '__main__':
    main()
