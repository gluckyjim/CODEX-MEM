# codex-mem

`codex-mem` 是一套面向 Codex 的本地优先记忆工作流。

它解决的不是“模型会不会变聪明”，而是更实际的问题：

- 长项目里的规则会被忘
- 用户偏好会被忘
- 上一轮关键决策会被忘
- 默认上下文装不下长期合作信息

`codex-mem` 的思路是：

- 开工前跑一次 `preflight`
- 做完后跑一次 `capture`
- 用户说“记住这条”时显式写入
- 用 SQLite 做长期存储
- 用 Markdown 做快速摘要

## 核心能力

- `remember`
- `search`
- `preflight`
- `capture`
- `project-state`
- `import-legacy`

## 快速开始

```bash
python -m codex_mem init
python -m codex_mem preflight --project "my-project" --query "topic"
```

保存长期规则：

```bash
python -m codex_mem remember --project "my-project" --text "记住这条：开工前先读记忆。"
```

保存一轮工作摘要：

```bash
python -m codex_mem capture --project "my-project" --summary "完成项目状态渲染和 preflight 检索优化。"
```

更多说明见：

- [README.md](README.md)
- [docs/integration-guide.md](docs/integration-guide.md)
- [docs/publishing.md](docs/publishing.md)
