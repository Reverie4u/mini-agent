# Mini Agent Loop 设计方案

**日期**: 2026-06-14
**状态**: 已确认

## 概述

构建一个最小化的 Agent 循环，使用 Anthropic API (Claude)，在命令行 REPL 中实现带工具调用的智能对话。

## 配置

所有 LLM API 配置通过 `.env` 文件管理，用户可手动调整：

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `ANTHROPIC_API_KEY` | API 密钥/Token | `sk-ant-xxx` 或火山引擎 token |
| `ANTHROPIC_BASE_URL` | API 端点地址 | `https://api.anthropic.com` 或火山引擎地址 |
| `ANTHROPIC_MODEL` | 模型名称 | `claude-sonnet-4-6` 或 `deepseek-v4-pro[1M]` |

- `agent.py` 通过 `os.getenv()` 读取，允许代码中覆盖默认值
- 不硬编码任何厂商特定配置，兼容 Anthropic 官方和第三方兼容 API
- `Agent` 类构造函数接受可选的 `api_key`、`base_url`、`model` 参数

## 架构

```
mini-agent/
├── agent.py          # Agent 核心循环：对话管理、工具调度、步数/超时控制
├── tools.py          # 工具注册表 + 3 个工具实现
├── main.py           # REPL 入口
├── requirements.txt  # anthropic, python-dotenv, requests
└── .env              # ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
```

## 核心流程

```
用户输入 → Agent Loop:
  1. 发送 messages + tools 到 Anthropic API
  2. 模型返回 content 数组
     - 全是 text → 打印回复，结束本轮
     - 包含 tool_use → 解析工具名和参数
  3. 执行工具，收集结果
  4. 将 tool_result 追加到 messages，回到步骤 1
  5. 超过 max_steps 或 timeout → 终止并报错
```

## 组件设计

### 1. tools.py — 工具定义与执行

工具注册表：`name → (function, tool_schema)` 的映射。

| 工具 | 功能 | 实现方式 |
|------|------|----------|
| `calculator` | 计算数学表达式 | Python `eval`，受限命名空间只允许数学运算 |
| `search` | 搜索网络信息 | DuckDuckGo Instant Answer API（免费，无需 key） |
| `read_file` | 读取本地文件 | `open()` + 路径遍历防护（`os.path.realpath`） |

- 工具 schema 使用 Anthropic 格式：`{name, description, input_schema}`
- 每个工具函数接受一个 dict 参数，返回字符串结果
- 工具执行异常捕获后转为错误字符串返回

### 2. agent.py — Agent 循环

`Agent` 类：

```python
class Agent:
    def __init__(self, max_steps=10, timeout=60,
                 api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.messages = []      # 对话历史
        self.max_steps = 10     # 最大工具调用步数
        self.timeout = 60       # 超时秒数

    def run(self, user_message: str) -> str:
        """执行一轮 agent 对话，返回最终回复"""
```

核心循环逻辑：
- 将用户消息追加到 `messages`
- while 循环：
  - 调用 `anthropic.messages.create(model, messages, tools)`
  - 遍历 `response.content`：
    - `text` → 累积到回复中
    - `tool_use` → 收集到待执行列表
  - 如果没有 `tool_use` → 返回累积的文本回复
  - 如果有 `tool_use`：
    - 并发执行所有工具（`concurrent.futures`）
    - 将 `tool_result` block 追加到 messages
    - `step_count += 1`
    - 检查是否超过 `max_steps`
- 超时控制：用 `signal.alarm` 设置超时，超时后抛出异常

错误处理：
- API 调用失败 → 重试 1 次，仍失败则返回错误信息
- 工具执行异常 → 异常信息作为 `tool_result` 返回给模型
- 超时 → `TimeoutError`，提示用户
- 超过最大步数 → 返回 "已达到最大步数限制"

### 3. main.py — REPL 入口

- `input("> ")` 循环读取用户输入
- 维护一个 `Agent` 实例和对话历史
- 支持命令：
  - `/exit` — 退出
  - `/clear` — 清空对话历史
  - `/steps N` — 设置最大步数
- 每轮打印工具调用过程（工具名、参数、结果）

## 设计决策

| 决策 | 理由 |
|------|------|
| 工具并行执行 | 多个 tool_use 互不依赖时可并发，减少延迟 |
| 异常作为 tool_result | 让模型感知工具执行失败，可自行修正 |
| `signal.alarm` 超时 | 简单直接，Unix 系统原生支持 |
| 受限 eval | 只暴露 math 模块函数，防止代码注入 |
| DuckDuckGo 搜索 | 免费无需 API key，适合演示 |

## 待定

- 无。设计已确认，进入实现阶段。
