#!/usr/bin/env python3
"""没有 SRT 时用：在本机把口播视频听写成字幕（不上传，不用剪映电脑版）。
有逐字稿（.docx / .txt / .md）就用逐字稿的字替换听写的字，只借听写的时间轴，错字基本没了。

用法：
  transcribe.py 口播.mov --out <用户的文件夹>                      只听写
  transcribe.py 口播.mov --script 逐字稿.docx --out <用户的文件夹>  听写 + 用逐字稿纠字
输出：<文件夹>/字幕_自动识别.srt。最后一行：STATUS=ok / STATUS=ok_script / STATUS=script_mismatch / STATUS=error
第一次会下载听写模型（约 550MB）到 ~/.cache/ariel-broll/，以后不再下。需要 whisper.cpp（Mac：brew install whisper-cpp）。
"""
import argparse, difflib, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.request

MODEL = 'ggml-large-v3-turbo-q5_0.bin'
CACHE = pathlib.Path.home() / '.cache' / 'ariel-broll'
URLS = [f'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{MODEL}',
        f'https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/{MODEL}']   # 国内连不上 huggingface 就走镜像
PUNCT = set('，。！？、；：,.!?;:…—-·「」『』“”"\'（）()《》【】[] \t\r\n　~～')


def die(msg):
    print(msg); print('STATUS=error'); sys.exit(1)


def model_path():
    p = CACHE / MODEL
    if p.exists() and p.stat().st_size > 500_000_000:
        return p
    CACHE.mkdir(parents=True, exist_ok=True)
    for u in URLS:
        print(f'第一次用，下载听写模型（约 550MB）：{u}', file=sys.stderr)
        tmp = p.with_suffix('.part')
        try:
            with urllib.request.urlopen(u, timeout=60) as r, open(tmp, 'wb') as f:
                total, got, last = int(r.headers.get('Content-Length') or 0), 0, -10
                while chunk := r.read(1 << 20):
                    f.write(chunk); got += len(chunk)
                    if total and got * 100 // total >= last + 10:
                        last = got * 100 // total; print(f'  {last}%', file=sys.stderr)
            if tmp.stat().st_size > 500_000_000:
                tmp.rename(p); return p
        except Exception as e:
            print(f'  这个地址失败：{e}', file=sys.stderr)
    die('听写模型下载失败（两个地址都连不上）。检查网络后重试。')


def ts(sec):
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def parse_srt(text):
    segs = []
    for blk in re.split(r'\n\s*\n', text.strip()):
        lines = blk.strip().splitlines()
        tl = next((i for i, l in enumerate(lines) if '-->' in l), None)
        if tl is None: continue
        a, b = [x.strip().replace(',', '.') for x in lines[tl].split('-->')]
        sec = lambda x: sum(float(v) * k for v, k in zip(x.split(':'), (3600, 60, 1)))
        t = ''.join(lines[tl + 1:]).strip()
        if t: segs.append([sec(a), sec(b), t])
    return segs


def read_script(p):
    p = pathlib.Path(p)
    if p.suffix.lower() == '.docx':
        if shutil.which('textutil'):
            return subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(p)], capture_output=True, text=True).stdout
        import zipfile
        x = zipfile.ZipFile(p).read('word/document.xml').decode('utf-8')
        return re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', '\n', x))
    return p.read_text(encoding='utf-8', errors='ignore')


def align(segs, script):
    """用逐字稿的字替换听写的字，时间轴不动。返回 (新字幕, 吻合度)。"""
    W, owner = [], []
    for i, s in enumerate(segs):
        for ch in s[2]:
            if ch not in PUNCT: W.append(ch); owner.append(i)
    S = [ch for ch in script if ch not in PUNCT]
    if not W or not S: return segs, 0.0
    sm = difflib.SequenceMatcher(None, W, S, autojunk=False)
    ops = sm.get_opcodes(); ratio = sm.ratio()
    bm = [None] * (len(W) + 1)   # bm[i] = 听写第 i 个字前面那条缝，对应逐字稿哪条缝
    for tag, i1, i2, j1, j2 in ops:
        for k in range(i1, i2):
            bm[k] = j1 + (k - i1 if tag == 'equal' else round((k - i1) * (j2 - j1) / max(1, i2 - i1)) if tag == 'replace' else 0)
    bm[len(W)] = len(S)
    eq = [o for o in ops if o[0] == 'equal']
    first, last = (eq[0][3], eq[-1][4]) if eq else (0, len(S))   # 逐字稿开头的标题、结尾的备注不算进来
    starts = {}
    for k, i in enumerate(owner):
        starts.setdefault(i, k)
    idx = sorted(starts)
    out = []
    for n, i in enumerate(idx):
        a = first if n == 0 else bm[starts[i]]
        b = last if n == len(idx) - 1 else bm[starts[idx[n + 1]]]
        a, b = max(a, first), min(max(b, a), last)
        out.append([segs[i][0], segs[i][1], ''.join(S[a:b]) or segs[i][2]])
    return out, ratio


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video'); ap.add_argument('--script'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    exe = shutil.which('whisper-cli') or shutil.which('whisper-cpp')
    if not exe: die('没装听写工具 whisper.cpp。Mac 上跑：brew install whisper-cpp')
    if not shutil.which('ffmpeg'): die('没装 ffmpeg。Mac 上跑：brew install ffmpeg')
    out = pathlib.Path(a.out).expanduser(); out.mkdir(parents=True, exist_ok=True)
    m = model_path()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='broll-asr-'))
    try:
        wav = tmp / 'a.wav'
        r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', a.video, '-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)])
        if r.returncode: die('从视频里取声音失败，视频可能坏了或没有声音。')
        print('开始听写（大约是视频时长的一半，7 分钟视频约 3 分钟）……', file=sys.stderr)
        r = subprocess.run([exe, '-m', str(m), '-l', 'zh', '--prompt', '以下是普通话的口播，使用简体中文。',
                            '-ml', '18', '-sow', '-osrt', '-of', str(tmp / 'o'), '-np', str(wav)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        srt = tmp / 'o.srt'
        if r.returncode or not srt.exists(): die('听写失败：' + (r.stderr or '')[-400:])
        segs = parse_srt(srt.read_text(encoding='utf-8'))
    finally:
        pass
    status = 'ok'
    if a.script:
        new, ratio = align(segs, read_script(a.script))
        print(f'逐字稿和听写的吻合度：{ratio:.0%}')
        if ratio >= 0.6: segs, status = new, 'ok_script'
        else: status = 'script_mismatch'; print('吻合度太低，逐字稿可能不是这一期，先只用听写结果。')
    dst = out / '字幕_自动识别.srt'
    dst.write_text(''.join(f'{i}\n{ts(s)} --> {ts(e)}\n{t}\n\n' for i, (s, e, t) in enumerate(segs, 1)), encoding='utf-8')
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'{len(segs)} 句，存在 {dst}')
    print(f'STATUS={status}')


if __name__ == '__main__':
    main()
