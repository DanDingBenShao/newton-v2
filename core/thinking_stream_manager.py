"""
Newton-X v2.0 — Thinking Stream Manager
Maintains structured log of agent tool calls with intent labels.
Persists to thinking_stream.json, max 100 entries.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

def _stream_path():
    try:
        from config import get
        return Path(get("thinking_stream"))
    except ImportError:
        return Path(os.getenv("NEWTON_THINKING_STREAM", str(Path.home() / ".newton-x" / "thinking_stream.json")))

STREAM_FILE = _stream_path()
MAX_ENTRIES = 100


class ThinkingStreamManager:
    """Manages the agent's cognitive activity log."""

    # Display icons (ASCII-safe for Windows CMD)
    ICONS = {
        "Write": "[W]",
        "Edit": "[E]",
        "Read": "[R]",
        "Grep": "[G]",
        "WebSearch": "[S]",
        "WebFetch": "[F]",
        "Bash": "[B]",
        "Glob": "[O]",
        "write_file": "[W]",
        "edit_file": "[E]",
    }

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if STREAM_FILE.exists():
            try:
                return json.loads(STREAM_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "entries": [],
        }

    def _save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        STREAM_FILE.parent.mkdir(parents=True, exist_ok=True)
        STREAM_FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_thought(
        self,
        tool_name: str,
        intent: str,
        context: str,
        file_path: str = "",
        content_summary: str = "",
        thinking: str | None = None,
    ):
        """Record a new thought entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "intent": intent,
            "context": context,
            "file_path": file_path,
            "content_summary": content_summary,
        }
        if thinking:
            entry["thinking"] = thinking
        self.data["entries"].append(entry)

        # Trim to MAX_ENTRIES
        if len(self.data["entries"]) > MAX_ENTRIES:
            self.data["entries"] = self.data["entries"][-MAX_ENTRIES:]

        self._save()

    def get_recent_thoughts(self, n: int = 10) -> list[dict]:
        """Return last N entries, newest first."""
        return list(reversed(self.data["entries"][-n:]))

    def get_thinking_summary(self, last_n: int = 15) -> str:
        """Return an icon-based visual summary of recent thinking."""
        entries = self.data["entries"][-last_n:]
        if not entries:
            return "(尚无思考记录)"

        lines = []
        for e in entries:
            ts = e.get("timestamp", "")[11:19]  # HH:MM:SS
            icon = self.ICONS.get(e.get("tool", "?"), "[?]")
            intent = e.get("intent", "?")
            fname = e.get("file_path", "")
            if fname and len(fname) > 30:
                fname = "..." + fname[-27:]
            lines.append(f"  {ts} {icon} {intent:20s} {fname}")

        header = f"思考流 (最近 {len(entries)} 步):"
        return header + "\n" + "\n".join(lines)

    def get_stats(self, last_n: int = 20) -> dict:
        """Return behavioral stats for recent window."""
        entries = self.data["entries"][-last_n:]
        tools = {}
        for e in entries:
            t = e.get("tool", "?")
            tools[t] = tools.get(t, 0) + 1

        write_count = tools.get("Write", 0) + tools.get("write_file", 0)
        edit_count = tools.get("Edit", 0) + tools.get("edit_file", 0)
        read_count = tools.get("Read", 0)
        search_count = tools.get("Grep", 0) + tools.get("WebSearch", 0) + tools.get("WebFetch", 0)

        return {
            "total": len(entries),
            "production": write_count + edit_count,
            "information": read_count + search_count,
            "write_count": write_count,
            "edit_count": edit_count,
            "read_count": read_count,
            "search_count": search_count,
        }

    def clear(self):
        """Reset everything."""
        self.data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "entries": [],
        }
        self._save()
