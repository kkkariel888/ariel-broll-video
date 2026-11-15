#!/usr/bin/env python3
"""门铃：等用户在页面上点下一下（只用 Python 自带库）。

  python3 wait_page.py <工作文件夹> [--for mode,confirm,pick,...] [--timeout 1800]

用户在页面上点的每一下，highlight_server.py 都记进 <工作文件夹>/事件.jsonl。这个脚本一直等，
等到有新的一下（--for 只等这几种）就打印出来退出——AI 就被叫醒了，不用用户回对话发消息。
  Claude Code / Claude 桌面 app：后台运行（run_in_background），AI 照常干活，用户一点，AI 自动被叫醒
  Codex：直接运行，它会等到用户点了才返回
已经看过的记在 事件.seen，不会重复叫。
  --file 模式.json   只等 <工作文件夹> 里出现这个文件（不读、不标记事件，给子任务用：不会抢走主 AI 的门铃）
最后一行：STATUS=event（下面是新的事件，每行一个 JSON）/ STATUS=timeout（等太久，没人点）
事件种类：mode（文字/动画）confirm（确认标黄）pick（选了风格）more（再来 3 个风格）save_style（存进我的风格）
          review（某个画面通过 / 要改）approve_all（全部通过，出片）
"""
import argparse, json, os, sys, time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("--for", dest="kinds", default="")
    ap.add_argument("--timeout", type=float, default=1800); ap.add_argument("--file")
    a = ap.parse_args()
    if a.file:
        t0, fp = time.time(), os.path.join(a.work, a.file)
        while not os.path.exists(fp):
            if time.time() - t0 > a.timeout:
                print("STATUS=timeout"); return
            time.sleep(0.4)
        print(open(fp, encoding="utf-8").read().strip()); print("STATUS=event"); return
    ev_path = os.path.join(a.work, "事件.jsonl")
    seen_path = os.path.join(a.work, "事件.seen")
    kinds = {k.strip() for k in a.kinds.split(",") if k.strip()}
    try:
        seen = int(open(seen_path).read().strip() or 0)
    except Exception:
        seen = 0
    t0 = time.time()
    while True:
        lines = []
        if os.path.exists(ev_path):
            with open(ev_path, encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
        new = lines[seen:]
        hits = []
        for l in new:
            try:
                e = json.loads(l)
            except Exception:
                continue
            if not kinds or e.get("act") in kinds:
                hits.append(e)
        if hits:
            with open(seen_path, "w") as f:
                f.write(str(len(lines)))
            for e in hits:
                print(json.dumps(e, ensure_ascii=False))
            print("STATUS=event"); return
        if new and kinds:
            with open(seen_path, "w") as f:   # 不关心的事件也算看过
                f.write(str(len(lines)))
            seen = len(lines)
        if time.time() - t0 > a.timeout:
            print("STATUS=timeout"); return
        time.sleep(0.4)


if __name__ == "__main__":
    main()
