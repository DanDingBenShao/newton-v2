"""
Newton-X v2.0 — Abstraction Layer
Pure regex extraction of intent from tool calls. Zero LLM cost.
"""

import re
from typing import Optional


class AbstractionLayer:
    """Extracts high-level intent labels from raw tool call data."""

    # ── Write/Edit intent patterns ────────────────────────────

    CLASS_PATTERN = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
    FUNC_PATTERN = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
    IMPORT_PATTERN = re.compile(r"^(?:from|import)\s+(\w+)", re.MULTILINE)
    DECORATOR_PATTERN = re.compile(r"^\s*@(\w+)", re.MULTILINE)

    # Complexity signals
    THREADING = re.compile(r"(?:threading|multiprocessing|asyncio|concurrent)", re.IGNORECASE)
    DB_ACCESS = re.compile(r"(?:session\.|\.execute\(|\.query\(|\.commit\()", re.IGNORECASE)
    NETWORK = re.compile(r"(?:requests\.|urllib|httpx|aiohttp|socket)", re.IGNORECASE)
    SECURITY = re.compile(r"(?:hash|encrypt|decrypt|token|auth|password|secret)", re.IGNORECASE)

    # ── Read intent by file type ──────────────────────────────

    READ_PATTERNS = [
        (re.compile(r"test[s]?[/\\]|test_|_test\.py|conftest\.py|spec\.", re.IGNORECASE), "阅读测试代码"),
        (re.compile(r"\.ya?ml$|\.toml$|\.ini$|\.cfg$|\.env|\.json$|settings\.py|config\.py|Dockerfile"), "阅读配置文件"),
        (re.compile(r"\.md$|README|CHANGELOG|CONTRIBUTING|\.rst$|\.txt$|docs?[/\\]"), "阅读文档"),
        (re.compile(r"\.py$|\.js$|\.ts$|\.go$|\.rs$|\.java$"), "阅读源代码"),
    ]

    # ── Thinking extraction ────────────────────────────────────

    # Matches # think: ... or // think: ... or /* think: ... */
    THINK_PATTERN = re.compile(
        r"(?:#|//|/\*)\s*@?think\s*[:：]\s*(.+?)(?:\*/)?$",
        re.MULTILINE | re.IGNORECASE,
    )

    @staticmethod
    def extract_thinking(content: str) -> str | None:
        """Extract the thinking annotation from code. Returns None if absent."""
        if not content:
            return None
        match = AbstractionLayer.THINK_PATTERN.search(content)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_intent(tool_name: str, arguments: dict) -> tuple[str, str]:
        """
        Returns (intent_label, context_description).
        intent_label: short tag like "编写类" or "搜索关键词"
        context_description: richer one-line summary
        """
        tool = tool_name.lower()
        content = arguments.get("content", arguments.get("new_str", ""))
        file_path = arguments.get("path", arguments.get("file_path", ""))
        query = arguments.get("pattern", arguments.get("query", ""))

        if tool in ("write", "edit", "write_file", "edit_file"):
            return AbstractionLayer._extract_write_intent(content, file_path, tool)
        elif tool in ("read",):
            return AbstractionLayer._extract_read_intent(file_path)
        elif tool in ("grep",):
            return AbstractionLayer._extract_search_intent(query, "代码搜索")
        elif tool in ("websearch",):
            return AbstractionLayer._extract_search_intent(query, "网页搜索")
        elif tool in ("webfetch",):
            return AbstractionLayer._extract_search_intent(query or file_path, "网页抓取")
        elif tool in ("bash",):
            return AbstractionLayer._extract_bash_intent(arguments)
        elif tool in ("glob",):
            return AbstractionLayer._extract_search_intent(query, "文件查找")
        else:
            return (f"调用{tool}", f"执行 {tool} 工具")

    @staticmethod
    def _extract_write_intent(content: str, file_path: str, tool: str) -> tuple[str, str]:
        if not content:
            return ("编辑文件", f"{'写入' if tool == 'write' else '编辑'} {file_path}")

        classes = AbstractionLayer.CLASS_PATTERN.findall(content)
        funcs = AbstractionLayer.FUNC_PATTERN.findall(content)
        imports = AbstractionLayer.IMPORT_PATTERN.findall(content)

        parts = []
        if classes:
            parts.append(f"类:{','.join(classes[:3])}")
        if funcs:
            parts.append(f"函数:{','.join(funcs[:5])}")
        if imports:
            parts.append(f"依赖:{','.join(imports[:5])}")

        detail = "; ".join(parts) if parts else "代码编辑"

        # Detect domain
        domains = []
        if AbstractionLayer.THREADING.search(content):
            domains.append("并发")
        if AbstractionLayer.DB_ACCESS.search(content):
            domains.append("数据库")
        if AbstractionLayer.NETWORK.search(content):
            domains.append("网络")
        if AbstractionLayer.SECURITY.search(content):
            domains.append("安全")

        domain_str = f" [{', '.join(domains)}]" if domains else ""
        intent = f"{'编写' if tool == 'write' else '编辑'}{domain_str}"
        context = f"{intent} | {detail} | {file_path}"

        return (intent, context)

    @staticmethod
    def _extract_read_intent(file_path: str) -> tuple[str, str]:
        for pattern, label in AbstractionLayer.READ_PATTERNS:
            if pattern.search(file_path):
                return (label, f"{label}: {file_path}")
        return ("阅读文件", f"阅读: {file_path}")

    @staticmethod
    def _extract_search_intent(query: str, tool_type: str) -> tuple[str, str]:
        if query:
            q = str(query)[:80]
            return (f"{tool_type}: {q}", f"{tool_type}: {q}")
        return (tool_type, tool_type)

    @staticmethod
    def _extract_bash_intent(arguments: dict) -> tuple[str, str]:
        cmd = str(arguments.get("command", ""))[:80]
        if "pip" in cmd:
            return ("安装依赖", f"执行: {cmd}")
        if "test" in cmd.lower() or "pytest" in cmd:
            return ("运行测试", f"执行: {cmd}")
        if "git" in cmd:
            return ("Git操作", f"执行: {cmd}")
        if "curl" in cmd or "wget" in cmd:
            return ("网络请求", f"执行: {cmd}")
        return ("执行命令", f"执行: {cmd}")

    @staticmethod
    def extract_content_summary(content: str, max_length: int = 120) -> str:
        """Lightweight content summary — first meaningful line(s)."""
        if not content:
            return "(空)"

        # Try to find the first non-empty, non-comment, non-decorator line
        lines = content.strip().split("\n")
        meaningful = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("@"):
                continue
            meaningful.append(stripped)

        if not meaningful:
            return content[:max_length]

        summary = "; ".join(meaningful[:3])
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."
        return summary
