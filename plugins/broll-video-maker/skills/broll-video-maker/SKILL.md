---
name: broll-video-maker
description: 用户给一个装着剪映 SRT 字幕和口播视频的文件夹，自动审错别字、在侧边仿 Word 页面标黄，再按内容推荐一个高级风格（5 个内置 + 参考图 + GitHub 导入）、用这期原话出样图点一下选定，每句自动配版式，出逐帧图、对齐语速出片。Claude 和 Codex 通用。
---

# 口播配动画 B-roll（1.1 · Claude / Codex 通用）

**说话方式**：少说话，直接干活。不寒暄、不解释流程、不复述用户的话。能让用户点的就不让用户打字；真要问，一次只问一个问题。用中文、大白话。

本 skill 文件夹里有：
- `scripts/highlight_server.py`：标黄 + 选风格小助手（只用 Python 自带库）
- `scripts/render.py`：**统一出图命令**，所有风格都走它（Python 自带库 + 本机 Chrome + ffmpeg）
- `scripts/styles_tool.py`：风格管家（验证上架、打分排名、参考图风格 DNA、我的风格、上次那个）
- `assets/highlighter.html`：仿 Word 的标黄页面，确认后接着选风格
- `styles/`：风格包，一个风格一个文件夹；`styles/_pending/README.md` 是待验证区和开源核验记录
- `references/style-dna.md`：参考图提炼风格的规矩

## 开工：读文件夹
用户会给一个文件夹，里面有剪映导出的字幕 `.srt` 和口播视频（都必需）。
用 `ffprobe` 读视频宽、高、帧率、时长。宽小于高就是竖屏 9:16，否则横屏 16:9。**不要问画幅。**

## 第 1 步：审错别字
- 只改错别字和听写错误（同音字、专有名词、数字写错）。不改说法，不加标点，不改时间轴。
- 原 SRT 不动，另存 `字幕_修正.srt`（能直接导回剪映）。
- 对话里用小表告诉用户：时间 | 原来 | 改成。没错就说「没发现错别字」。

## 第 2 步：侧边打开仿 Word 文档并标黄，同时把风格排好
1. 通读修正后的字幕，挑 8～15 处建议做 B-roll 的地方（有数字、有步骤、有对比、概念抽象、最想让观众记住的），原文一字不差写进 `建议标黄.json`（字符串数组）。
2. **给风格打分**（见第 5 步「打分」），写出 `风格排名.json`。必须在打开页面前写好，页面确认标黄后会直接用它。
3. 后台启动小助手（会一直运行）：
   `python3 <本skill>/scripts/highlight_server.py 字幕_修正.srt --suggest 建议标黄.json --out <用户的文件夹>`
4. 在侧边浏览器打开它打印的地址（见文末「在哪打开」）。

## 第 3 步：一句话交代，然后等
和错别字表放在同一条消息里，只说：

> 右边我先标了 N 处，直接改就行。改好点「确认标黄」，下面会让你点选「文字多 / 动画多」和风格，选好回来说一声。

「文字讲解多一点 / 纯动画多一点」和选风格都在页面上点，**不在对话里问**。

## 第 4 步：读结果
用户说好了，读文件夹里的：
- `标黄结果.json`：`confirmed` 为 true 才继续。`result` 每项一处：`no`（B1、B2…）、`text`、`startTime` / `endTime`（秒）。时间直接用。
- `风格选择.json`：`confirmed` 为 true 才继续。`style_id`、`path`（风格包位置）、`mode`（text = 文字多，anim = 动画多）、`sample`（样图用的那句）。
- 用户如果在对话里粘贴了「标黄结果（共 N 处）：…」，就用粘贴的内容；风格这时在对话里按下面「没有小助手时」处理。

## 第 5 步：风格（Agent 先读内容再挑，用户只点一下）

