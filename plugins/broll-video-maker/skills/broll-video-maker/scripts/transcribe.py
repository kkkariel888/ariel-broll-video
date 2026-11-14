#!/usr/bin/env python3
"""没有 SRT 时用：在本机把口播视频听写成带时间的字幕（不上传，只用 CPU，Claude Code / Cowork / Codex 都能跑）。
有逐字稿（.docx / .txt / .md）就用逐字稿的字和标点，只借听写的时间，错字基本没有；逐字稿里视频没说的句子自动跳过。

用法：
  transcribe.py 口播.mov --out <用户的文件夹>                      只听写
  transcribe.py 口播.mov --script 逐字稿.docx --out <用户的文件夹>  听写 + 用逐字稿纠字
输出：
  <文件夹>/字幕_自动识别.srt   一句一行，后面当 SRT 用
  <文件夹>/逐字时间.json       每个字说出来的那一秒，[[字, 秒], ...]，卡关键词用
最后一行：STATUS=ok / ok_script / script_mismatch / error

听写引擎：SenseVoice（sherpa-onnx，Apache-2.0）。第一次自动装 Python 包（约 20MB，来自 PyPI）、
下载模型（约 160MB，来自 GitHub），存在 ~/.cache/ariel-broll/，以后不再下。7 分钟视频约 20 秒听完。
"""
import argparse, difflib, json, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile, time, urllib.request, wave

MODEL_NAME = 'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17'
BASE = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'
PUNCT = set('，。！？、；：,.!?;:…—-·「」『』“”"\'（）()《》【】[] \t\r\n　~～')
BREAK = set('，。！？；：,.!?;:…\n')


def say(*a):
    print(*a, file=sys.stderr, flush=True)


def die(msg):
    print(msg); print('STATUS=error'); sys.exit(1)


def cache_dir():
    for d in [os.environ.get('ARIEL_BROLL_CACHE'), pathlib.Path.home() / '.cache' / 'ariel-broll',
              pathlib.Path(tempfile.gettempdir()) / 'ariel-broll']:
        if not d: continue
        d = pathlib.Path(d)
        try:
            d.mkdir(parents=True, exist_ok=True); (d / '.w').write_text('1'); (d / '.w').unlink()
            return d
        except Exception:
            continue
    die('找不到能写的缓存文件夹。')


def load_engine(cache):
    """装 sherpa-onnx + numpy 到缓存里的独立文件夹（不动系统 Python），然后导入。"""
    lib = cache / f'pylib-py{sys.version_info[0]}{sys.version_info[1]}'
    sys.path.insert(0, str(lib))
    try:
        import numpy, sherpa_onnx  # noqa
        return
    except ImportError:
        pass
    say('第一次用：安装听写引擎（约 20MB）……')
    base = [sys.executable, '-m', 'pip', 'install', '-q', '--disable-pip-version-check', '--target', str(lib), 'sherpa-onnx', 'numpy']
    r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode and 'externally-managed' in (r.stderr + r.stdout):
        r = subprocess.run(base + ['--break-system-packages'], capture_output=True, text=True)
    if r.returncode and 'No module named pip' in r.stderr:
        subprocess.run([sys.executable, '-m', 'ensurepip', '--user'], capture_output=True)
        r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode:
        die('安装听写引擎失败（要能访问 pypi.org）：' + (r.stderr or r.stdout)[-500:])
    import importlib; importlib.invalidate_caches()
    try:
        import numpy, sherpa_onnx  # noqa
    except ImportError as e:
        die(f'听写引擎装上了但用不了：{e}')


def fetch(url, dst):
    tmp = dst.with_name(dst.name + '.part')
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, 'wb') as f:
        total, got, last = int(r.headers.get('Content-Length') or 0), 0, -25
        while chunk := r.read(1 << 20):
            f.write(chunk); got += len(chunk)
            if total and got * 100 // total >= last + 25:
                last = got * 100 // total; say(f'  {last}%')
    tmp.rename(dst)


