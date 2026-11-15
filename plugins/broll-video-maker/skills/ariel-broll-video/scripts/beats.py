#!/usr/bin/env python3
"""让画面跟着说话的快慢走（只用 Python 自带库 + ffmpeg）。全部在后台用，不给用户看、不要用户确认。

  beats.py make <工作>                     用户点了「开始做」以后跑：给标黄的每一处写一份节拍
  beats.py voice <工作> --video <口播视频>  出片以后跑：给每段成片配上原声做预览（页面「④ 成片」点开就带声音）

make：把「每个字是第几秒说的」（逐字时间.json，听写量出来的）对到字幕的字上（字幕_修正.srt，用户的字），
  给每一处写 <工作>/逐帧代码/节拍/B3.js。画面页引用它以后可以用：
    window.BEAT        {no, dur, text, chars:[[字, 秒]…], pauses:[[秒, 停多久]…], phrases:[[秒, 短句]…], precise}
                       秒都是从这一处开头算；chars 不含标点
    at("康波周期")       这个词说出来的那一秒（同一个词第二次出现：at("词", 2)）
    cue("康波周期")      动作开始的那一秒 = 说到前 0.25 秒（词说出来时动作刚好到位）
    endOf("康波周期")    这个词说完的那一秒
  没有 逐字时间.json（听写工具装不上）就把每行字幕的时长按字数摊开，precise=false，并打印一句提醒。
voice：成片本身没有声音（拖进剪映不会和原声叠在一起）；另做一份带原声的预览放 <工作>/成片/预览/，
  写进 成片.json 每段的 preview，页面播放时用它。放进用户文件夹的还是没声音的那份。
最后一行：STATUS=ok / STATUS=fail
"""
import difflib, json, os, pathlib, re, shutil, subprocess, sys

PUNCT = set('，。！？、；：,.!?;:…—-·「」『』“”"\'（）()《》【】[] \t\r\n　~～')
LEAD = 0.25          # 动作比词早多少秒开始
PAUSE = 0.45         # 两个字的开头隔这么久以上，就算停顿了一下


def jload(p, d=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
    except Exception:
        return d


def _ts(s):
    h, m, rest = s.strip().replace('.', ',').split(':')
    sec, ms = (rest.split(',') + ['0'])[:2]
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms.ljust(3, '0')[:3]) / 1000


def read_cues(path):
    raw = pathlib.Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = []
    for chunk in re.split(r'\n\s*\n', raw.strip()):
        lines = [l for l in chunk.split('\n') if l.strip()]
        ti = next((i for i, l in enumerate(lines) if '-->' in l), None)
        if ti is None:
            continue
        a, b = lines[ti].split('-->')
        text = ''.join(l.strip() for l in lines[ti + 1:])
        if text:
            cues.append((_ts(a), _ts(b.split()[0]), text))
    return cues


