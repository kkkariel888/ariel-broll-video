#!/usr/bin/env python3
"""风格管家：验证上架 / 打分排名 / 参考图风格 DNA / 我的风格 / 上次那个。只用 Python 自带库。

  styles_tool.py list                                   列出能用的风格（上架的 + 我的风格）
  styles_tool.py verify <风格> [--text 一句真话]         跑通竖屏+横屏 3 秒小样，过了才改成「上架」
  styles_tool.py rank --types '{"讲原理":0.6,"比数字":0.4}' [--srt 字幕.srt] [--out 风格排名.json]
  styles_tool.py dna-new <dna.json> --folder <当期文件夹>  参考图提炼出的风格 DNA → 当期草稿风格
  styles_tool.py save-mine <草稿风格文件夹>               满意了，存进「我的风格」
  styles_tool.py last [--set <风格>]                     查看 / 记下「上次用的风格」
"""
import argparse, datetime, json, os, pathlib, re, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
STYLES = HERE / 'styles'
HOME = pathlib.Path(os.environ.get('BROLL_HOME', pathlib.Path.home() / '.broll-video-maker'))
MINE = HOME / 'my-styles'
LAST = HOME / 'last.json'
sys.path.insert(0, str(HERE / 'scripts'))
import render as R  # noqa: E402

CATEGORIES = ['讲原理', '比数字', '讲新闻', '演示工具', '讲结论']
LAYOUT_OF = {'讲原理': 'principle', '比数字': 'numbers', '演示工具': 'tool', '讲新闻': 'principle', '讲结论': 'numbers'}
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
NO_COPY = ['logo', '真人脸', '品牌名', '角色', '原图里的具体画面']

def read(p):
    return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))

def write(p, d):
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

def all_styles(include_pending=False):
    out = []
    for d in sorted(STYLES.iterdir()):
        if d.name.startswith('_') or not (d / 'style.json').exists():
            continue
        st = read(d / 'style.json')
        if st.get('status') == '上架' or include_pending:
            out.append((d, st, '内置'))
    if MINE.exists():
        for d in sorted(MINE.iterdir()):
            if (d / 'style.json').exists():
                out.append((d, read(d / 'style.json'), '我的'))
    return out

# ---------- 验证上架 ----------
SAMPLES = {'principle': '复利就是利滚利，本金生利息，利息再生利息', 'numbers': '存银行年化 2%，买指数基金长期大约 8%，差了 4 倍',
           'tool': '我让 Claude 读完字幕，自动标黄，再一键出片', 'news': '今天 OpenAI 发布了新模型，价格直接砍半',
           'conclusion': '所以说到底，年轻人最该投资的是自己'}

def verify(name, text=None):
    """5 种版式 × 竖横屏全部跑通才上架。视频小样各出一条，每种版式各出一张定格图。"""
    d = R.find_style(name); st = read(d / 'style.json')
    sd = d / 'samples'; sd.mkdir(exist_ok=True)
    report = {'style': st['id'], 'checked_at': datetime.date.today().isoformat(), 'results': {}}
    ok = True
    for asp, tag in [('9:16', '9x16'), ('16:9', '16x9')]:
        size = '1080x1920' if asp == '9:16' else '1920x1080'
        for lay, t in SAMPLES.items():
            key = f'{asp} {lay}'
            try:
                png = R.render(name, text if (text and lay == R.pick_layout(text)) else t, 3.0, asp, size, at=2.96, out=str(sd / f'{lay}_{tag}.png'), layout=lay)[0]
                first = R.render(name, t, 3.0, asp, size, at=0.0, out=str(sd / '_first.png'), layout=lay)[0]
                moved = pathlib.Path(first).read_bytes() != pathlib.Path(png).read_bytes(); pathlib.Path(first).unlink()
                report['results'][key] = {'ok': moved, 'still': 'samples/' + os.path.basename(png)}
                ok &= moved
            except Exception as e:
                report['results'][key] = {'ok': False, 'error': str(e)[:300]}; ok = False
        try:
            mp4 = R.render(name, SAMPLES['principle'], 3.0, asp, size, out=str(sd / f'sample_{tag}.mp4'), quiet=True, layout='principle')[0]
            info = probe(mp4); good = abs(info.get('dur', 0) - 3.0) < 0.15
            report['results'][f'{asp} 视频'] = {'ok': good, 'video': 'samples/' + os.path.basename(mp4), **info}; ok &= good
        except Exception as e:
            report['results'][f'{asp} 视频'] = {'ok': False, 'error': str(e)[:300]}; ok = False
    st['status'] = '上架' if ok else '待验证'
    st['verified'] = report
    write(d / 'style.json', st)
    bad = [k for k, v in report['results'].items() if not v.get('ok')]
    print('结论：', f"{st['name']} 跑通了 {len(report['results'])} 项，已上架" if ok else f"{st['name']} 没跑通：{'、'.join(bad)}，留在待验证区")
    return ok

