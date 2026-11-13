#!/usr/bin/env python3
"""发新版本时用：一次改齐 Claude 和 Codex 两边的版本号。
用法：python3 tools/bump.py 1.1.1        （不写版本号就把最后一位 +1）
改完照常提合并申请，合并后：Claude app 自动同步、Claude Code 和 Codex 下次启动自动更新。
"""
import json, sys, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
FILES = [R/".claude-plugin/marketplace.json"] + sorted(R.glob("plugins/*/.claude-plugin/plugin.json")) + sorted(R.glob("plugins/*/.codex-plugin/plugin.json"))
def load(p): return json.loads(p.read_text(encoding="utf-8"))
cur = load(R/"plugins/broll-video-maker/.claude-plugin/plugin.json")["version"]
new = sys.argv[1] if len(sys.argv) > 1 else ".".join(cur.split(".")[:-1] + [str(int(cur.split(".")[-1]) + 1)])
for p in FILES:
    d = load(p)
    if "plugins" in d:
        for e in d["plugins"]:
            if "version" in e: e["version"] = new
    else:
        d["version"] = new
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{p.relative_to(R)} → {new}")
