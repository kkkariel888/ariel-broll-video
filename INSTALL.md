# 给 AI 助手的安装说明

> 用户把这个仓库链接发给你，说「帮我装上」，你就照下面做完，**一次做完，不要分几轮问**。
> 跟用户说话用中文、大白话；只有真的需要用户本人点一下的，才停下来叫他。

## 1. 先认出自己在哪个环境
- **Claude Code / Codex（能跑命令行）** → 做第 2 步。
- **Claude 桌面 app / 网页版（claude.ai）** → 做第 3 步；如果这个对话还能跑命令（连着用户电脑），第 2 步也做，用来装 ffmpeg 等工具和风格库。

## 2. 能跑命令行：一条命令装好全部
```bash
git clone --depth 1 https://github.com/kkkariel888/ariel-skills.git /tmp/ariel-skills && bash /tmp/ariel-skills/install.sh
```
它会：检查并安装 git、python3、ffmpeg，检查 Chrome；下载 Lemo-Opuscar 风格库；
在 Claude Code 里添加插件市场、安装 `broll-video-maker`、**打开自动更新**；在 Codex 里添加插件市场并安装。
最后它会打印「还要你点一下的」清单，把清单原样告诉用户（只说跟他的环境有关的那几条）。

会卡住、只能用户自己来的情况（照实说，别假装装好了）：
- Mac 第一次用 git：屏幕会弹「安装命令行开发者工具」，用户点「安装」，装完你再跑一次。
- Mac 没有 Homebrew：装它要用户输一次开机密码。
- 连不上 GitHub：等网络好了再跑。

## 3. Claude 桌面 app / 网页版：在 app 里添加一次
1. 打开 Customize → Plugins → Add marketplace（从 GitHub 仓库添加）。
2. 粘贴 `kkkariel888/ariel-skills`，**勾上 Sync automatically（自动同步）**。
3. 装 `broll-video-maker`。
你能控制浏览器就直接帮用户打开这个页面并填好；不能就把这 3 步发给用户，让他点。

## 装完以后
- 作者每发一个新版本，Claude app 会自动同步，Claude Code 会自动更新，Codex 每次开工时 skill 会自己查新版本并更新。用户什么都不用做。
- 第一次用的时候，skill 还会再检查一遍工具和风格库，缺什么补什么。
