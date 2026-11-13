<a id="readme-top"></a>

<div align="center">

<h1>ariel-broll-video</h1>

<p><strong>给口播视频配「代码动画 B-roll」的 AI skill</strong><br>
你只管把剪映导出的字幕和视频丢进一个文件夹，剩下的审稿、挑风格、画画面、对齐语速、出片，AI 带着你点几下就做完。</p>

<p>
<img alt="版本" src="https://img.shields.io/badge/version-1.1.2-blue?style=flat-square">
<img alt="Claude" src="https://img.shields.io/badge/Claude-桌面%20%7C%20网页%20%7C%20Code-D97757?style=flat-square">
<img alt="Codex" src="https://img.shields.io/badge/Codex-命令行%20%7C%20桌面-000000?style=flat-square">
<img alt="License" src="https://img.shields.io/github/license/kkkariel888/ariel-broll-video?style=flat-square">
<img alt="Stars" src="https://img.shields.io/github/stars/kkkariel888/ariel-broll-video?style=flat-square">
</p>

<p>
<a href="#快速开始">快速开始</a> ·
<a href="#它是怎么工作的">工作流程</a> ·
<a href="#常见问题">常见问题</a> ·
<a href="https://github.com/kkkariel888/ariel-broll-video/issues">反馈问题</a>
</p>

</div>

---

> **一句话装好：** 复制下面这句话发给你的 Claude 或 Codex 就行。
>
> ```
> 帮我装上这个：https://github.com/kkkariel888/ariel-broll-video
> ```
>
> 装一次，以后作者每次更新，你那边自动变成最新版。

<details>
<summary><strong>目录</strong></summary>