### 风格和版式是两回事
- **风格 = 长相**：配色、字体、质感、卡片、动效感觉。**一条视频只用一个风格**，整期统一。
- **版式 = 画面结构**：讲原理（编号卡片串起来）/ 比数字（柱子 + 数字滚动）/ 演示工具（窗口打字）/ 讲新闻（标题卡 + 荧光笔）/ 讲结论（大字逐行浮出）。**每一处标黄按这句话自动配**（`render.py` 里的 `pick_layout`：有数字→比数字，发布/宣布/日期→讲新闻，软件/工具/英文名→演示工具，所以/总之/记住→讲结论，其余→讲原理），Agent 可以用 `--layout` 改判。
- 所以一条视频里五类内容混着讲也没关系：风格选一次，版式每句自己配。某一张配得不合适，到逐帧审稿时单独改。

### 风格从哪来（三条路，最后都是同一种风格包）
1. **内置 5 个**（按气质分，参考 YouTube 顶尖动效频道的感觉自研，不含原图素材）：
   | id | 名字 | 气质 | 学的是谁的感觉 |
   |---|---|---|---|
   | deep-glass | 深空玻璃 | 深色、柔光、毛玻璃，克制又贵 | Apple 发布会、Cleo Abram |
   | editorial-paper | 编辑部纸感 | 米色纸、宋体大标题、荧光笔划重点 | Vox、Johnny Harris |
   | noir-minimal | 极简黑白 | 纯黑、宋体、大留白、慢 | LEMMiNO |
   | vivid-flat | 鲜明扁平 | 深蓝底、高饱和色块、圆润、弹 | Kurzgesagt |
   | swiss-data | 克制数据 | 浅灰白、网格、一个信号红、精确 | Polymatter、瑞士排版 |
2. **参考图**：用户发图，Agent 按 `references/style-dna.md` 提炼风格 DNA，学感觉不抄图 → 当期草稿 → 满意了存进「我的风格」。
3. **GitHub 开源导入**：用户发链接，Agent 先查许可证（必须写清是 MIT / Apache / BSD / CC0），只把它的配色、字体、动效数值翻译成风格包（不搬代码），来源和原作者署名写进 `license` / `source`，跑通后存进「我的风格」。没写许可证或不允许改的，直接告诉用户不能用。

### 风格包长什么样
`styles/<id>/style.json`：`palette`（bg / ink / accent / accent2 / muted / line / marker）、`background`（base、glow 柔光、texture、grain 颗粒、vignette 暗角）、`surface`（卡片：glass / paper / flat / outline，圆角、阴影）、`type`（head / body 用 sans 或 serif，一律思源黑体 / 思源宋体，字重、字距）、`line`、`accent_style`（marker 荧光笔 / underline / glow / fill）、`motion`（进场、速度、每 5 秒换几次画面）、`suits`（适合 5 类内容的程度 0~1）、`vibe`、`inspired_by`、`license`、`source`、`status`、`verified`。
`samples/` 里是验证时跑出来的小样。代码模板在 `styles/_layouts/`，共用零件在 `styles/_engine/`。旧的 3 个风格在 `styles/_retired/`，不参与推荐。

### 统一出图接口
```
python3 scripts/render.py --style <id 或风格文件夹> --text "原话" --dur 3 --aspect 9:16 [--size 1080x1920 --fps 30] \
  [--layout principle|numbers|tool|news|conclusion] [--mode anim|text] [--items "环节1|环节2"] [--emphasis "重点词"] \
  ( --out B3.mp4 | --keyframes --label "B3 · 00:41：原话" --out 逐帧图/B3 | --at 1.2 --out 图.png )
python3 scripts/render.py --style x --text "原话" --which-layout     # 只看这句会配到哪个版式
```

### 打分（默认只推第 1 名）
1. Agent 读完整份字幕，判断这期 5 类内容各占多少，比如 `{"比数字":0.4,"讲原理":0.3,"演示工具":0.2,"讲结论":0.1}`。
2. `python3 scripts/styles_tool.py rank --types '<比例>' --srt 字幕_修正.srt --out <用户的文件夹>/风格排名.json`
   分数 = 内容和风格的搭配度 70（按 `suits` 加权）+ 语速匹配 15 + 信息密度匹配 15（脚本从字幕自动算）；「我的风格」同分 +3。
3. 可以给排名里的每项加一句 `why`；不加页面会自动写。