def model_files(cache):
    d = cache / MODEL_NAME
    vad = cache / 'silero_vad.onnx'
    try:
        if not (d / 'model.int8.onnx').exists():
            say('第一次用：下载听写模型（约 160MB，来自 GitHub）……')
            tb = cache / (MODEL_NAME + '.tar.bz2')
            fetch(BASE + MODEL_NAME + '.tar.bz2', tb)
            with tarfile.open(tb) as t:
                t.extractall(cache, members=[m for m in t.getmembers() if m.name.endswith(('model.int8.onnx', 'tokens.txt', 'LICENSE'))])
            tb.unlink()
        if not vad.exists():
            fetch(BASE + 'silero_vad.onnx', vad)
    except Exception as e:
        die(f'下载听写模型失败（要能访问 github.com 和 objects.githubusercontent.com）：{e}')
    return d / 'model.int8.onnx', d / 'tokens.txt', vad


def read_audio(video, tmp):
    import numpy as np
    ff = shutil.which('ffmpeg')
    if not ff: die('没装 ffmpeg。Mac：brew install ffmpeg；Linux：apt-get install -y ffmpeg')
    wav = tmp / 'a.wav'
    r = subprocess.run([ff, '-loglevel', 'error', '-y', '-i', str(video), '-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)])
    if r.returncode or not wav.exists(): die('从视频里取声音失败，视频可能坏了或没有声音。')
    w = wave.open(str(wav))
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def recognize(audio, model, tokens, vad_model):
    """返回 [(字, 秒)] 和每个字所在那段话的结束时间。"""
    import numpy as np, sherpa_onnx as so
    rec = so.OfflineRecognizer.from_sense_voice(model=str(model), tokens=str(tokens), num_threads=min(4, os.cpu_count() or 2),
                                                language='zh', use_itn=False, provider='cpu')
    cfg = so.VadModelConfig(); cfg.silero_vad.model = str(vad_model); cfg.sample_rate = 16000
    cfg.silero_vad.min_silence_duration = 0.2; cfg.silero_vad.max_speech_duration = 8
    vad = so.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)
    segs, ws = [], cfg.silero_vad.window_size

    def drain():
        while not vad.empty():
            s = vad.front; segs.append((s.start / 16000, np.array(s.samples))); vad.pop()
    for i in range(0, len(audio), ws):
        vad.accept_waveform(audio[i:i + ws]); drain()
    vad.flush(); drain()
    chars, ends = [], []
    for st, smp in segs:
        s = rec.create_stream(); s.accept_waveform(16000, smp); rec.decode_stream(s)
        r, end = s.result, st + len(smp) / 16000
        for tk, t in zip(r.tokens, r.timestamps):
            for ch in tk.strip():
                if ch not in PUNCT and not ch.startswith('<'):
                    chars.append((ch, round(st + t, 3))); ends.append(end)
    return chars, ends


def read_script(p):
    p = pathlib.Path(p)
    if p.suffix.lower() == '.docx':
        if shutil.which('textutil'):
            return subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(p)], capture_output=True, text=True).stdout
        import zipfile
        x = zipfile.ZipFile(p).read('word/document.xml').decode('utf-8')
        return re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', '\n', x))
    return p.read_text(encoding='utf-8', errors='ignore')


