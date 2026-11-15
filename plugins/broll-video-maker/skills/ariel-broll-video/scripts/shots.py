#!/usr/bin/env python3
"""审稿分镜：把每处标黄按「完整的一两句」切成几张逐帧图（只用 Python 自带库）。

  python3 shots.py <工作> [--style <风格slug>] [--size 1080x1920]

读 <工作>/分镜.json（AI 按意思切好的）：{"B1": ["第一组原话", "第二组原话", ...], "B2": [...]}
  - 每组是一两句完整的话，能单独画成一个画面；不许把上一句的尾巴和下一句的开头拼成一组。
  - 每处所有组按顺序拼起来，必须和标黄原话一字不差（空格不算）。

检查通过后：
  - 用 逐字时间.json 算每组开始的那一秒，取「这组说完前 0.3 秒」当逐帧图时间（相对这一处开头）
  - 打印每处的 KEYTIMES（写进 逐帧代码/Bx.html 的 window.KEYTIMES）
  - 写 <工作>/逐帧审稿.json（每处几张图，每张只配那一组原话）
最后一行 STATUS=ok；有问题打印哪一处哪里对不上，STATUS=mismatch。
"""
import json, os, sys


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return
    work = a[0]
    style = a[a.index("--style") + 1] if "--style" in a else ""
    size = a[a.index("--size") + 1] if "--size" in a else ""
    if not size:
        size = (json.load(open(os.path.join(work, "格式.json"))) if os.path.exists(os.path.join(work, "格式.json")) else {}).get("size", "1080x1920")
    p = lambda n: os.path.join(work, n)
    res = json.load(open(p("标黄结果.json"), encoding="utf-8"))["result"]
    groups = json.load(open(p("分镜.json"), encoding="utf-8"))
    w = json.load(open(p("逐字时间.json"), encoding="utf-8"))
    chars = "".join(c for c, _ in w); T = [t for _, t in w]
    sq = lambda s: "".join(str(s).split())
    fmt = lambda s: "%02d:%02d" % (int(s) // 60, int(s) % 60)
    bad, rows, kts = [], [], {}
    for r in res:
        no, a0, e0 = r["no"], r["startTime"], r["endTime"]
        gs = groups.get(no) or [r["text"]]
        if sq("".join(gs)) != sq(r["text"]):
            full, got = sq(r["text"]), sq("".join(gs))
            k = next((i for i in range(min(len(full), len(got))) if full[i] != got[i]), min(len(full), len(got)))
            bad.append(f"{no}：分组拼起来和原话对不上，从第 {k} 个字开始：原话「{full[k:k+12]}」/ 分组「{got[k:k+12]}」"); continue
        # 这一处在逐字稿里从哪开始
        i0 = min(range(len(T)), key=lambda i: abs(T[i] - a0)); pos = i0; starts = []
        for g in gs:
            k = chars.find(sq(g)[:4], pos)
            k = pos if k < 0 or k - pos > 40 else k
            starts.append(T[k] if k < len(T) else e0); pos = k + max(1, len(sq(g)) - 8)   # 听写的字数可能和原话差几个，留点余量，免得越过下一组开头
        starts.append(e0)
        kt = [round(max(starts[j] - a0 + 0.3, starts[j + 1] - a0 - 0.3), 2) for j in range(len(gs))]
        kts[no] = kt
        rows.append({"no": no, "text": r["text"], "time": fmt(a0), "page": f"逐帧代码/{no}.html",
                     "frames": [{"img": f"逐帧图/{no}/{j + 1}.png", "text": g, "time": fmt(starts[j])} for j, g in enumerate(gs)]})
        print(f"{no}：{len(gs)} 张  KEYTIMES={json.dumps(kt)}")
    if bad:
        print("\n".join(bad)); print("STATUS=mismatch"); return
    out = {"size": size, "rows": rows}
    if style:
        out["style"] = style
    json.dump(out, open(p("逐帧审稿.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(kts, open(p("分镜时间.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("STATUS=ok")


if __name__ == "__main__":
    main()
