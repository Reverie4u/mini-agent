# Mini Agent pip 打包设计方案

**日期**: 2026-06-14
**状态**: 已确认
**前置 spec**: [Mini Agent Loop 设计](./2026-06-14-mini-agent-loop-design.md)

## 概述

将 mini-agent 从扁平的脚本项目重构为标准 Python 包，支持 `pip install` 安装和 `mini-agent` CLI 命令。

## 目标

- 用户可通过 `pip install .` 一键安装
- 安装后直接使用 `mini-agent` 命令启动 REPL
- 同时支持 `from mini_agent import Agent` 作为 Python 库导入
- 保留 `.env` 配置方式不变

## 变更内容

### 目录重构

旧结构 → 新结构：

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `agent.py` | `mini_agent/agent.py` | 移入包目录 |
| `tools.py` | `mini_agent/tools.py` | 移入包目录 |
| `main.py` | `mini_agent/cli.py` | 重命名，更语义化 |
| — | `mini_agent/__init__.py` | 新增，导出公开 API |
| — | `pyproject.toml` | 新增，打包配置 |
| — | `README.md` | 新增，使用文档 |
| `requirements.txt` | 删除 | 依赖由 pyproject.toml 管理 |

### pyproject.toml 配置

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mini-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["anthropic>=0.39.0", "python-dotenv>=1.0.0", "requests>=2.31.0"]

[project.scripts]
mini-agent = "mini_agent.cli:main"
```

关键点：
- `[project.scripts]` 声明 CLI 入口 `mini-agent → mini_agent.cli:main`
- 依赖直接在 `[project]` 中声明，无需 `requirements.txt`

### 导入路径修正

文件内部 import 需从相对导入改为包内绝对导入：

```python
# agent.py 内
from mini_agent.tools import TOOL_REGISTRY, execute_tool

# cli.py 内
from mini_agent.agent import Agent
```

### `__init__.py` 公开 API

```python
from .agent import Agent
from .tools import TOOL_REGISTRY, execute_tool
```

## 两种使用方式

**CLI 工具**：
```bash
pip install .
mini-agent
```

**Python 库**：
```python
from mini_agent import Agent

agent = Agent(api_key="sk-xxx", base_url="...", model="...")
response = agent.run("帮我计算 3*5")
```

## 兼容性

- `.env` 配置方式不变
- Agent 类的构造函数参数不变
- 工具注册表接口不变
