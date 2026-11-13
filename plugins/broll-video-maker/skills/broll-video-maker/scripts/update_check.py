#!/usr/bin/env python3
"""每次开工前查一下有没有新版本，有就自己更新（只用 Python 自带库）。

用法：python3 update_check.py
打印一行结论，最后一行是 STATUS=latest / updated / outdated / offline。
- Claude Code / Codex：看到新版本就直接跑更新命令，下次对话生效。
- Claude 桌面 app / 网页版：作者合并新版本后会自动同步，这里只提示。
查不到（没网）就跳过，不影响干活。
"""
import json, os, shutil, subprocess, sys, urllib.request

REPO = "kkkariel888/ariel-broll-video"
MARKET = "ariel-broll-video"
PLUGIN = "broll-video-maker"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/plugins/{PLUGIN}/.claude-plugin/plugin.json"
HERE = os.path.dirname(os.path.abspath(__file__))


def local_version():
    p = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".claude-plugin", "plugin.json"))
    try:
        return json.load(open(p, encoding="utf-8")).get("version", "0")
    except Exception:
        return "0"


def remote_version():
    try:
        with urllib.request.urlopen(RAW, timeout=6) as r:
            return json.loads(r.read().decode("utf-8")).get("version")
    except Exception:
        return None


def vt(v):
    return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=180).returncode == 0
    except Exception:
        return False


def main():
    mine, latest = local_version(), remote_version()
    if not latest:
        print("查不到新版本（可能没网），先用现在这版。\nSTATUS=offline")
        return
    if vt(latest) <= vt(mine):
        print(f"已是最新版 {mine}。\nSTATUS=latest")
        return
    done = False
    if shutil.which("claude"):
        done = run(["claude", "plugin", "marketplace", "update", MARKET]) and \
               run(["claude", "plugin", "update", f"{PLUGIN}@{MARKET}"]) or done
    if shutil.which("codex"):
        done = run(["codex", "plugin", "marketplace", "upgrade", MARKET]) or done
    if done:
        print(f"发现新版本 {latest}（现在 {mine}），已自动更新，下次开新对话生效。这次先用旧版干活。\nSTATUS=updated")
    else:
        print(f"发现新版本 {latest}（现在 {mine}）。用 Claude 桌面 app / 网页版的话会自动同步；"
              f"其他情况请让 AI 帮你更新插件 {PLUGIN}@{MARKET}。这次先用旧版干活。\nSTATUS=outdated")


if __name__ == "__main__":
    main()