1. [这是什么](#这是什么)
2. [它能做到什么](#它能做到什么)
3. [快速开始](#快速开始)
4. [怎么用](#怎么用)
5. [它是怎么工作的](#它是怎么工作的)
6. [风格从哪来](#风格从哪来)
7. [版权和安全](#版权和安全)
8. [自动更新](#自动更新)
9. [常见问题](#常见问题)
10. [路线图](#路线图)
11. [参与贡献](#参与贡献)
12. [许可证](#许可证)
13. [致谢](#致谢)

</details>

## 这是什么

**B-roll** 是你讲话时穿插进去、帮观众看懂的辅助画面：讲到数字时柱子弹起来，讲到步骤时一步步亮起来。

以前做 B-roll 要自己想每一帧画什么、再一点点剪。这个 skill 让 AI 来做这件事：它读你的字幕，挑出该配画面的地方，按一个统一的高级风格**用代码一张张画出来**，再卡着你说话的节奏做成动画片段。

- **skill 是什么**：写给 AI 的一本固定工作说明书。装上以后，AI 每次做视频都按同一套规矩来，不用你每次从头交代。
- **为什么用代码画**：AI 写一段代码，规定第几秒出现什么、数字怎么滚。哪里不满意就改哪一句，改完重出，不用整段重来。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 它能做到什么

| | |
|---|---|
| ✍️ **审错别字** | 只改错别字和听写错误，不改你的说法、不动时间轴；另存一份修正版，能直接导回剪映 |
| 🖍️ **仿 Word 标黄** | 右边弹出一个像 Word 的页面，AI 先标好 8～15 处建议配画面的句子，你像用 Word 一样增删 |
| 🎨 **点一下选风格** | 从近百种开源影片风格里挑最合适的 3 个，**用你这期的原话**先画好样图，你点「就这个 / 换一个 / 用上次那个」 |
| 🖼️ **每个画面现画** | 不是套模板。每句话说什么就画什么，配色、字体、质感、动作节奏严格按选定的风格 |
| 🔍 **逐帧审稿** | 每处出 3 张关键帧（开场 / 最满 / 定格），一张张单独给你看，下面标着对应的那句原话。全部确认前不出视频 |
| ⏱️ **对齐语速** | 用字幕里的真实时间卡点，关键词在你说到的那一刻出现 |
| 🎞️ **画质只升不降** | 可以只要动画片段自己进剪映拼，也可以直接嵌进原视频；交付时列出前后的分辨率、帧率、码率给你对 |

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 快速开始

### 支持哪些软件

| 软件 | 支持 |
|---|---|
| Claude 桌面 app / 网页版 | ✅ |
| Claude Code | ✅ |
| Codex 命令行 / Codex 桌面 app | ✅ |

### 电脑上需要什么

不用自己装，AI 会帮你检查并装好：

- **git**：从 GitHub 下载东西用
- **ffmpeg**：处理视频的免费工具
- **Chrome 或 Edge**：把代码画成画面用
- **Lemo-Opuscar 风格库**：第一次用时自动下载到你电脑上，大约 30MB

### 安装

**方法一（推荐）：交给 AI**

把这句话发给你的 Claude 或 Codex：

```
帮我装上这个：https://github.com/kkkariel888/ariel-broll-video
```

AI 会照仓库里的 [INSTALL.md](INSTALL.md) 一口气装好全部东西，最后告诉你哪些好了、哪些还要你点一下。

需要你本人点的只有这几种情况，都是电脑出于安全必须你确认的：
- Mac 第一次装 git 会弹窗，点「安装」
- 装 Homebrew（Mac 上装软件的工具）要输一次开机密码
- 用 Claude 桌面 app 的话，要在设置里粘贴一次链接

**方法二：自己装**

<details>
<summary>展开看每个软件怎么装</summary>

**能用终端（Mac / Linux）**：一条命令装齐全部

```bash
git clone --depth 1 https://github.com/kkkariel888/ariel-broll-video.git /tmp/ariel-broll-video && bash /tmp/ariel-broll-video/install.sh
```

**Claude 桌面 app / 网页版**：Customize → Plugins → Add → Add marketplace → Add from a repository → 填 `kkkariel888/ariel-broll-video` → 打开 **Sync automatically** → Sync → 装 Broll video maker

**Claude Code**：

```
/plugin install broll-video-maker --marketplace kkkariel888/ariel-broll-video
```

**Codex 桌面 app**：Plugins → Add marketplace → 填 `kkkariel888/ariel-broll-video` → 装 broll-video-maker

**Codex 命令行**：

```bash
codex plugin marketplace add kkkariel888/ariel-broll-video
codex plugin add broll-video-maker@ariel-broll-video
```

</details>

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 怎么用

1. 在剪映里导出这期的**字幕（.srt）**和**口播视频**，放进同一个文件夹。
2. 对 AI 说一句：

   ```
   给这期配 B-roll，文件在：<你的文件夹>
   ```

   想指定风格，可以顺手加一句：
   - 「参考这张图的感觉」，再附一张你喜欢的图
   - 「用这个风格：<一个 GitHub 链接>」
   - 「用上次那个」

3. 接下来照着屏幕点就行。你全程要做的只有：**改标黄 → 点风格 → 审图 → 二选一出片**。只有想改某张图时才需要打字，比如「B3 第 2 张太花」。

做完以后，文件夹里会有：

```
字幕_修正.srt        改过错别字的字幕，能直接导回剪映
标黄逐字稿.docx      带黄色高亮的逐字稿
风格样图/            选风格时的样图
已确认逐帧图/        你审过的每一张图
成片/               动画片段（成片也会另存一份到桌面）
```

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 它是怎么工作的

| 步骤 | 你做什么 | AI 在后台做什么 |
|---|---|---|
| 1. 丢文件夹 | 放好字幕和视频，说一句话 | 自己看出是竖屏还是横屏、帧率多少，不问你 |
| 2. 审错别字 | 扫一眼「时间 / 原来 / 改成」小表 | 只改错别字，另存修正版 |
| 3. 标黄 | 在右边像 Word 一样增删标黄，点「确认」 | 你改的同时，已经在挑风格、画样图 |
| 4. 选风格 | 点「文字多 / 动画多」，再点「就这个 / 换一个」 | 用你这期的原话画 3 张样图 |
| 5. 审逐帧图 | 一张张看，哪张不对就说 | 每处标黄按风格单独画，出 3 张关键帧 |
| 6. 出片 | 二选一：只要片段，或嵌进原视频 | 卡着你的语速渲染，先出 1 段给你看 |
| 7. 拿成片 | 去桌面拿 | 整理好文件夹，中间草稿不留 |

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 风格从哪来

风格只选一次，像一个「菜系」：规定配色、字体、质感、动作节奏。每一处标黄说的内容不一样，AI 就按这个菜系一道一道现做，所以整期画面一看就是同一套。

| 来源 | 怎么用 | 说明 |
|---|---|---|
| **默认：Lemo-Opuscar 风格库** | 什么都不用给 | 近百种开源影片风格，每种都有一份很细的风格说明。AI 读完你的字幕，判断你在讲原理、比数字还是演示工具，挑最搭的 3 个 |
| **你的参考图** | 附一张你喜欢的图 | AI 提炼它的「风格 DNA」，做成你自己的新风格，以后也能再用 |
| **GitHub 上的风格链接** | 发一个链接 | AI 先查许可证，能用才用 |
| **用上次那个** | 说一句 | 频道调性期期一致 |

**风格 DNA 只学感觉，不抄图：**
- 只提取 8 样：主色、背景质感、版式留白、字体粗细、线条粗细、进场方式、动效节奏、几秒换一次画面
- 颜色是程序一个像素一个像素量出来的，不靠 AI「看」
- 不抄 logo、真人脸、品牌、角色和原图里的具体画面
- 出样图时自动出一张「参考图 vs 新风格」的对比图。觉得太像就说「再离远一点」

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 版权和安全

- **自动审查许可证**：你发别人的 GitHub 链接，AI 先读它的许可证，给出四种结论：**可以用 / 分块看 / 有限制 / 不能用**。没写许可证的默认不能用，公开不等于免费。
- **这个仓库里不带别人的东西**：Lemo-Opuscar 的风格说明不允许被打包进别的产品里发出去，但允许「读它、照它做你自己的片子」。所以这里一个字都没搬，而是让 AI 在你自己电脑上现下载、现读。
- **你做出来的片子归你**，商用也行，不用署名（Lemo 的许可证原文这么写）。
- **自动避开不能用的东西**：Lemo 里有一个风格要重画真实 App 的界面，还带着别家公司的小角色，这些商标不在它的授权里，skill 直接不选它。所有风格也都照它的说明，不画真实品牌的名字、界面和 logo。
- **不能拿去卖**：Lemo 的风格说明不能单独拿出来卖，也不能放进收费的产品或服务里。这个 skill 是免费开源的，只在你自己电脑上读它来做你的片子，在它允许的范围内。
- **字体**：风格里点名的免费开源字体会自动下载，许可证文件跟着字体一起放好。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 自动更新

| 你在用什么 | 怎么更新 |
|---|---|
| Claude 桌面 app / 网页版 | 作者发新版后自动同步（安装时打开的 Sync automatically） |
| Claude Code | 安装时已打开自动更新，下次开新对话就是新版 |
| Codex 命令行 / 桌面 app | 每次启动自动拉最新版 |

另外，skill 每次开工前会自己查一下有没有新版本，算第二道保险。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 常见问题

<details>
<summary><strong>「订阅」「关注」「Star」要做吗？</strong></summary>

都不用。把链接发给 AI 说「帮我装上」就够了。Star 只是给作者点个赞，跟能不能用、能不能更新没关系。

</details>

<details>
<summary><strong>风格库下载失败怎么办？</strong></summary>

多半是连不上 GitHub。AI 会停下来告诉你原因，网络好了说「重试」就行。它不会拿一个丑的保底风格糊弄你。

</details>

<details>
<summary><strong>会不会把我的视频画质弄差？</strong></summary>

不会。画质只能保持或更高，交付时会列出原片和成片的分辨率、帧率、码率给你对。选「只要动画片段」的话，原片一点都不动。

</details>

<details>
<summary><strong>Windows 能用吗？</strong></summary>

skill 本身能用。一键安装脚本目前只支持 Mac 和 Linux，Windows 上 AI 会改成一步步帮你装 git、ffmpeg。

</details>

<details>
<summary><strong>用网页版 Claude，「用上次那个」为什么记不住？</strong></summary>

网页版碰不到你的电脑，没地方存上次的选择。用 Claude 桌面 app 或 Codex 就能记住。

</details>

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 路线图

- [x] 审错别字 + 仿 Word 标黄
- [x] Lemo 风格库 / 参考图 DNA / GitHub 风格链接三种风格来源
- [x] 每个画面按风格现画 + 逐帧审稿
- [x] 一句话安装，Claude 和 Codex 都能自动更新
- [ ] Windows 一键安装
- [ ] 更多真实视频的完整测试

想要什么功能，欢迎到 [Issues](https://github.com/kkkariel888/ariel-broll-video/issues) 提。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 参与贡献

欢迎提建议、报问题、改代码：

1. 到 [Issues](https://github.com/kkkariel888/ariel-broll-video/issues) 说说你遇到的问题或想法
2. 想直接改：Fork 这个仓库 → 新建分支 → 改好后提 Pull Request（合并申请）

作者发新版时用 `python3 tools/bump.py`，一次改齐 Claude 和 Codex 两边的版本号。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 许可证

本仓库的代码用 [MIT 许可证](LICENSE)：可以随便用、改、商用，保留作者署名就行。

风格库 Lemo-Opuscar 不在本仓库里，用的时候从它的官方仓库下载，遵守它自己的许可证。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

## 致谢

- 风格库：[Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) by Lemomo (LemoLab)。风格说明采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)，并附加授权「读它、照它、改它来做你自己的片子（含商用片）」；代码采用 MIT。本仓库没有收录、也没有修改它的任何文件，使用时从官方仓库下载到你自己的电脑
- 思源黑体 / 思源宋体、霞鹜漫黑等开源字体（SIL OFL 1.1）
- 本 README 的结构参考了 [Best-README-Template](https://github.com/othneildrew/Best-README-Template)、[standard-readme](https://github.com/RichardLitt/standard-readme) 和 [Art of README](https://github.com/hackergrrl/art-of-readme)

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>
