import math
import os
import requests
from typing import Any

# ---------------------------------------------------------------------------
# 工具 schema（Anthropic 格式）
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "calculator",
        "description": "计算数学表达式，支持 +-*/、幂运算、三角函数、对数等。例如: '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)'",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "search",
        "description": "搜索网络信息，返回相关结果摘要",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "读取本地文件内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径（相对或绝对路径）",
                }
            },
            "required": ["path"],
        },
    },
]

# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------

# calculator 的安全命名空间：只暴露 math 模块函数和基本内置函数
_SAFE_NAMESPACE = {
    k: getattr(math, k)
    for k in dir(math)
    if not k.startswith("_")
}
_SAFE_NAMESPACE.update({
    "abs": abs,
    "round": round,
    "int": int,
    "float": float,
    "pow": pow,
    "max": max,
    "min": min,
    "sum": sum,
})


def calculator(expression: str) -> str:
    """安全计算数学表达式"""
    try:
        result = eval(expression, {"__builtins__": {}}, _SAFE_NAMESPACE)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def search(query: str) -> str:
    """通过 DuckDuckGo Instant Answer API 搜索"""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"])
        if data.get("Answer"):
            parts.append(f"Answer: {data['Answer']}")

        related = data.get("RelatedTopics", [])
        for topic in related[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(f"- {topic['Text']}")

        if not parts:
            return f"未找到关于 '{query}' 的搜索结果"

        return "\n".join(parts)
    except Exception as e:
        return f"搜索失败: {e}"


def read_file(path: str) -> str:
    """安全读取文件，防止路径遍历攻击"""
    try:
        real_path = os.path.realpath(path)
        cwd = os.path.realpath(os.getcwd())

        if not real_path.startswith(cwd + os.sep) and real_path != cwd:
            return f"安全限制: 只能读取项目目录内的文件 ({cwd})"

        if not os.path.exists(real_path):
            return f"文件不存在: {path}"

        if os.path.getsize(real_path) > 1024 * 1024:  # 1MB 限制
            return f"文件过大 (>1MB): {path}"

        with open(real_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        return f"无法读取二进制文件: {path}"
    except Exception as e:
        return f"读取文件失败: {e}"


# 工具注册表：name → (function, schema)
TOOL_REGISTRY: dict[str, tuple[callable, dict]] = {
    "calculator": (calculator, TOOL_SCHEMAS[0]),
    "search": (search, TOOL_SCHEMAS[1]),
    "read_file": (read_file, TOOL_SCHEMAS[2]),
}


def execute_tool(name: str, params: dict[str, Any]) -> str:
    """执行指定工具并返回结果字符串"""
    if name not in TOOL_REGISTRY:
        return f"未知工具: {name}"
    func, _ = TOOL_REGISTRY[name]
    try:
        return func(**params)
    except TypeError as e:
        return f"参数错误: {e}"
