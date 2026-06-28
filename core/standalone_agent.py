#!/usr/bin/env python3
"""
Newton-X Standalone Agent — DeepSeek-powered, full tool access.
Reads tasks from queue, executes autonomously, writes all tool calls to stream.
System 2 Daemon monitors the stream.
"""

import json, os, sys, time, urllib.request, subprocess, re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────

def _cfg(key: str, env_key: str, default: str) -> str:
    try:
        from config import get
        return get(key, default)
    except ImportError:
        return os.getenv(env_key, default)

def _path(key: str, env_key: str, fallback: str) -> Path:
    try:
        from config import get
        return Path(get(key))
    except ImportError:
        return Path(os.getenv(env_key, str(Path.home() / ".newton-x" / fallback)))

API_URL = _cfg("api_url", "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
API_KEY = _cfg("api_key", "DEEPSEEK_API_KEY", "")
MODEL = _cfg("model", "DEEPSEEK_MODEL", "deepseek-v4-flash")

TASK_FILE = _path("task_file", "NEWTON_TASK_FILE", "newton_task.jsonl")
RAW_STREAM = _path("raw_stream", "NEWTON_RAW_STREAM", "newton_raw.jsonl")
WORK_DIR = Path(os.getenv("AGENT_WORK_DIR", str(Path.home())))

# ── Tool definitions (for DeepSeek function calling) ──────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute or relative to working dir)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit an existing file by replacing old_str with new_str",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old_str": {"type": "string", "description": "Text to replace"},
                    "new_str": {"type": "string", "description": "Replacement text"}
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a bash/shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search codebase for a pattern using grep",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex)"},
                    "path": {"type": "string", "description": "Directory to search (optional)"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish_task",
            "description": "Signal task completion with a summary",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "What was accomplished"}
                },
                "required": ["summary"]
            }
        }
    }
]

# ── Tool implementations ──────────────────────────────────────

def write_raw_event(tool_name: str, tool_input: dict, file_path: str = ""):
    """Log a tool call to the raw stream for System 2 monitoring."""
    event = {
        "tool_name": tool_name,
        "file_path": file_path,
        "tool_input": tool_input,
        "timestamp": time.strftime("%H:%M:%S"),
    }
    try:
        RAW_STREAM.parent.mkdir(parents=True, exist_ok=True)
        with open(RAW_STREAM, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def execute_tool(call: dict) -> str:
    """Execute a single tool call. Returns result string."""
    name = call["function"]["name"]
    args = json.loads(call["function"]["arguments"]) if isinstance(call["function"]["arguments"], str) else call["function"]["arguments"]

    try:
        if name == "read_file":
            path = Path(args["path"])
            if not path.is_absolute():
                path = WORK_DIR / path
            content = path.read_text(encoding="utf-8") if path.exists() else f"(file not found: {path})"
            write_raw_event("Read", {"path": str(path)}, str(path))
            return content[:8000]

        elif name == "write_file":
            path = Path(args["path"])
            if not path.is_absolute():
                path = WORK_DIR / path
            path.parent.mkdir(parents=True, exist_ok=True)
            content = args["content"]
            # Inject # think: if not present
            if not content.startswith("# think:"):
                content = f"# think: {args.get('think', 'implementing')}\n{content}"
            path.write_text(content, encoding="utf-8")
            write_raw_event("Write", {"path": str(path), "content": content}, str(path))
            return f"File written: {path}"

        elif name == "edit_file":
            path = Path(args["path"])
            if not path.is_absolute():
                path = WORK_DIR / path
            old = args["old_str"]
            new = args["new_str"]
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            if old not in existing:
                return f"ERROR: old_str not found in {path}"
            updated = existing.replace(old, new, 1)
            # Inject think annotation
            if not new.startswith("# think:"):
                new = f"# think: {args.get('think', 'editing')}\n{new}"
                updated = existing.replace(old, new, 1)
            path.write_text(updated, encoding="utf-8")
            write_raw_event("Edit", {"path": str(path), "content": new}, str(path))
            return f"File edited: {path}"

        elif name == "run_bash":
            cmd = args["command"]
            write_raw_event("Bash", {"command": cmd}, "")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=str(WORK_DIR))
            output = result.stdout[:3000] + (result.stderr[:1000] if result.stderr else "")
            return output or "(no output)"

        elif name == "search_code":
            pattern = args["pattern"]
            search_path = args.get("path", str(WORK_DIR))
            write_raw_event("Grep", {"pattern": pattern, "path": search_path}, search_path)
            result = subprocess.run(
                ["grep", "-r", "-n", "--include=*.py", pattern, search_path],
                capture_output=True, text=True, timeout=10, cwd=str(WORK_DIR)
            )
            return result.stdout[:4000] or "(no matches)"

        elif name == "web_search":
            query = args["query"]
            write_raw_event("WebSearch", {"query": query}, "")
            # Use curl for reliability
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "10",
                 f"https://api.deepseek.com/v1/chat/completions",
                 "-H", "Content-Type: application/json",
                 "-H", f"Authorization: Bearer {API_KEY}",
                 "-d", json.dumps({
                     "model": MODEL, "max_tokens": 200,
                     "messages": [{"role": "user", "content": f"Search result for: {query}. Provide a concise factual answer in Chinese."}]
                 })],
                capture_output=True, timeout=20,
            )
            try:
                body = json.loads(result.stdout.decode("utf-8"))
                return body["choices"][0]["message"]["content"][:1000]
            except Exception:
                return f"(simulated) For '{query}', common results suggest checking standard library docs and PyPI for existing packages."

        elif name == "finish_task":
            return args.get("summary", "Task complete")

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        return f"Tool error: {e}"


