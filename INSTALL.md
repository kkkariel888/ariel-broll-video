# 给 AI 助手的安装说明（Claude 和 Codex 通用）

> 用户把这个仓库链接发给你，说「帮我装上」，你就照下面做完，**一次做完，不要分几轮问**。
> 跟用户说话用中文、大白话；只有真的需要用户本人点一下的，才停下来叫他。

这个仓库同时是 Claude 和 Codex 的插件市场：
- Claude 读 `.claude-plugin/marketplace.json`，插件信息在 `plugins/<名字>/.claude-plugin/plugin.json`
- Codex 读 `.agents/plugins/marketplace.json`，插件信息在 `plugins/<名字>/.codex-plugin/plugin.json`
- 两边用的是同一份 skill：`plugins/broll-video-maker/skills/broll-video-maker/`

## 1. 能跑命令（Claude Code、Codex 命令行、Codex 桌面 app、连着电脑的 Claude app）：一条命令装好全部
```bash
git clone --depth 1 https://github.com/kkkariel888/ariel-skills.git /tmp/ariel-skills && bash /tmp/ariel-skills/install.sh
```
它会：
1. 检查并安装 git、python3、ffmpeg，检查 Chrome
2. 下载 Lemo-Opuscar 风格库到 `~/lemo-opuscar`
3. 找到 Claude Code 就：添加插件市场、安装 `broll-video-maker`、**打开自动更新**
4. 找到 Codex（命令行版，或 Codex 桌面 app 自带的）就：添加插件市场、安装 `broll-video-maker`。Codex 每次启动都会自己拉最新版，不用额外设置
5. 最后打印「好了的」和「还要你点一下的」两张清单。把跟用户环境有关的那几条原样告诉他

只能用户自己来的情况（照实说，别假装装好了）：
- Mac 第一次用 git：屏幕会弹「安装命令行开发者工具」，用户点「安装」，装完你再跑一次
- Mac 没有 Homebrew：装它要用户输一次开机密码
- 连不上 GitHub：等网络好了再跑

## 2. Claude 桌面 app / 网页版：在 app 里添加一次
1. Customize → Plugins → Add marketplace（从 GitHub 仓库添加）
2. 粘贴 `kkkariel888/ariel-skills`，**勾上 Sync automatically（自动同步）**
3. 装 `broll-video-maker`

能控制浏览器就直接帮用户打开页面填好；不能就把这 3 步发给用户。
如果这个对话也能跑命令，第 1 步照样跑，用来装 ffmpeg 等工具和风格库。

## 装完以后：作者一更新，所有人自动变新
| 用户在用什么 | 怎么自动更新 |
|---|---|
| Claude 桌面 app / 网页版 | 作者合并新版本后自动同步（第 2 步勾的那个） |
| Claude Code | 第 1 步已打开自动更新，下次开新对话就是新版 |
| Codex（命令行或桌面 app） | 每次启动自己拉最新版 |

另外 skill 每次开工前会自己查一下有没有新版本，有就顺手更新，算第二道保险。
第一次真正用的时候，skill 还会再检查一遍工具和风格库，缺什么补什么。
