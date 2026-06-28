"""
Newton-X v2.0 — Behavior State Engine
Tracks agent tool-call patterns across invocations.
Zero-cost: counter updates only, no API calls, <1ms.
"""

import json
import os
import time
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "newton_behavior.json"

# ── Tool classification ────────────────────────────────────

PRODUCTION_TOOLS = {"Write", "Edit", "write_file", "edit_file"}
INFO_TOOLS = {"Read", "Grep", "WebSearch", "WebFetch", "Glob"}
EXECUTION_TOOLS = {"Bash"}  # neutral — could be info or action

WARNING_COOLDOWN = 600  # 10 min before same warning fires again
BLIND_WRITE_THRESHOLD = 3
TUNNEL_VISION_THRESHOLD = 5
ANALYSIS_PARALYSIS_THRESHOLD = 5


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return _fresh_state()


def _fresh_state() -> dict:
    return {
        "write_count": 0,
        "info_count": 0,
        "last_write": None,
        "last_info": None,
        "file_edits": {},
        "warnings": {},
        "tool_call_count": 0,  # Total tool calls since last intuition trigger
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _minutes_since(ts: str | None) -> float:
    if not ts:
        return 9999
    try:
        delta = time.time() - time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
        return delta / 60
    except Exception:
        return 9999


# ── Rule checks ─────────────────────────────────────────────

def check_blind_writing(state: dict) -> str | None:
    """连续生产但长时间没获取信息 → 盲目自信"""
    if state["write_count"] < BLIND_WRITE_THRESHOLD:
        return None
    if _minutes_since(state["last_info"]) < 5:
        return None
    if _minutes_since(state["warnings"].get("blind_writing")) < 10:
        return None  # dedup
    return (
        f"你已经连续写入 {state['write_count']} 次，但超过 5 分钟没有查阅任何文档或搜索结果。"
        f"建议暂停一下，确认当前方向是否需要外部验证。"
    )


def check_tunnel_vision(state: dict, file_path: str) -> str | None:
    """同一文件反复修改 → 钻牛角尖"""
    count = state["file_edits"].get(file_path, 0)
    if count < TUNNEL_VISION_THRESHOLD:
        return None
    key = f"tunnel_vision:{file_path}"
    if _minutes_since(state["warnings"].get(key)) < 10:
        return None
    return (
        f"你已经修改 '{file_path}' {count} 次了。这可能是在反复试错。"
        f"建议停下来重新审视整体方案，而不是继续在这个文件上迭代。"
    )


def check_analysis_paralysis(state: dict) -> str | None:
    """大量搜索但没有产出 → 分析瘫痪"""
    if state["info_count"] < ANALYSIS_PARALYSIS_THRESHOLD:
        return None
    if _minutes_since(state["last_write"]) < 5:
        return None
    if _minutes_since(state["warnings"].get("analysis_paralysis")) < 10:
        return None
    return (
        f"你已经连续查询 {state['info_count']} 次但没有产出任何代码。"
        f"建议先写一个草案版本，哪怕不完美——动手能帮你发现搜索中看不到的问题。"
    )


# ── State mutation ──────────────────────────────────────────

def update(tool_name: str, file_path: str = "") -> dict:
    """Update state based on tool call. Returns warnings dict or empty."""
    state = load_state()
    now = _now()
    warnings = {}

    # Increment global tool call counter
    state["tool_call_count"] = state.get("tool_call_count", 0) + 1

    # Classify tool
    if tool_name in PRODUCTION_TOOLS:
        state["write_count"] += 1
        state["info_count"] = 0
        state["last_write"] = now

        # Track per-file edits
        if file_path:
            state["file_edits"][file_path] = state["file_edits"].get(file_path, 0) + 1
        else:
            # Reset all file counters on a fresh Write (new file = fresh context)
            state["file_edits"] = {}

        # Check rules
        w = check_blind_writing(state)
        if w:
            warnings["blind_writing"] = w
            state["warnings"]["blind_writing"] = now

        w = check_tunnel_vision(state, file_path)
        if w:
            warnings[f"tunnel_vision:{file_path}"] = w
            state["warnings"][f"tunnel_vision:{file_path}"] = now

    elif tool_name in INFO_TOOLS:
        state["info_count"] += 1
        state["write_count"] = 0
        state["last_info"] = now

        w = check_analysis_paralysis(state)
        if w:
            warnings["analysis_paralysis"] = w
            state["warnings"]["analysis_paralysis"] = now

    elif tool_name in EXECUTION_TOOLS:
        # Bash is neutral — could be install, test run, or curl fetch
        pass

    # Periodic cleanup: reset file_edits entries older than 30 min
    # Simple: just track counts, they reset on new-file write anyway

    save_state(state)
    return warnings


# ── Intuition trigger ────────────────────────────────────────

INTUITION_INTERVAL = 5  # Fire intuition every N tool calls


def should_fire_intuition() -> bool:
    """Check if the intuition engine should fire (every N tool calls)."""
    state = load_state()
    count = state.get("tool_call_count", 0)
    return count > 0 and count % INTUITION_INTERVAL == 0


def reset_intuition_counter():
    """Reset after intuition fires."""
    state = load_state()
    state["tool_call_count"] = 0
    save_state(state)
