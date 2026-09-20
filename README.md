# 长夜醒来之前：本地创作工程

这个目录同时承担两件事：维护《长夜醒来之前》的私密创作资料，以及生成 GitHub Pages 上的公开阅读网页。现有前三十章不需要迁移到别处，DeepSeek Harness 直接打开本目录即可接手。

## 给 Harness 的第一次指令

```text
请完整阅读 AGENTS.md 与 work/HARNESS_HANDOFF.md，并严格按其中的读取顺序核对作者后台、地理设定、章节清单和末三章。不要向我展示任何后台剧透。先报告你确认到的当前公开章数、下一章编号和本次写作的非剧透目标；未经确认不要改旧章。随后按单章工作流续写。
```

模型名称和 API Key 请在 Harness 自己的配置中设置，不要写入本仓库。

## 目录结构

```text
AGENTS.md                    所有写作代理都必须遵守的公开规则
dist/                        GitHub Pages 公开阅读网页
scripts/novel_project.py     章节提取、构建和校验工具
tests/                       防止旧章被误改的自动校验
work/                        本机私密创作层，不进入 Git
  HARNESS_HANDOFF.md         当前接班点与最近任务
  project-state.json         当前章数和发布状态
  author-backstage.md        私密总纲、人物弧线、时间线、伏笔台账
  geography-bible.md         地理设定
  manuscript/chapters/       每章独立稿源
  manuscript/manifest.json   章节标题、状态、字数与内容指纹
```

## 常用命令

```bash
python3 scripts/novel_project.py status
python3 scripts/novel_project.py validate
python3 -m unittest discover -s tests -v
```

续写、构建和发布的完整顺序写在 `AGENTS.md`。构建器会根据每章独立稿源更新目录和网页，同时用内容指纹检查稿源是否被悄悄改动。

## 隐私边界

`work/` 已被 `.gitignore` 排除，其中包含会剧透的总纲和连续性资料。公开仓库只保留网页、无剧透规则和工具。如果以后把工程复制到另一台电脑，需要通过私密方式单独复制 `work/`，不能依赖公开 GitHub 仓库恢复它。