def lines_from_asr(chars, ends):
    """没有逐字稿：按说话的停顿分行；一行超过 16 个字，从里面停顿最长的地方断开。"""
    groups, cur = [], []
    for i, (ch, t) in enumerate(chars):
        cur.append(i)
        nxt = chars[i + 1][1] if i + 1 < len(chars) else None
        if nxt is None or ends[i] != ends[i + 1] or nxt - t > 0.8:
            groups.append(cur); cur = []
    idx = []
    while groups:
        g = groups.pop(0)
        if len(g) <= 16: idx.append(g); continue
        cut = max(range(len(g) // 3, len(g) - len(g) // 3), key=lambda k: chars[g[k]][1] - chars[g[k - 1]][1])
        groups[:0] = [g[:cut], g[cut:]]
    return finish([[chars[g[0]][1], chars[g[-1]][1], ''.join(chars[x][0] for x in g), ends[g[-1]]] for g in idx])


def finish(rows):
    """[开始, 最后一个字, 文字, 这段话结束] → [开始, 结束, 文字]，结束不超过下一句开始。"""
    merged = []                  # 「哎」「对」这种一两个字的行，并到前一句
    for r in rows:
        if merged and len(r[2]) <= 2 and r[0] - merged[-1][1] < 0.8 and len(merged[-1][2]) < 24:
            merged[-1] = [merged[-1][0], r[1], merged[-1][2] + r[2], r[3]]
        else:
            merged.append(list(r))
    rows = merged
    for n in range(1, len(rows)):  # 开始时间不能倒着走
        rows[n][0] = max(rows[n][0], rows[n - 1][0] + 0.05); rows[n][1] = max(rows[n][1], rows[n][0])
    out = []
    for n, (st, last, text, seg_end) in enumerate(rows):
        nxt = rows[n + 1][0] if n + 1 < len(rows) else None
        end = min(seg_end, last + 0.6)
        if nxt is not None:
            end = nxt if nxt - last < 0.6 else min(end, nxt)
        end = max(end, st + 0.2)
        if nxt is not None: end = min(end, nxt)
        out.append([st, end, text])
    return out


def lines_from_script(chars, ends, script):
    """有逐字稿：用逐字稿的字，按逐字稿的标点断句，时间来自听写。视频里没说的句子跳过。"""
    S, sbreak = [], []           # 逐字稿的字；每个字后面是不是断句
    for ch in script:
        if ch in BREAK and S: sbreak[-1] = True
        elif ch not in PUNCT: S.append(ch); sbreak.append(False)
    C = [c for c, _ in chars]
    sm = difflib.SequenceMatcher(None, C, S, autojunk=False)
    match = sum(b.size for b in sm.get_matching_blocks())
    ratio = match / max(1, len(C))
    st = [None] * len(S); en = [None] * len(S)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 > i1):
            for k in range(j1, j2):
                i = i1 + (k - j1 if tag == 'equal' else (k - j1) * (i2 - i1) // (j2 - j1))
                st[k] = chars[i][1]; en[k] = ends[i]
    nb = [0] * len(S)            # 离下一个断句还有几个字
    for k in range(len(S) - 1, -1, -1):
        nb[k] = 0 if sbreak[k] or k == len(S) - 1 else nb[k + 1] + 1
    rows, cur = [], []
    for k, ch in enumerate(S):
        cur.append(k)
        if sbreak[k] or k == len(S) - 1 or (len(cur) >= 18 and nb[k] >= 6):
            spoken = [x for x in cur if st[x] is not None]
            if spoken:
                rows.append([st[spoken[0]], st[spoken[-1]], ''.join(S[x] for x in cur), en[spoken[-1]]])
            cur = []
    return finish(rows), ratio


def ts(sec):
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video'); ap.add_argument('--script'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out).expanduser(); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cache = cache_dir()
    load_engine(cache)
    model, tokens, vad = model_files(cache)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='broll-asr-'))
    try:
        say('开始听写……')
        chars, ends = recognize(read_audio(a.video, tmp), model, tokens, vad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not chars: die('没听到说话声。视频是不是没声音？')
    status, lines = 'ok', None
    if a.script:
        lines, ratio = lines_from_script(chars, ends, read_script(a.script))
        print(f'逐字稿和听写的吻合度：{ratio:.0%}')
        if ratio >= 0.6: status = 'ok_script'
        else: status, lines = 'script_mismatch', None; print('吻合度太低，逐字稿可能不是这一期，先只用听写结果。')
    lines = lines or lines_from_asr(chars, ends)
    (out / '字幕_自动识别.srt').write_text(''.join(f'{i}\n{ts(s)} --> {ts(e)}\n{t}\n\n' for i, (s, e, t) in enumerate(lines, 1)), encoding='utf-8')
    (out / '逐字时间.json').write_text(json.dumps(chars, ensure_ascii=False), encoding='utf-8')
    print(f'{len(lines)} 句，用时 {time.time() - t0:.0f} 秒，存在 {out / "字幕_自动识别.srt"}')
    print(f'STATUS={status}')


if __name__ == '__main__':
    main()