def probe(p):
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                            '-of', 'json', p], capture_output=True, text=True)
        j = json.loads(r.stdout); s = j['streams'][0]
        return {'w': s['width'], 'h': s['height'], 'fps': s['r_frame_rate'], 'dur': float(j['format']['duration'])}
    except Exception:
        return {}

# ---------- 打分排名 ----------
def srt_stats(path):
    """从字幕算语速（字/秒）和数字密度（每分钟几个数字）。"""
    txt = pathlib.Path(path).read_text(encoding='utf-8-sig')
    ts = re.findall(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', txt)
    sec = lambda h, m, s, ms: int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    speak = sum(max(0, sec(*t[4:]) - sec(*t[:4])) for t in ts) or 1
    lines = [l for l in txt.splitlines() if l.strip() and not l.strip().isdigit() and '-->' not in l]
    chars = sum(len(re.sub(r'\s', '', l)) for l in lines)
    nums = len(re.findall(r'\d+(?:\.\d+)?', ''.join(lines)))
    total = (sec(*ts[-1][4:]) if ts else speak) / 60 or 1
    cps = chars / speak
    pace = 'fast' if cps > 5.0 else ('slow' if cps < 3.5 else 'mid')
    density = 'high' if nums / total > 3 else ('low' if nums / total < 1 else 'mid')
    return {'chars_per_sec': round(cps, 2), 'numbers_per_min': round(nums / total, 2), 'pace': pace, 'density': density}

def rank(types, stats=None):
    """分数 = 内容类型匹配 70 + 语速匹配 15 + 信息密度匹配 15。types 是 Agent 读完内容给的比例。"""
    order = ['slow', 'mid', 'fast']; dens = ['low', 'mid', 'high']
    rows = []
    for d, st, src in all_styles():
        suits = st.get('suits') or {st.get('category', ''): 1.0}
        tot = sum(float(v) for v in types.values()) or 1
        s_cat = 70 * sum(float(types.get(k, 0)) * float(suits.get(k, 0)) for k in types) / tot
        cat = max(suits, key=suits.get) if suits else ''
        s_pace = s_den = 7.5
        if stats:
            dp = abs(order.index(st.get('pace', 'mid')) - order.index(stats['pace']))
            dd = abs(dens.index(st.get('density', 'mid')) - dens.index(stats['density']))
            s_pace = [15, 7, 0][dp]; s_den = [15, 7, 0][dd]
        bonus = 3 if src == '我的' else 0          # 自己的风格同分时优先
        score = round(s_cat + s_pace + s_den + bonus, 1)
        rows.append({'id': st['id'], 'name': st['name'], 'category': cat, 'vibe': st.get('vibe', ''), 'source': src, 'path': str(d), 'score': score,
                     'parts': {'内容': round(s_cat, 1), '语速': s_pace, '密度': s_den}})
    rows.sort(key=lambda r: -r['score'])
    return rows

# ---------- 参考图 → 风格 DNA ----------
DNA_FIELDS = {
    'palette': '主色 3~5 个色值：bg, ink, accent 必填；accent2, muted 可选',
    'background': '背景质感：texture = plain/paper/grain/grid/dots/scanlines/vignette',
    'layout_rules': '版式和留白：margin（0.05~0.15）、align（left/center）、whitespace（一句话）',
    'type': '字体粗细大小：head_weight、body_weight（100~900）、scale（0.8~1.3）',
    'line': '线条粗细：width（1~8）',
    'motion.entrance': '进场方式：draw/rise/pop/blur/type',
    'motion.speed': '动效速度：0.7（慢）~1.4（快）',
    'motion.cuts_per_5s': '每 5 秒换几次画面：1~4',
}

def check_dna(dna):
    errs = []
    p = dna.get('palette', {})
    for k in ['bg', 'ink', 'accent']:
        if not HEX.match(str(p.get(k, ''))): errs.append(f'palette.{k} 要是 #RRGGBB')
    cols = [v for v in p.values() if HEX.match(str(v))]
    if not 3 <= len(cols) <= 5: errs.append('主色要 3~5 个')
    if dna.get('background', {}).get('texture', 'plain') not in ['plain', 'paper', 'grain', 'grid', 'dots', 'scanlines', 'vignette']: errs.append('background.texture 不认识')
    m = dna.get('motion', {})
    if m.get('entrance', 'rise') not in ['draw', 'rise', 'pop', 'blur', 'type']: errs.append('motion.entrance 不认识')
    if not 0.6 <= float(m.get('speed', 1)) <= 1.5: errs.append('motion.speed 要在 0.6~1.5')
    if not 1 <= int(m.get('cuts_per_5s', 2)) <= 4: errs.append('motion.cuts_per_5s 要在 1~4')
    if not 1 <= float(dna.get('line', {}).get('width', 3)) <= 8: errs.append('line.width 要在 1~8')
    banned = json.dumps(dna, ensure_ascii=False).lower()
    for w in ['logo', 'http', '.png', '.jpg', '.svg']:
        if w in banned: errs.append(f'DNA 里不能带「{w}」：只记感觉，不带原图素材')
    return errs

def dna_new(dna_path, folder):
    dna = read(dna_path); errs = check_dna(dna)
    if errs:
        sys.exit('风格 DNA 不合格：\n- ' + '\n- '.join(errs))
    name = dna.get('name') or '参考图风格'
    sid = 'draft-' + datetime.datetime.now().strftime('%m%d%H%M')
    st = {'id': sid, 'name': name, 'vibe': dna.get('vibe', ''), 'fit': dna.get('fit', ''),
          'suits': dna.get('suits') or {c: 0.7 for c in CATEGORIES},
          'palette': dna['palette'], 'background': dna.get('background', {'texture': 'plain'}),
          'layout_rules': dna.get('layout_rules', {}), 'type': dna.get('type', {}), 'line': dna.get('line', {'width': 3}),
          'motion': dna.get('motion', {}), 'surface': dna.get('surface', {'kind': 'outline'}),
          'accent_style': dna.get('accent_style', 'fill'), 'density': dna.get('density', 'mid'), 'pace': dna.get('pace', 'mid'),
          'license': '从用户参考图提炼的风格 DNA（只记配色、质感、版式、字重、线条、动效），不含原图素材',
          'source': '用户参考图', 'status': '草稿', 'not_copied': NO_COPY,
          'sample_text': dna.get('sample_text', '')}
    d = pathlib.Path(folder) / '风格草稿' / sid
    write(d / 'style.json', st)
    print(d)
    return d

def save_mine(draft):
    d = pathlib.Path(draft); st = read(d / 'style.json')
    sid = re.sub(r'^draft-', 'my-', st['id'])
    dst = MINE / sid
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(d, dst, ignore=shutil.ignore_patterns('samples'))
    st['id'] = sid; st['status'] = '我的'; write(dst / 'style.json', st)
    print(dst)

def last(set_to=None):
    if set_to:
        d = R.find_style(set_to); st = read(d / 'style.json')
        write(LAST, {'id': st['id'], 'name': st['name'], 'path': str(d), 'at': datetime.datetime.now().isoformat(timespec='seconds')})
    print(json.dumps(read(LAST), ensure_ascii=False) if LAST.exists() else '{}')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('list'); p.add_argument('--all', action='store_true')
    p = sub.add_parser('verify'); p.add_argument('style'); p.add_argument('--text')
    p = sub.add_parser('rank'); p.add_argument('--types', required=True); p.add_argument('--srt'); p.add_argument('--out')
    p = sub.add_parser('dna-new'); p.add_argument('dna'); p.add_argument('--folder', required=True)
    p = sub.add_parser('save-mine'); p.add_argument('draft')
    p = sub.add_parser('last'); p.add_argument('--set')
    a = ap.parse_args()
    if a.cmd == 'list':
        for d, st, src in all_styles(a.all):
            print(f"{st['id']:<18}{st['name']:<8}{st.get('status',''):<6}{src}  {st.get('vibe','')}")
    elif a.cmd == 'verify':
        sys.exit(0 if verify(a.style, a.text) else 1)
    elif a.cmd == 'rank':
        stats = srt_stats(a.srt) if a.srt else None
        rows = rank(json.loads(a.types), stats)
        out = {'types': json.loads(a.types), 'stats': stats, 'ranking': rows}
        if a.out: write(a.out, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif a.cmd == 'dna-new':
        dna_new(a.dna, a.folder)
    elif a.cmd == 'save-mine':
        save_mine(a.draft)
    elif a.cmd == 'last':
        last(a.set)

if __name__ == '__main__':
    main()
