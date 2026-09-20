# 《长夜醒来之前》本地 Harness 工程设计

## 目标

把现有的单文件阅读网页整理成可由 DeepSeek Harness 长期维护的本地小说工程，同时保持公开网页、既有正文与 GitHub Pages 发布方式不变。

## 边界

- `dist/` 继续是唯一公开发布目录。
- 总纲、人物秘密、伏笔台账、逐章创作源文件继续放在被 Git 忽略的 `work/` 中，防止公开仓库泄露剧透。
- 不在仓库中保存 DeepSeek API Key，不修改用户级 Harness 配置。
- 本次只调整工程结构，不改任何小说正文。

## 结构

```text
.
├── AGENTS.md                       # 所有本地 Agent 共用的工作规则
├── README.md                       # 本地启动、写作、校验、发布说明
├── dist/                           # GitHub Pages 公共产物
├── scripts/novel_project.py        # 提取、建章、构建、校验、状态工具
├── tests/test_novel_project.py     # 构建工具回归测试
└── work/                           # 私密且被 Git 忽略
    ├── HARNESS_HANDOFF.md          # DeepSeek 接管说明
    ├── project-state.json          # 当前章节与下一步
    ├── author-backstage.md         # 总纲、人物弧线、时间线、伏笔台账
    ├── geography-bible.md          # 地理设定
    └── manuscript/
        ├── manifest.json           # 章节顺序、标题、哈希、字数
        └── chapters/001.html ...   # 每章独立正文源文件
```

## 数据流

`extract` 从当前 `dist/index.html` 初始化本地章节源文件；以后 Harness 只编辑 `work/manuscript/chapters/` 与私密后台。`build` 根据清单重新生成网页正文、目录和总章数；`validate` 同时检查源文件与构建产物，避免重复章节、顺序错误、标题错位、标签失衡和误发布私密文件。

新增章节通过 `new` 创建标准骨架并追加清单。正文完成后先更新作者后台，再运行构建与校验。只有 `dist/`、公共说明和构建工具进入公开 Git 历史。

## 安全与失败处理

- 构建结果先写入同目录临时文件，通过全部校验后再原子替换目标网页。
- `extract` 默认拒绝覆盖已有本地稿源，必须显式传 `--force`。
- `build` 或 `validate` 遇到标题不匹配、重复编号、章节过短、标签失衡时立即失败，不改网页。
- 私密文件路径受 `.gitignore` 保护；校验会确认这些文件没有被 Git 跟踪。
- 发布仍由人工或 Harness 在通过测试后执行 `git commit` 与 `git push`。

## 验收

1. 从当前网页提取三十章。
2. 不修改章节内容，重新构建网页。
3. 确认三十章标题、顺序、正文哈希与构建前一致。
4. 运行单元测试和项目校验。
5. 确认 `git diff` 只包含工程文件，不包含小说正文变化。
