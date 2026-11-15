#!/usr/bin/env python3
"""主路线跑完后，从它的临时文件夹存两个中间存档，给「再来 3 个」「要改」这两个场景当起点（不用从头跑，省钱）。

  python3 tests/ux/save_checkpoint.py <主路线的临时文件夹>

存到 tests/ux/checkpoints/samples_ready/（样图刚出齐、还没选风格）和 review_ready/（审稿表刚出齐、还没通过）。
有大图，已在 .gitignore 里，不进仓库。画面页用到的画图工具一起存进 _home/kits/，场景跑的时候当测试主目录用。
"""
import json, os, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
LATER = {
    'samples_ready': ['风格选择.json', '逐帧审稿.json', '审稿结果.json', '成片.json', '逐帧图', '逐帧代码', 'kits草稿', '事件.jsonl', '事件.seen'],
    'review_ready': ['审稿结果.json', '成片.json', '事件.jsonl', '事件.seen'],
}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run = pathlib.Path(sys.argv[1]).resolve()
    work = run / '.broll'
    if not (work / '逐帧审稿.json').exists():
        sys.exit(f'{work} 里还没有 逐帧审稿.json：主路线要先跑到审稿表出齐')
    home = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker'))
    for name, drop in LATER.items():
        dst = HERE / 'checkpoints' / name
        shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True)
        for f in run.iterdir():
            if f.suffix.lower() in ('.mp4', '.mov', '.srt', '.docx', '.txt', '.md'):
                shutil.copy2(f, dst / f.name)
        shutil.copytree(work, dst / '.broll', ignore=shutil.ignore_patterns(*drop))
        rank = dst / '.broll' / '风格排名.json'
        if rank.exists():
            d = json.loads(rank.read_text(encoding='utf-8')); d['drawing'] = False
            rank.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        slugs = {c['slug'] for c in json.loads(rank.read_text(encoding='utf-8')).get('candidates', [])} if rank.exists() else set()
        for s in slugs:
            if (home / 'kits' / s).is_dir():
                shutil.copytree(home / 'kits' / s, dst / '_home' / 'kits' / s, dirs_exist_ok=True)
        print(f'✓ {name} → {dst}')


if __name__ == '__main__':
    main()
