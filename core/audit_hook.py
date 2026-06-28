#!/usr/bin/env python3
"""
Newton-X Hook — Minimal event collector.
Only writes raw tool call to stream file, exits immediately.
All processing is done by the System 2 Daemon (system2_daemon.py).
"""

import json
import os
import sys
from pathlib import Path

# Configurable path — override via NEWTON_RAW_STREAM env or ~/.newton-x/config.json
def _raw_path():
    try:
        from config import get
        return Path(get("raw_stream"))
    except ImportError:
        return Path(os.getenv("NEWTON_RAW_STREAM", str(Path.home() / ".newton-x" / "newton_raw.jsonl")))

RAW_STREAM = _raw_path()


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("path", tool_input.get("file_path", ""))

    event = {
        "tool_name": tool_name,
        "file_path": file_path,
        "tool_input": tool_input,
        "timestamp": __import__("time").strftime("%H:%M:%S"),
    }

    try:
        RAW_STREAM.parent.mkdir(parents=True, exist_ok=True)
        with open(RAW_STREAM, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never block the tool

    sys.exit(0)


if __name__ == "__main__":
    main()