def char_times(cues, asr):
    """字幕里每个字（不含标点）是第几秒说的。返回 [[字, 秒, 是否量出来的], …]。"""
    S, owner = [], []
    for ci, (_, _, text) in enumerate(cues):
        for ch in text:
            if ch not in PUNCT:
                S.append(ch); owner.append(ci)
    t = [None] * len(S)
    match = 0.0
    if asr:
        A = [c for c, _ in asr]
        sm = difflib.SequenceMatcher(None, A, S, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal' or (tag == 'replace' and i2 > i1):
                for k in range(j1, j2):
                    i = i1 + (k - j1 if tag == 'equal' else (k - j1) * (i2 - i1) // (j2 - j1))
                    t[k] = float(asr[i][1])
        match = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(S))
        # 听写对错了位置（离这行字幕的时间差 1 秒以上）就不信它
        for k, ci in enumerate(owner):
            st, en, _ = cues[ci]
            if t[k] is not None and not (st - 1.0 <= t[k] <= en + 1.0):
                t[k] = None
    measured = [x is not None for x in t]
    # 没量到的字：同一行里前后量到的字之间按顺序摊开；整行都没量到就按字数摊满这一行
    for ci, (st, en, _) in enumerate(cues):
        ks = [k for k, o in enumerate(owner) if o == ci]
        if not ks:
            continue
        span = max(0.2, (en - st) * 0.92)
        anchors = [(-1, st)] + [(k, t[k]) for k in ks if t[k] is not None] + [(len(S), st + span)]
        for (ka, ta), (kb, tb) in zip(anchors, anchors[1:]):
            gap = [k for k in ks if ka < k < kb and t[k] is None]
            for n, k in enumerate(gap, 1):
                t[k] = ta + (tb - ta) * n / (len(gap) + 1) if ka >= 0 else st + (tb - st) * (n - 1) / max(1, len(gap))
    for k in range(1, len(t)):          # 时间不能倒着走
        t[k] = max(t[k], t[k - 1])
    return [[S[k], round(t[k], 3), measured[k]] for k in range(len(S))], match


def find_span(chars, text, start_time):
    """标黄的这句话在全文里是哪几个字：取开头时间离 startTime 最近的那一处。"""
    want = [c for c in text if c not in PUNCT]
    if not want:
        return None
    flat = ''.join(c for c, _, _ in chars)
    key = ''.join(want)
    best, i = None, flat.find(key)
    while i >= 0:
        d = abs(chars[i][1] - (start_time or 0))
        if best is None or d < best[0]:
            best = (d, i)
        i = flat.find(key, i + 1)
    if best:
        return best[1], best[1] + len(want)
    # 找不到完全一样的（用户标黄后字幕又改过）：用相似度找最像的一段
    sm = difflib.SequenceMatcher(None, flat, key, autojunk=False)
    m = max(sm.get_matching_blocks(), key=lambda b: b.size)
    if m.size < max(2, len(want) // 3):
        return None
    s = max(0, m.a - m.b)
    return s, min(len(chars), s + len(want))


JS = r"""(function(){var B=window.BEAT=%s;var flat=B.chars.map(function(c){return c[0]}).join('');
var P=/[\s，。！？、；：,.!?;:…—\-·「」『』“”"'（）()《》【】\[\]~～]/g;
window.__beatUsed=window.__beatUsed||[];window.__beatMiss=window.__beatMiss||[];
function find(w,n){var k=String(w).replace(P,''),i=-1;n=n||1;for(var j=0;j<n;j++){i=flat.indexOf(k,i+1);if(i<0)break;}
  if(i<0||!k){window.__beatMiss.push(String(w));return null;}return {i:i,n:k.length};}
window.at=function(w,n){var f=find(w,n);if(!f)return null;var t=B.chars[f.i][1];window.__beatUsed.push({w:String(w),t:t});return t;};
window.cue=function(w,n,lead){var t=window.at(w,n);if(t===null)return null;return Math.max(0,t-(lead==null?%s:lead));};
window.endOf=function(w,n){var f=find(w,n);if(!f)return null;var j=f.i+f.n-1,nx=B.chars[j+1];
  return nx?Math.min(nx[1],B.chars[j][1]+0.35):Math.min(B.dur,B.chars[j][1]+0.3);};
if(typeof window.DUR==='undefined')window.DUR=B.dur;})();
"""


def make(work):
    work = pathlib.Path(work)
    hl = jload(work / '标黄结果.json', {}) or {}
    items = hl.get('result') or []
    if not items:
        print('标黄结果.json 里没有标黄的地方'); print('STATUS=fail'); return 1
    srt = next((work / n for n in ('字幕_修正.srt', '字幕_自动识别.srt') if (work / n).exists()), None)
    if not srt:
        srt = next(iter(sorted(work.parent.glob('*.srt'))), None)
    if not srt:
        print('找不到字幕（字幕_修正.srt）'); print('STATUS=fail'); return 1
    cues = read_cues(srt)
    asr = jload(work / '逐字时间.json')
    chars, match = char_times(cues, asr)
    out = work / '逐帧代码' / '节拍'
    out.mkdir(parents=True, exist_ok=True)
    if asr:
        print(f'每个字的时间：用听写量出来的（和字幕对上 {match:.0%}）')
    else:
        print('提醒：没有 逐字时间.json（听写没跑成），每个字的时间按每行字幕的长短摊开估的，只能跟到每一句的快慢。'
              '对话里跟用户说一句「这次画面只能跟到每句话，跟不到每个字」。')
    for it in items:
        no, st, en = it.get('no'), it.get('startTime'), it.get('endTime')
        if st is None or en is None:
            print(f'{no}：没有时间，跳过'); continue
        dur = round(max(0.5, en - st), 3)
        span = find_span(chars, it.get('text', ''), st)
        if not span:
            print(f'{no}：在字幕里没找到这句话，跳过（画面就按整句的起止时间做）'); continue
        cs = chars[span[0]:span[1]]
        rel = [[c, round(min(dur, max(0.0, t - st)), 3)] for c, t, _ in cs]
        precise = bool(asr) and sum(1 for c in cs if c[2]) >= len(cs) * 0.6
        pauses = []
        for a, b in zip(rel, rel[1:]):
            if b[1] - a[1] >= PAUSE:
                pauses.append([round(a[1] + 0.25, 2), round(b[1] - a[1] - 0.25, 2)])
        cut, k = {0}, 0                      # 短句：原话的标点处、说话停顿处都切开（剪映字幕没标点）
        for ch in it.get('text', ''):
            if ch in PUNCT: cut.add(k)
            elif ch.strip(): k += 1
        cut |= {i + 1 for i, (x, y) in enumerate(zip(rel, rel[1:])) if y[1] - x[1] >= PAUSE}
        cut = sorted(i for i in cut if i < len(rel))
        ph = [[rel[i][1], ''.join(c for c, _ in rel[i:j])] for i, j in zip(cut, cut[1:] + [len(rel)])]
        beat = {'no': no, 'dur': dur, 'text': it.get('text', ''), 'chars': rel, 'pauses': pauses, 'phrases': ph, 'precise': precise}
        (out / f'{no}.js').write_text(JS % (json.dumps(beat, ensure_ascii=False), LEAD), encoding='utf-8')
        speed = len(rel) / max(0.5, rel[-1][1] - rel[0][1] + 0.3)
        print(f'{no}：{dur} 秒，{len(rel)} 字，每秒约 {speed:.1f} 字，停顿 {len(pauses)} 处'
              + ('' if precise else '（按字幕行估的）') + f' → 逐帧代码/节拍/{no}.js')
    print('STATUS=ok'); return 0


def voice(work, video):
    work = pathlib.Path(work)
    if not shutil.which('ffmpeg'):
        print('没找到 ffmpeg'); print('STATUS=fail'); return 1
    out = jload(work / '成片.json', {}) or {}
    hl = {x.get('no'): x for x in ((jload(work / '标黄结果.json', {}) or {}).get('result') or [])}
    pv = work / '成片' / '预览'
    pv.mkdir(parents=True, exist_ok=True)
    n = 0
    for c in out.get('clips', []):
        src = work / c.get('file', '')
        it = hl.get(c.get('no'))
        if not src.is_file() or not it or it.get('startTime') is None:
            continue
        dst = pv / src.name
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(src), '-ss', f"{it['startTime']:.3f}", '-i', str(video),
                                '-map', '0:v:0', '-map', '1:a:0?', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                                '-movflags', '+faststart', str(dst)], capture_output=True, text=True)
            if r.returncode:
                print(f"{c.get('no')}：配原声失败：{r.stderr.strip()[:200]}"); continue
        c['preview'] = str(dst.relative_to(work)); n += 1
    (work / '成片.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{n} 段配好了原声预览（只在页面上播放用，放进文件夹的还是没声音的）')
    print('STATUS=ok'); return 0


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'make':
        sys.exit(make(a[1]))
    if len(a) >= 2 and a[0] == 'voice' and '--video' in a and a.index('--video') + 1 < len(a):
        sys.exit(voice(a[1], a[a.index('--video') + 1]))
    print(__doc__)


if __name__ == '__main__':
    main()
