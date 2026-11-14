#!/usr/bin/env bash
# 一键准备 ariel-broll-video 需要的一切（macOS / Linux）。给 AI 助手跑的，也可以自己跑。
# 用法：bash install.sh            # 全装
#       bash install.sh --check    # 只检查，不装
# 做的事：
#   1. 检查并安装 git、python3、ffmpeg；检查 Chrome / Edge
#   2. 下载 Lemo-Opuscar 风格库到 ~/lemo-opuscar
#   3. 本机有 Claude Code 就：添加插件市场 + 安装 broll-video-maker + 打开自动更新
#      本机有 Codex 就：添加插件市场 + 安装
#   4. 最后打印一张清单：哪些好了、哪些还要用户点一下
set -u
REPO="kkkariel888/ariel-broll-video"
MARKET="ariel-broll-video"
PLUGIN="broll-video-maker"
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1

ok=();  todo=()
say(){ printf '%s\n' "$*"; }
have(){ command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"

brew_install(){ # $1 = 包名
  if [ "$OS" = "Darwin" ]; then
    if ! have brew; then
      todo+=("装 Homebrew（Mac 的装软件工具）：在「终端」粘贴 /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"，会让你输一次开机密码")
      return 1
    fi
    brew install "$1" >/dev/null 2>&1 && return 0
  elif have apt-get; then
    sudo apt-get install -y "$1" >/dev/null 2>&1 && return 0
  elif have dnf; then
    sudo dnf install -y "$1" >/dev/null 2>&1 && return 0
  fi
  return 1
}

need(){ # $1 = 命令  $2 = 包名  $3 = 中文说明
  if have "$1"; then ok+=("$3"); return 0; fi
  if [ $CHECK_ONLY = 1 ]; then todo+=("缺 $3"); return 1; fi
  if [ "$OS" = "Darwin" ] && [ "$1" = "git" ]; then
    xcode-select --install >/dev/null 2>&1
    todo+=("屏幕上弹出「安装命令行开发者工具」，点「安装」，装完再跑一次")
    return 1
  fi
  say "正在装 $3 …"
  if brew_install "$2" && have "$1"; then ok+=("$3（刚装好）"); else todo+=("$3 没装上，手动装：Mac 用 brew install $2"); fi
}

say "== 1/3 检查基础工具 =="
need git git "git（下载工具）"
need python3 python3 "python3"
need ffmpeg ffmpeg "ffmpeg（剪视频工具）"

chrome=""
for p in "/Applications/Google Chrome.app" "/Applications/Microsoft Edge.app" "/Applications/Chromium.app"; do [ -d "$p" ] && chrome="$p"; done
for c in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge; do have "$c" && chrome="$c"; done
if [ -n "$chrome" ]; then ok+=("Chrome / Edge（画画面用）"); else todo+=("装一个 Chrome：https://www.google.com/chrome/ （画画面要用）"); fi

say "== 2/3 下载风格库 =="
if [ $CHECK_ONLY = 0 ] && have git && have python3; then
  tmp="$(mktemp -d)"
  if git clone --depth 1 --filter=blob:none --sparse "https://github.com/$REPO.git" "$tmp/r" >/dev/null 2>&1 \
     && git -C "$tmp/r" sparse-checkout set "plugins/$PLUGIN/skills/$PLUGIN/scripts" >/dev/null 2>&1 \
     && python3 "$tmp/r/plugins/$PLUGIN/skills/$PLUGIN/scripts/lemo.py" ensure; then
    ok+=("Lemo-Opuscar 风格库（~/lemo-opuscar）")
  else
    todo+=("风格库没下载成功（多半是连不上 GitHub），网络好了再跑一次")
  fi
  rm -rf "$tmp"
elif [ -d "$HOME/lemo-opuscar/styles" ]; then ok+=("Lemo-Opuscar 风格库"); else todo+=("缺风格库"); fi

say "== 3/3 装插件并打开自动更新 =="
if have claude; then
  if [ $CHECK_ONLY = 0 ]; then
    claude plugin marketplace add "$REPO" >/dev/null 2>&1
    claude plugin install "$PLUGIN@$MARKET" >/dev/null 2>&1
    # 打开自动更新：写进 ~/.claude/settings.json 的 extraKnownMarketplaces.<市场>.autoUpdate
    python3 - "$MARKET" "$REPO" <<'PY'
import json, os, sys
market, repo = sys.argv[1], sys.argv[2]
d = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
p = os.path.join(d, "settings.json")
try: s = json.load(open(p))
except Exception: s = {}
m = s.setdefault("extraKnownMarketplaces", {}).setdefault(market, {})
m.setdefault("source", {"source": "github", "repo": repo})
m["autoUpdate"] = True
os.makedirs(d, exist_ok=True)
json.dump(s, open(p, "w"), ensure_ascii=False, indent=2)
PY
  fi
  if claude plugin list 2>/dev/null | grep -q "$PLUGIN@$MARKET"; then ok+=("Claude Code：已装 $PLUGIN，自动更新已打开"); else todo+=("Claude Code 里没装上 $PLUGIN"); fi
fi
# Codex：命令行版或 Codex 桌面 app 自带的命令行（两者共用 ~/.codex，装一次两边都有）
CODEX=""
have codex && CODEX="codex"
[ -z "$CODEX" ] && [ -x "/Applications/Codex.app/Contents/Resources/codex" ] && CODEX="/Applications/Codex.app/Contents/Resources/codex"
if [ -n "$CODEX" ]; then
  if [ $CHECK_ONLY = 0 ]; then
    "$CODEX" plugin marketplace add "$REPO" >/dev/null 2>&1
    "$CODEX" plugin add "$PLUGIN@$MARKET" >/dev/null 2>&1
  fi
  if "$CODEX" plugin list 2>/dev/null | grep -q "$PLUGIN"; then
    ok+=("Codex：已装 $PLUGIN（Codex 每次启动会自己拉最新版，不用设置）")
  else
    todo+=("Codex 里没装上 $PLUGIN：在 Codex 里打开 Plugins → Add marketplace → 粘贴 $REPO → 装 $PLUGIN")
  fi
fi
if [ -z "$CODEX" ] && ! have claude; then
  todo+=("没找到 Claude Code 或 Codex 的命令行：如果你用的是 Codex 桌面 app，在 Plugins → Add marketplace 粘贴 $REPO 再装 $PLUGIN")
fi
todo+=("如果你用的是 Claude 桌面 app / 网页版：Customize → Plugins → Add marketplace → 粘贴 $REPO，勾上「Sync automatically」→ 装 $PLUGIN（这一步只能在 app 里点，AI 可以帮你打开页面）")

say ""
say "== 好了的 =="
for x in "${ok[@]}"; do say "  ✓ $x"; done
say "== 还要你点一下的 =="
for x in "${todo[@]}"; do say "  · $x"; done
