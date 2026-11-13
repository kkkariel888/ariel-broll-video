# 开源项目核验记录

收录规矩：许可证写清楚（MIT / Apache / BSD / CC0 可以照做；带 NC 的只能非商用或按额外许可；GPL / SA 改动要同样公开；没写的不能用）。
核验工具：`python3 scripts/dna.py license <GitHub 链接>`。

## 风格库
| 仓库 | 许可证 | 结论 |
|---|---|---|
| lemomo-ai/lemo-opuscar（2026-11-13 核验，99 个风格） | 代码 MIT；风格说明 CC BY-NC 4.0 + 额外许可（读、照做、改来做自己的片子，商用片也行）；演示片 CC BY 4.0；Clawd 角色、部分配音、第三方商标除外 | **采用为默认风格库**，但只在用户电脑上现下载现读（`lemo.py`），本 skill 不带它的任何内容。放进别的产品或服务分发需要商用授权（lemomo.studio@gmail.com） |

## 做视频工具（2026-11-13 核验，均未收进 skill）
| 仓库 | 许可证 | 结论 |
|---|---|---|
| Barty-Bart/motion-graphics（原作者 Bart Slodyczka） | MIT | 质量好，但我们画面改用 Lemo 的页面约定和工具，不再需要 |
| mrgoraya/morph-edit | MIT | 基于 Bart 的引擎，未收 |
| mrrajrumel/motion-skill | 写的 MIT | **不收**：代码和 Bart 的几乎一样，却换成了自己的版权名、没写来源 |
| petergyang/video-short | MIT | 依赖 HyperFrames，用户已判定不适合做 B-roll |
| showlab/Code2Video | MIT | Manim 长讲解，重、慢，不适合几秒的 B-roll |
| YIAN6557/eian-collage-broll | MIT | 只出素材包，没有画面代码 |

## 坑
- Manim：MIT，可放心用。
- Remotion：不是 MIT，超过 3 人的盈利公司要买公司版。
- 字体用开源的（SIL OFL）：思源黑体 / 宋体、霞鹜漫黑等，许可证文件随字体放。
