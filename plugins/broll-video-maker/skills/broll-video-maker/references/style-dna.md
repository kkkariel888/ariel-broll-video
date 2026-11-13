# 参考图 → 风格 DNA

用户发参考图（截图、Pinterest 动态图、别人视频的一帧），Agent 自己看图提炼，**不让用户描述**。
原则：**学感觉，不抄图**。产出是一份风格 DNA，不是复刻那张图。

## 只提取这 8 样
| # | 提取什么 | 写进 dna.json 的哪里 | 取值 |
|---|---|---|---|
| 1 | 主色 3~5 个色值 | `palette`：bg 背景、ink 正文、accent 强调，可加 accent2、muted | `#RRGGBB` |
| 2 | 背景质感 | `background.texture` | plain / paper / grain / grid / dots / scanlines / vignette |
| 3 | 版式和留白 | `layout_rules.margin`、`align`、`whitespace` | margin 0.05~0.15；align left / center |
| 4 | 字体粗细大小 | `type.head_weight`、`body_weight`、`scale` | 100~900；scale 0.8~1.3（字体一律用思源黑体，不搬原图字体） |
| 5 | 线条粗细 | `line.width` | 1~8 |
| 6 | 进场方式 | `motion.entrance` | draw 描线 / rise 浮上来 / pop 弹出 / blur 模糊变清 / type 打字 |
| 7 | 动效速度和节奏 | `motion.speed`、`motion.feel` | 0.7 慢 ~ 1.4 快；feel 用一句话写 |
| 8 | 每 5 秒换几次画面 | `motion.cuts_per_5s` | 1~4 |

静态图看不出 6~8 时，按画面气质估一个，并在 `motion.feel` 里写「从静态图估的」。

另外按这期内容填 `category`（讲原理 / 比数字 / 讲新闻 / 演示工具 / 讲结论），决定用哪套版式。

## 不抄
logo、真人脸、品牌名、角色、原图里的具体画面。
DNA 里不能出现图片路径、网址、品牌名、logo，`styles_tool.py dna-new` 会检查，带了就拒收。

## dna.json 例子
```json
{
  "name": "暖橘杂志风",
  "category": "讲结论",
  "palette": {"bg": "#FFF4E8", "ink": "#2B1B12", "accent": "#FF7A1A", "muted": "#B8A493"},
  "background": {"texture": "grain"},
  "layout_rules": {"margin": 0.1, "align": "left", "whitespace": "大，一屏一个重点"},
  "type": {"head_weight": 900, "body_weight": 400, "scale": 1.15},
  "line": {"width": 2},
  "motion": {"entrance": "pop", "speed": 1.15, "cuts_per_5s": 2, "feel": "大字弹进来，停一下再走"}
}
```

## 流程
1. 看图 → 写 `dna.json`（当期文件夹里）。
2. `python3 scripts/styles_tool.py dna-new dna.json --folder <当期文件夹>` → 生成 `风格草稿/draft-xxxx/`。
3. 用这期一句真话出样图：`python3 scripts/render.py --style <草稿文件夹> --text "…" --keyframes --label "B? · 时间：原话" --out …`。
4. 用户满意 → `styles_tool.py save-mine <草稿文件夹>`，存进「我的风格」（本机 `~/.broll-video-maker/my-styles/`，以后每期都参与打分）。
   不满意 → 只留在当期文件夹当草稿，不进菜单。
