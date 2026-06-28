#!/usr/bin/env python3
"""
Newton-X System 2 Daemon + Monitor (unified)
- Tails raw hook events
- Runs full v2.0 pipeline: abstraction + behavior + thinking + intuition
- Displays real-time cards
"""

import json
import os
import sys
import time
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────

HOME = Path.home()
RAW_STREAM = HOME / ".claude" / "newton_raw.jsonl"       # Hook writes here
AUDIT_STREAM = HOME / ".claude" / "audit_stream.jsonl"    # Monitor output
PID_FILE = HOME / ".claude" / "newton_monitor.pid"

# ── v2.0 Modules ─────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from abstraction_layer import AbstractionLayer
from thinking_stream_manager import ThinkingStreamManager
from behavior_state import update, load_state, save_state, _fresh_state, should_fire_intuition, reset_intuition_counter

# Lazy import — only when needed
_intuition = None

def get_intuition():
    global _intuition
    if _intuition is None:
        from intuition_engine import IntuitionEngine
        _intuition = IntuitionEngine(None)  # We'll pass stream mgr later
    return _intuition

# ── Display ──────────────────────────────────────────────────

R = "\033[91m"; Y = "\033[93m"; G = "\033[92m"; C = "\033[96m"
D = "\033[2m"; BD = "\033[1m"; X = "\033[0m"; CLR = "\033[2J\033[H"

RISK_CN = {"LOW": "低", "MEDIUM": "中", "HIGH": "高"}
VECTOR_CN = {"A": "源头", "B": "替代", "C": "时空", "D": "反事实", "?": "?"}

def render(entries: list[dict], intuition_results: list[dict]):
    # Move cursor to top-left WITHOUT clearing screen — no flicker
    sys.stdout.write("\033[H")
    sys.stdout.flush()

    # Print with enough lines to overwrite previous frame
    output_lines = []
    output_lines.append(f"{BD}{C}Newton-X System 2  实时监控{X}")
    output_lines.append("")

    acts = {"SKIP": 0, "PASS": 0, "WARN": 0, "BLOCK": 0}
    for e in entries:
        a = e.get("action", "SKIP")
        if a in acts: acts[a] += 1

    output_lines.append(f"  累计 {BD}{len(entries)}{X} 次  "
          f"|  {R}拦截 {acts['BLOCK']}{X}  "
          f"|  {Y}警告 {acts['WARN']}{X}  "
          f"|  {G}通过 {acts['PASS']}{X}  "
          f"|  {D}跳过 {acts['SKIP']}{X}")
    output_lines.append("")

    # Show intuition insights first
    for ins in intuition_results[-2:]:
        bar = f"{R}{BD}" if ins.get("signal") == "ALERT" else f"{Y}{BD}"
        output_lines.append(f"{bar}{'─'*60}{X}")
        output_lines.append(f"  {BD}外脑直觉{X}  置信度 {ins.get('confidence', 0):.0%}")
        output_lines.append(f"  {ins.get('perception', '')}")
        output_lines.append(f"  -> {ins.get('regulation', '')}")
        bs = ins.get("better_solution")
        if bs:
            output_lines.append(f"  {G}更优解法:{X}")
            for line in bs.split("\n")[:6]:
                output_lines.append(f"  {line}")
        output_lines.append("")

    # Show last 3 audit events
    for e in reversed(entries[-3:]):
        fname = e.get("file_path", "?")
        act = e.get("action", "?")
        sig = e.get("signal", "?")
        vec = e.get("primary_vector", "?")
        conf = e.get("confidence", 0)
        dur = e.get("duration_ms", 0)
        reason = e.get("reasoning", "")
        suggestion = e.get("suggestion", "")

        if act == "BLOCK": bar, act_t = f"{R}{BD}", f"{R}已拦截{X}"
        elif act == "WARN": bar, act_t = f"{Y}{BD}", f"{Y}已警告{X}"
        elif sig == "PASS": bar, act_t = f"{G}", f"{G}已放行{X}"
        else: bar, act_t = f"{D}", f"{D}已跳过{X}"

        output_lines.append(f"{bar}{'─'*60}{X}")
        output_lines.append(f"  {BD}{fname}{X}  |  {act_t}  |  向量 {VECTOR_CN.get(vec, vec)}  |  {conf:.0%}  |  {dur}ms")
        if reason: output_lines.append(f"  {reason}")
        if suggestion: output_lines.append(f"  -> {suggestion}")
        output_lines.append("")

    # Counter
    state = load_state()
    count = state.get("tool_call_count", 0)
    next_fire = 5 - (count % 5) if count > 0 else 5
    output_lines.append(f"{D}Ctrl+C 退出 | 下次直觉触发: {next_fire} 步后{X}")

    # Pad to ~40 lines to overwrite previous frame
    while len(output_lines) < 40:
        output_lines.append("")

    # Single write — no flicker
    sys.stdout.write("\n".join(output_lines))
    sys.stdout.flush()


