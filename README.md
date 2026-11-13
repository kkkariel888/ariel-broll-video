# ariel-skills

Ariel 开源的 AI skill 合集。

## 怎么装：把这个链接发给你的 AI
复制这句话，发给你的 Claude / Codex：

```
帮我装上这个：https://github.com/kkkariel888/ariel-skills
```

AI 会照 [INSTALL.md](INSTALL.md) 一口气装好：git、ffmpeg、风格库、插件本身，并打开自动更新。
中间只有极少数地方要你自己点一下（比如 Mac 弹窗点「安装」、在 Claude app 里勾「自动同步」），AI 会告诉你。

**以后作者一更新，你那边自动变成最新版，不用再做任何事。**

> 想自己装：能用终端的话跑
> `git clone --depth 1 https://github.com/kkkariel888/ariel-skills.git /tmp/ariel-skills && bash /tmp/ariel-skills/install.sh`
> Claude app 里：Customize → Plugins → Add marketplace → 粘贴 `kkkariel888/ariel-skills` → 勾 Sync automatically。

## 插件列表
| 插件 | 做什么 |
|---|---|
| broll-video-maker | 给口播视频配代码动画 B-roll：审错别字、仿 Word 标黄、从 Lemo 风格库 / 参考图 / GitHub 链接挑风格、每个画面按风格现画、逐帧审稿、对齐语速、出片（风格库首次使用时自动下载：Lemo-Opuscar by Lemomo） |

## 许可证
MIT。风格库 Lemo-Opuscar 不打包在这里，使用时从它的官方仓库下载，遵守它自己的许可证。
