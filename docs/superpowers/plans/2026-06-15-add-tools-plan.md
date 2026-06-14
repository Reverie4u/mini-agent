# 新增 4 个工具：write_file、grep、list_files、web_fetch

**日期**: 2026-06-15
**对应 spec**: [新增工具设计](./specs/2026-06-15-add-tools.md)

## Context

当前 mini-agent 只有 3 个工具（calculator、search、read_file），缺少文件写入、代码搜索、目录浏览和网页抓取能力。参考 Claude Code 的工具集补齐这些能力。

## 步骤

### 1. 更新 tools.py — 新增 4 个工具函数

文件：`mini_agent/tools.py`

新增函数：
- `write_file(path, content)` — 安全写入文件，防护路径遍历 + 敏感路径拒绝
- `grep(pattern, path)` — 正则搜索文件内容，限制项目目录内，结果截断 20 条
- `list_files(path, depth)` — 列出目录树，忽略 .git/venv/__pycache__ 等
- `web_fetch(url)` — 抓取网页，提取文本，截断 50KB

新增 4 个对应的 Anthropic schema，追加到 `TOOL_SCHEMAS` 列表。

更新 `TOOL_REGISTRY` 注册 4 个新工具。

### 2. 验证

```bash
pipx install --force .
echo "搜索 agent.py 里的 import" | mini-agent
echo "抓取 https://example.com 的内容" | mini-agent
```

## 涉及文件

- `mini_agent/tools.py` — 唯一修改的文件