# ── Event processing ─────────────────────────────────────────

al = AbstractionLayer()
mgr = ThinkingStreamManager()

def process_event(event: dict) -> dict | None:
    """Run full v2.0 pipeline on one raw event. Returns audit result dict."""
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    fpath = tool_input.get("path", tool_input.get("file_path", ""))
    code = tool_input.get("content", tool_input.get("new_str", ""))

    # 1. Abstraction
    intent, ctx = al.extract_intent(tool, tool_input)
    summary = al.extract_content_summary(code) if code else ""
    thinking = al.extract_thinking(code) if code else None

    # 2. Behavior state
    warnings = update(tool, fpath)

    # 3. Thinking stream
    mgr.add_thought(tool, intent, ctx, fpath, summary, thinking)

    # 4. Build result
    result = {
        "timestamp": time.strftime("%H:%M:%S"),
        "file_path": fpath,
        "risk_level": "INFO",
        "duration_ms": 0,
        "signal": "INFO",
        "action": "PASS",
        "reasoning": intent,
        "suggestion": "",
        "primary_vector": "?",
        "confidence": 0.0,
    }

    # Behavior warnings
    if warnings:
        result["signal"] = "BEHAVIOR"
        result["action"] = "WARN"
        result["reasoning"] = list(warnings.values())[0]

    return result


def fire_intuition() -> dict | None:
    """Fire LLM intuition engine. Returns insight dict or None."""
    engine = get_intuition()
    engine.stream = mgr  # Wire the shared stream
    insight = engine.analyze(17)
    reset_intuition_counter()
    return insight


# ── Main loop ────────────────────────────────────────────────

def main():
    # Init state
    save_state(_fresh_state())
    mgr.clear()

    # Write PID
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    print(f"{C}Newton-X System 2 启动中...{X}")
    print(f"  原始事件: {RAW_STREAM}")
    print(f"  审计输出: {AUDIT_STREAM}")
    print()

    # Ensure files exist
    RAW_STREAM.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_STREAM.parent.mkdir(parents=True, exist_ok=True)
    RAW_STREAM.touch()
    AUDIT_STREAM.touch()

    # Load existing events (don't fire intuition for historical data)
    if RAW_STREAM.exists():
        with open(RAW_STREAM, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        result = process_event(event)
                        if result:
                            entries.append(result)
                    except Exception:
                        pass
        # Reset counter after loading history so intuition fires at the right time
        save_state(_fresh_state())

    # Now open in tail mode for new events
    raw_fh = open(RAW_STREAM, "r", encoding="utf-8")
    raw_fh.seek(0, 2)

    entries: list[dict] = []
    intuitions: list[dict] = []
    current_task: str | None = None
    last_render = 0

    try:
        while True:
            had_new = False

            # Read new raw events
            while True:
                where = raw_fh.tell()
                line = raw_fh.readline()
                if not line:
                    raw_fh.seek(where)
                    break
                had_new = True
                try:
                    event = json.loads(line)
                    result = process_event(event)
                    if result:
                        entries.append(result)
                        # Write to audit stream for external consumers
                        with open(AUDIT_STREAM, "a", encoding="utf-8") as f:
                            f.write(json.dumps(result, ensure_ascii=False) + "\n")

                    # Check intuition trigger
                    if should_fire_intuition():
                        insight = fire_intuition(current_task)
                        if insight:
                            intuitions.append(insight)
                            # Write intuition to audit stream
                            ins_entry = {
                                "timestamp": time.strftime("%H:%M:%S"),
                                "file_path": "",
                                "risk_level": "INFO",
                                "signal": insight.get("signal", "WARNING"),
                                "action": "WARN",
                                "reasoning": insight.get("perception", ""),
                                "suggestion": insight.get("regulation", ""),
                                "better_solution": insight.get("better_solution", ""),
                                "primary_vector": "B",
                                "confidence": insight.get("confidence", 0),
                                "duration_ms": 0,
                                "type": "intuition",
                            }
                            entries.append(ins_entry)
                            with open(AUDIT_STREAM, "a", encoding="utf-8") as f:
                                f.write(json.dumps(ins_entry, ensure_ascii=False) + "\n")
                except Exception:
                    pass

            if had_new:
                render(entries, intuitions)
                last_render = time.time()

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n{Y}监控已停止。{X}")
    finally:
        try: PID_FILE.unlink()
        except: pass


if __name__ == "__main__":
    main()
