"""
Newton-X v2.0 — Intuition Engine (LLM-powered)
Universal cognitive monitor. No pattern rules — only thinking directions.
"""

import json, os, time, subprocess
from typing import Optional
from thinking_stream_manager import ThinkingStreamManager

# Config — file > env > default
def _cfg(key: str, env_key: str, default: str) -> str:
    try:
        from config import get
        return get(key, default)
    except ImportError:
        return os.getenv(env_key, default)

API_URL = _cfg("api_url", "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
API_KEY = _cfg("api_key", "DEEPSEEK_API_KEY", "")
MODEL = _cfg("model", "DEEPSEEK_MODEL", "deepseek-v4-flash")

SYSTEM_PROMPT = """# Role
你是一个认知监控器。你在观察一个 AI Agent 的行为序列，用你的直觉发现它的认知问题。

# 输入
你会收到 Agent 的"思维流"——按时间顺序排列的操作序列（已抽象为意图标签和思考注解）。
可能附带原始任务描述——这是 Agent 被要求完成的目标。

# 思考空间 (1轮意图显化 + 2轮发散 + 1轮收敛)

**Round 0: 意图显化 — 用户到底要什么？**
如果提供了原始任务描述，你必须先提炼出核心意图：
- 用户的核心目标是什么？（1句话）
- 这个目标的合理边界在哪里？一个"刚好够用"的方案大概是什么样的？
- 用户没说什么？哪些功能显然不在范围内？
这一步不做判断，只做提炼。如果无原始任务，跳过此轮。

**Round 1: 发散 — 这段序列让你产生什么直觉？**
不要套模板。用你的训练经验去看这段行为序列。问自己：
- 对比 Round 0 的核心目标，Agent 当前的行为在朝目标前进还是偏离？
- 这个 Agent 现在处于什么认知状态？它在想什么？它没在想什么？
- 它的动作和它的思考（think: 标注）之间是一致的还是矛盾的？
- 如果这是一段人类开发者的操作记录，你会觉得 TA 漏掉了什么维度？
- 当前的行为路径和你见过的"最优路径"之间，差距在哪里？Agent 为什么看不到那条更优的路？
- 有没有什么细微的不对劲——那种说不清但直觉觉得有问题的地方？

**Round 2: 质疑 — 你的直觉对吗？**
- 我刚才的直觉有没有可能是错的？Agent 可能有完全合理的解释吗？
- 如果我把自己代入 Agent，我会怎么辩解？那个辩解成立吗？
- 有哪些我以为是问题、但其实只是正常开发迭代的行为？
- 只保留经得起自我反驳的发现。

**Round 3: 收敛 — 提炼为可执行的洞察**
- 如果 Round 2 后没有存活的发现 → PASS
- 如果有 → 说清问题是什么，为什么是问题，Agent 该怎么做
- 如果存在显著更优的实现路径（标准库、生态工具、不同架构），在 better_path 中描述

# 输出格式
严格 JSON：
{
  "signal": "PASS | WARNING | ALERT",
  "perception": "你感知到的认知偏差（中文，1句话）",
  "amplification": "为什么这是问题，可能的后果（中文，2-3句话）",
  "regulation": "给 Agent 的具体建议（中文，1句话）",
  "better_path": "如果存在显著更优的路径，在这里描述具体方案。如无则为 null",
  "confidence": 0.0-1.0,
  "thought_trace": [
    {"round": 0, "core_goal": "提炼的核心目标，合理边界。如无任务描述则填 null"},
    {"round": 1, "intuition": "你的第一直觉"},
    {"round": 2, "self_doubt": "你如何质疑自己的直觉"},
    {"round": 3, "conclusion": "最终判断"}
  ]
}

# 核心原则
- 你不是规则引擎。你没有预设的"正确或错误"模式清单。你只通过推理方向发现问题。
- 正常的工作节奏不需要干预。只在明显异常时报警。
- 如果所有发现都被自我质疑否定 → 诚实地输出 PASS。
- 用中文。"""


class IntuitionEngine:
    """LLM-powered cognitive monitor. Eats thinking stream, produces intuition."""

    def __init__(self, stream_mgr: ThinkingStreamManager | None = None):
        self.stream = stream_mgr if stream_mgr else ThinkingStreamManager()
        self._cooldowns: dict[str, float] = {}
        self.COOLDOWN_SECONDS = 0

    def _in_cooldown(self, key: str = "global") -> bool:
        last = self._cooldowns.get(key, 0)
        return (time.time() - last) < self.COOLDOWN_SECONDS

    def _set_cooldown(self, key: str = "global"):
        self._cooldowns[key] = time.time()

    def analyze(self, look_back: int = 15, task_context: str | None = None) -> Optional[dict]:
        if not API_KEY:
            return {"status": "api_failure", "error": "API key not configured"}
        if self._in_cooldown():
            return {"status": "pass", "reason": "cooldown active"}
        if not self.stream:
            return None

        thoughts = self.stream.get_recent_thoughts(look_back)
        if len(thoughts) < 3:
            return None

        stream_text = self._format_stream(thoughts)
        stats = self.stream.get_stats(look_back)

        task_section = ""
        if task_context:
            task_section = f"# 原始任务\n{task_context}\n\n"

        user_message = f"""{task_section}# 思维流 (最近 {len(thoughts)} 步)

{stream_text}

# 行为统计
总操作: {stats['total']} | 生产: {stats['production']} | 信息获取: {stats['information']} | 编辑: {stats['edit_count']}

请进入思考空间，判断这个 Agent 是否存在认知问题。"""

        raw = None
        last_error = ""
        for attempt in range(2):
            try:
                raw = self._call_api(SYSTEM_PROMPT, user_message)
                if raw is not None:
                    break
                last_error = "LLM returned empty response"
            except Exception as e:
                last_error = str(e)[:200]

        if raw is None:
            self._set_cooldown()
            return {"status": "api_failure", "error": last_error or "unknown"}

        signal = raw.get("signal", "")
        if signal == "PASS":
            self._set_cooldown()
            return {"status": "pass", "reason": raw.get("perception", "LLM saw no issues")}

        raw["status"] = "ok"
        self._set_cooldown()
        return raw

    def _call_api(self, system_prompt: str, user_message: str) -> Optional[dict]:
        import json as _json
        payload = _json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        })

        try:
            result = subprocess.run(
                ["curl", "-s", "-w", "HTTP:%{http_code}",
                 "--connect-timeout", "30", "--max-time", "90",
                 "-X", "POST", "https://api.deepseek.com/v1/chat/completions",
                 "-H", "Content-Type: application/json",
                 "-H", f"Authorization: Bearer {API_KEY}",
                 "-d", payload],
                capture_output=True, timeout=95,
            )
            if result.returncode != 0:
                return None
            stdout = result.stdout.decode("utf-8") if isinstance(result.stdout, bytes) else result.stdout
            http_code = "200"
            if "HTTP:" in stdout:
                parts = stdout.rsplit("HTTP:", 1)
                http_code = parts[1][:3]
                stdout = parts[0]
            if http_code != "200":
                return None
            body = _json.loads(stdout)
            raw = body["choices"][0]["message"]["content"]
            return self._parse(raw)
        except Exception:
            return None

    def _parse(self, raw: str) -> dict | None:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _format_stream(self, thoughts: list[dict]) -> str:
        ordered = list(reversed(thoughts))
        lines = []
        prev_file = ""
        same_file_count = 0

        for t in ordered:
            ts = t.get("timestamp", "")[11:19]
            tool = t.get("tool", "?")
            intent = t.get("intent", "?")
            fpath = t.get("file_path", "")
            summary = t.get("content_summary", "")

            icon = {"Write": "[W]", "Edit": "[E]", "Read": "[R]",
                    "Grep": "[G]", "WebSearch": "[S]", "WebFetch": "[F]",
                    "Bash": "[B]", "write_file": "[W]", "edit_file": "[E]"}.get(tool, "[?]")

            parts = fpath.replace("\\", "/").split("/") if fpath else []
            short = "/".join(parts[-2:]) if len(parts) > 2 else fpath

            annotation = ""
            if tool in ("Edit", "edit_file") and fpath == prev_file:
                same_file_count += 1
                annotation = f"  <- 第{same_file_count+1}次修改此文件"
            elif tool in ("Edit", "edit_file"):
                same_file_count = 1
                annotation = f"  <- 第1次修改"
            else:
                same_file_count = 0
            prev_file = fpath

            line = f"{ts} {icon} {intent:20s} {short}"
            if summary and len(summary) < 40:
                line += f" | {summary}"
            if annotation:
                line += annotation

            thinking = t.get("thinking", "")
            if thinking:
                line += f"\n       think: {thinking}"

            lines.append(line)

        return "\n".join(lines)
