# Mini Agent

最小化 LLM Agent 循环 — 支持工具调用的命令行 AI 助手。

## 安装

```bash
git clone https://github.com/Reverie4u/mini-agent.git
cd mini-agent
pipx install .
```

## 配置

设置环境变量（或在项目目录下创建 `.env` 文件）：

```bash
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # 可选，默认 Anthropic 官方
export ANTHROPIC_MODEL="claude-sonnet-4-6"              # 可选
```

## 使用

```bash
mini-agent
```

REPL 命令：
- `/exit` — 退出
- `/clear` — 清空对话历史
- `/steps N` — 设置最大工具调用步数

## 示例

```
> 帮我计算 15 * 7 + 23
  [步骤 1] 执行工具: calculator
  └─ calculator({'expression': '15 * 7 + 23'}) → 128

15 × 7 + 23 = 128
```