# ── Agent loop ────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an autonomous coding agent. You receive a task and execute it step by step.

Rules:
- Use tools to read files, write code, search, and run commands.
- Before writing code, search the web or codebase to understand what already exists.
- When writing new files or editing, ALWAYS include a first line like '# think: <why you are doing this>' explaining your reasoning.
- After completing the task, call finish_task with a summary.
- Work in the directory: {work_dir}
- Be thorough but efficient. Don't write unnecessary code.
- Output in Chinese when communicating with the user."""


def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Call DeepSeek API via curl. Returns the assistant message."""
    payload_dict = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    if tools:
        payload_dict["tools"] = tools

    payload = json.dumps(payload_dict)

    result = subprocess.run(
        ["curl", "-s", "--connect-timeout", "30", "--max-time", "60",
         "-X", "POST", API_URL,
         "-H", "Content-Type: application/json",
         "-H", f"Authorization: Bearer {API_KEY}",
         "-d", payload],
        capture_output=True, timeout=65,
    )
    body = json.loads(result.stdout.decode("utf-8"))
    return body["choices"][0]["message"]


def run_task(task_description: str) -> str:
    """Execute one task. Returns completion summary."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(work_dir=str(WORK_DIR))},
        {"role": "user", "content": task_description},
    ]

    for iteration in range(20):
        try:
            msg = call_llm(messages, TOOLS)
        except Exception as e:
            return f"API error: {e}"

        tool_calls = msg.get("tool_calls", [])

        if tool_calls:
            messages.append(msg)
            for tc in tool_calls:
                result = execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            continue

        content = msg.get("content", "")
        if content:
            # Agent is communicating — may be done. Push to finish.
            messages.append(msg)
            messages.append({"role": "user", "content": "If task is complete, call finish_task. Otherwise continue."})
            continue

        return "No response"

    return "Max iterations"


# ── Main: poll for tasks ─────────────────────────────────────

def main():
    if not API_KEY:
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(f"[Agent] Started. Work dir: {WORK_DIR}")
    print(f"[Agent] Waiting for tasks in: {TASK_FILE}")

    # Ensure files exist
    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASK_FILE.touch()
    RAW_STREAM.parent.mkdir(parents=True, exist_ok=True)
    RAW_STREAM.touch()

    last_task_pos = 0

    try:
        while True:
            if TASK_FILE.exists():
                with open(TASK_FILE, "r", encoding="utf-8") as f:
                    f.seek(last_task_pos)
                    new_lines = f.read()

                if new_lines.strip():
                    for line in new_lines.strip().split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            task = json.loads(line)
                            desc = task.get("task", task.get("description", str(task)))
                            print(f"\n[Agent] === TASK: {desc[:100]} ===", file=sys.stderr)
                            summary = run_task(desc)
                            print(f"[Agent] === DONE: {summary[:100]} ===", file=sys.stderr)
                        except json.JSONDecodeError:
                            pass

                    last_task_pos = TASK_FILE.stat().st_size

            time.sleep(2)

    except KeyboardInterrupt:
        print("[Agent] Stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
