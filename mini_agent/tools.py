import math
import os
import re
import fnmatch
from html.parser import HTMLParser
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
    {
        "name": "write_file",
        "description": "写入/创建文件。会自动创建父目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对路径）",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "grep",
        "description": "在项目文件中搜索匹配正则表达式的内容，返回匹配的行及文件名",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "正则表达式或关键字",
                },
                "path": {
                    "type": "string",
                    "description": "搜索路径（文件或目录），默认为当前目录",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_files",
        "description": "列出目录结构，以树状格式展示",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要列出的目录路径，默认为当前目录",
                },
                "depth": {
                    "type": "integer",
                    "description": "最大深度，默认 2",
                },
            },
            "required": [],
        },
    },
    {
        "name": "web_fetch",
        "description": "抓取网页内容并提取纯文本",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页 URL",
                },
            },
            "required": ["url"],
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


# 敏感路径：write_file 拒绝写入
_SENSITIVE_PATTERNS = [".env", ".git", "venv", ".venv", "__pycache__", ".egg-info"]

# grep 忽略的目录
_IGNORED_DIRS = {".git", "venv", ".venv", "__pycache__", ".egg-info", "node_modules", ".mypy_cache"}


def _is_safe_path(path: str) -> tuple[bool, str]:
    """检查路径是否在项目目录内且不指向敏感文件"""
    cwd = os.path.realpath(os.getcwd())
    try:
        real_path = os.path.realpath(path)
    except Exception:
        return False, f"无效路径: {path}"

    if not real_path.startswith(cwd + os.sep) and real_path != cwd:
        return False, f"安全限制: 只能操作项目目录内的文件 ({cwd})"

    rel = os.path.relpath(real_path, cwd)
    for pattern in _SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(os.path.basename(rel), pattern):
            return False, f"安全限制: 不能操作敏感文件/目录 ({rel})"

    return True, real_path


def write_file(path: str, content: str) -> str:
    """安全写入文件"""
    safe, result = _is_safe_path(path)
    if not safe:
        return result

    try:
        os.makedirs(os.path.dirname(result) or ".", exist_ok=True)
        with open(result, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入 {os.path.relpath(result)} ({len(content)} 字节)"
    except Exception as e:
        return f"写入文件失败: {e}"


def grep(pattern: str, path: str = ".") -> str:
    """在项目文件中搜索正则匹配内容"""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"无效的正则表达式: {e}"

    cwd = os.path.realpath(os.getcwd())
    target = os.path.realpath(os.path.join(cwd, path))

    if not target.startswith(cwd + os.sep) and target != cwd:
        return f"安全限制: 只能搜索项目目录内的文件 ({cwd})"

    results = []
    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, filenames in os.walk(target):
            dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS]
            for f in filenames:
                files.append(os.path.join(root, f))

    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if regex.search(line):
                        rel = os.path.relpath(filepath, cwd)
                        results.append(f"{rel}:{lineno}: {line.rstrip()}")
                        if len(results) >= 20:
                            break
                if len(results) >= 20:
                    break
        except Exception:
            continue

    if not results:
        return f"未找到匹配 '{pattern}' 的内容"
    return "\n".join(results)


def list_files(path: str = ".", depth: int = 2) -> str:
    """列出目录结构"""
    cwd = os.path.realpath(os.getcwd())
    target = os.path.realpath(os.path.join(cwd, path))

    if not target.startswith(cwd + os.sep) and target != cwd:
        return f"安全限制: 只能列出项目目录内的文件 ({cwd})"

    if not os.path.isdir(target):
        return f"不是目录: {path}"

    depth = min(max(depth, 1), 3)
    lines = [os.path.relpath(target, cwd) + "/"]

    for root, dirs, filenames in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORED_DIRS)
        filenames = sorted(f for f in filenames if not f.startswith("."))

        level = len(os.path.relpath(root, target).split(os.sep))
        if root == target:
            level = 0
        if level >= depth:
            dirs[:] = []
            continue

        indent = "  " * (level + 1)
        for d in dirs:
            lines.append(f"{indent}{d}/")
        for f in filenames:
            lines.append(f"{indent}{f}")

    return "\n".join(lines)


class _TextExtractor(HTMLParser):
    """从 HTML 中提取纯文本"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {"script", "style", "noscript", "iframe"}

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text.append(stripped)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text.append("\n")


def web_fetch(url: str) -> str:
    """抓取网页并提取纯文本"""
    import requests

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "MiniAgent/1.0"},
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"不支持的内容类型: {content_type}"

        if "text/plain" in content_type:
            text = resp.text
        else:
            parser = _TextExtractor()
            parser.feed(resp.text)
            text = "\n".join(parser.text)

        if len(text) > 50 * 1024:
            text = text[:50 * 1024] + "\n\n[内容已截断]"
        return text.strip() or "[网页内容为空]"

    except Exception as e:
        return f"抓取失败: {e}"


# 工具注册表：name → (function, schema)
TOOL_REGISTRY: dict[str, tuple[callable, dict]] = {
    "calculator": (calculator, TOOL_SCHEMAS[0]),
    "search": (search, TOOL_SCHEMAS[1]),
    "read_file": (read_file, TOOL_SCHEMAS[2]),
    "write_file": (write_file, TOOL_SCHEMAS[3]),
    "grep": (grep, TOOL_SCHEMAS[4]),
    "list_files": (list_files, TOOL_SCHEMAS[5]),
    "web_fetch": (web_fetch, TOOL_SCHEMAS[6]),
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