### 页面上的三个按钮（小助手自动处理）
- 默认给第 1 名，配 **3 张样图**：用这期 3 句**不同版式**的原话，让用户一眼看到这个风格碰上不同内容的样子。
- **就这个**：写出 `风格选择.json`，并在本机记下「上次那个」。
- **换一个**：给接下来最接近的 2 个风格，各 3 张样图，配一句「跟上一个比：哪里不同」。
- **用上次那个**：直接用上次的风格（桌面版 Claude 和 Codex 能记住；网页版记不住）。

### 新风格上架
`python3 scripts/styles_tool.py verify <风格>`：5 种版式 × 竖横屏全部出图、画面会动，再各出一条 3 秒视频，12 项全过才改成「上架」，否则留在待验证区不给用户看。开源工具 / 风格的核验记录在 `styles/_pending/README.md`。

### 没有小助手时（Claude 网页版等）
自己跑 `rank`，用 `render.py --at` 给第 1 名出 3 张样图发在对话里，用能点的选项问「就这个 / 换一个」。

## 第 6 步：逐帧图审稿
- 先出图，全部确认前不渲染视频。
- 每个 B 编号出关键帧：`render.py --style <选定的> --text "原话" --dur <endTime-startTime> --keyframes --label "B3 · 00:41：原话" --mode <选定的>`（版式自动配，用户说「这张换成数字的」就加 `--layout numbers` 重出），得到开场、最满、定格 3 张。
- 模板版式不够表达这句时，Agent 可以照风格包的配色、字体、动效另写画面，但颜色、字重、线条、进场方式必须跟 style.json 一致。
- 一张一张单独发，绝不拼成大图；图下的标注不进最终视频。
- 用户点名改哪张只改哪张。确认过的存进 `已确认逐帧图/`。

## 第 7 步：对齐语速并出片
- 每段时长 = 这处标黄的 `startTime` 到 `endTime`；关键词在说到的那一刻出现（用 `--items` 拆环节，让每个环节落在对应的字上）。
- `render.py --out` 出每段视频：尺寸、帧率跟原视频一致（`--size`、`--fps`），libx264 -crf 16。先渲染 1 段给用户看。
- 让用户二选一：A. 只要动画片段 + 时间表，自己进剪映拼（原片零损失）；B. 直接嵌进原视频（libx264 -crf 16 或更低，音轨直接复制）。
- 画质只能保持或更高。交付前列出原片和成片的分辨率、帧率、码率。
- 文件夹最后有：`字幕_修正.srt`、`标黄逐字稿.docx`、`标黄结果.json`、`风格选择.json`、`风格样图/`、`已确认逐帧图/`、`成片/`。

## 在哪打开标黄页面
| 环境 | 做法 |
|---|---|
| Codex 桌面 app | in-app browser（侧边浏览器）打开地址 |
| Claude 桌面 app | 内置浏览器（侧边面板）打开地址 |
| Claude Code / Codex CLI | 把地址发给用户点开 |
| Claude 网页版（碰不到用户电脑） | 把 `assets/highlighter.html` 里的 `__DATA__` 换成页面数据，发布成右侧可交互页面并开启页面数据存储（db），确认后读 `transcript/current`；选风格按上面「没有小助手时」 |

- 页面数据格式：`{"title":名称,"blocks":[{"type":"p","text":原文,"hl":[[起,止]],"sug":[[起,止]],"cues":[[字起,字止,秒起,秒止]],"time":"00:12"}]}`。
- 缺 Chrome / ffmpeg 又装不上：直接说缺什么、怎么装，不要假装做完。环境变量 `CHROME` 可指定浏览器路径。

## 致谢
- 动效底层（弹簧、淡入淡出函数 `styles/_engine/motion.js`）来自 Barty-Bart/motion-graphics（Bart Slodyczka，MIT），原版权声明见 `styles/_engine/LICENSE-motion-graphics.txt`。
- 内置 5 个风格参考了 Apple 发布会、Cleo Abram、Vox、Johnny Harris、LEMMiNO、Kurzgesagt、Polymatter 的画面感觉，配色和参数为本仓库自研，不含任何原图、logo、角色。
- 字体：思源黑体 / 思源宋体（Source Han Sans / Serif，即 Noto Sans / Serif CJK，SIL OFL 1.1）。
