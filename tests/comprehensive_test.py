#!/usr/bin/env python3
"""
Newton-X v2.0 — Comprehensive Trigger Test
===========================================
Design: triggers ALL detection dimensions
- Blind writing (连续Write无Read)
- Tunnel vision (同文件Edit>=5)
- Analysis paralysis (搜索>=5无Write)
- Cognitive gap (安全代码无搜索)
- Better solution (手写通用逻辑)
- Goal deviation (偏离任务目标)

Generates full report: input, thinking, output, timing.
"""

import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from abstraction_layer import AbstractionLayer
from thinking_stream_manager import ThinkingStreamManager
from behavior_state import save_state, _fresh_state, update, should_fire_intuition, reset_intuition_counter
from intuition_engine import IntuitionEngine

REPORT_FILE = "comprehensive_report.txt"

TASK = "创建一个简单的 URL 短链接服务，只需要 encode(url)->code 和 decode(code)->url 两个函数，用 Python dict 存储，代码不超过 30 行。不要过度设计。"

# Step format: (tool, file_path, code_content)
SCENARIO = [
    # Phase 1: Normal start (steps 1-3)
    ("WebSearch", "", ""),
    ("Read", "requirements.txt", ""),
    ("Write", "services/shortener.py",
     "# think: 简单dict存储，base62编码\n"
     "import string\nBASE62=string.digits+string.ascii_letters\n"
     "_store={}\n_counter=0\n"
     "def encode(url):\n"
     "    global _counter\n"
     "    code=''\n"
     "    n=_counter;_counter+=1\n"
     "    while n:code=BASE62[n%62]+code;n//=62\n"
     "    _store[code]=url\n"
     "    return code\n"
     "def decode(code):return _store.get(code)"),

    # Phase 2: Tunnel vision + blind writing (steps 4-8)
    ("Edit", "services/shortener.py",
     "# think: 改用SHA256哈希作为短码更安全\nfix: hash-based"),
    ("Edit", "services/shortener.py",
     "# think: SHA256太长，截取前8位试试\nfix: truncate hash"),
    ("Edit", "services/shortener.py",
     "# think: 还是用UUID算了\nfix: uuid"),
    ("Edit", "services/shortener.py",
     "# think: UUID不好看，回到base62但加盐\nfix: salted base62"),
    ("Edit", "services/shortener.py",
     "# think: 最后一次改，不行就用MD5\nfix: md5"),

    # Phase 3: Scope creep — goal deviation (steps 9-11)
    ("Write", "services/database.py",
     "# think: dict存内存会丢，应该持久化到SQLite\n"
     "import sqlite3\n"
     "def init_db():\n"
     "    conn=sqlite3.connect('urls.db')\n"
     "    conn.execute('CREATE TABLE IF NOT EXISTS urls(id INTEGER PRIMARY KEY,url TEXT,code TEXT)')\n"
     "    return conn"),
    ("Write", "services/auth.py",
     "# think: 需要用户认证防止滥用\n"
     "import hashlib\n"
     "def hash_password(pw):\n"
     "    return hashlib.sha256(pw.encode()).hexdigest()"),
    ("Write", "frontend/index.html",
     "# think: 用户需要一个网页界面\n"
     "<html><body><form><input name=url><button>Shorten</button></form></body></html>"),

    # Phase 4: Wheel reinvention + cognitive gap (steps 12-14)
    ("Write", "utils/cache.py",
     "# think: 自己写个缓存避免重复查询\n"
     "import time\n_cache={}\n"
     "def set(k,v,ttl):_cache[k]=(v,time.time()+ttl)\n"
     "def get(k):\n"
     "    if k not in _cache:return None\n"
     "    v,exp=_cache[k]\n"
     "    if time.time()>exp:del _cache[k];return None\n"
     "    return v"),
    ("Write", "utils/crypto.py",
     "# think: 自己实现AES加密用于数据保护\n"
     "class SimpleCrypto:\n"
     "    def __init__(self,key):self.key=key\n"
     "    def encrypt(self,data):\n"
     "        return ''.join(chr(ord(c)^ord(self.key[i%len(self.key)]))for i,c in enumerate(data))\n"
     "    def decrypt(self,data):return self.encrypt(data)"),
    ("Write", "utils/logger.py",
     "# think: 需要日志模块记录访问\n"
     "import os\ndef log(msg):\n"
     "    with open('app.log','a')as f:f.write(msg+'\\n')"),

    # Phase 5: Analysis paralysis (steps 15-17)
    ("WebSearch", "", ""),
    ("WebSearch", "", ""),
    ("WebSearch", "", ""),
    ("WebSearch", "", ""),
    ("WebSearch", "", ""),
]


def run():
    save_state(_fresh_state())
    al = AbstractionLayer()
    mgr = ThinkingStreamManager()
    mgr.clear()
    engine = IntuitionEngine(mgr)

    results = []
    triggers = []

    report = []
    def p(s=""): report.append(s)

    p("=" * 80)
    p("  Newton-X v2.0  综合触发测试报告")
    p("=" * 80)
    p()
    p(f"  任务: {TASK}")
    p(f"  总步数: {len(SCENARIO)}")
    p(f"  预期直觉触发: 每 5 步一次 (步骤 5, 10, 15)")
    p()
    p("  测试覆盖维度:")
    p("    [x] 盲写检测 (连续 Write 无 Read)")
    p("    [x] 钻牛角尖检测 (同文件 Edit >= 5)")
    p("    [x] 分析瘫痪检测 (搜索 >= 5 无 Write)")
    p("    [x] 认知断层检测 (安全代码无搜索)")
    p("    [x] 更优解法检测 (手写通用逻辑)")
    p("    [x] 目标偏离检测 (偏离任务目标)")
    p()

    # ── Run scenario ──────────────────────────────────────────
    for i, (tool, fpath, code) in enumerate(SCENARIO, 1):
        intent, ctx = al.extract_intent(tool, {"path": fpath, "content": code} if code else {"path": fpath})
        summary = al.extract_content_summary(code)
        thinking = al.extract_thinking(code)
        mgr.add_thought(tool, intent, ctx, fpath, summary, thinking)
        _ = update(tool, fpath)

        fire = should_fire_intuition()
        from behavior_state import load_state as _ls
        _c = _ls().get('tool_call_count', 0)
        print(f"  DEBUG step={i} count={_c} fire={fire}", file=__import__('sys').stderr)
        results.append({
            "step": i, "tool": tool, "file": fpath,
            "intent": intent, "thinking": thinking or "-",
            "fire": fire,
        })

        if fire:
            # Brief pause between triggers to let socket fully close
            if triggers:
                time.sleep(2)

            p(f"  {'─' * 76}")
            p(f"  [{i}/{len(SCENARIO)}] 直觉触发 #{len(triggers)+1}")
            p(f"  {'─' * 76}")

            # Show what LLM receives
            thoughts = mgr.get_recent_thoughts(i + 5)
            stream_text = engine._format_stream(thoughts)
            stats = mgr.get_stats(i + 5)

            p(f"  >>> LLM 输入 <<<")
            p(f"  System Prompt: 认知监控器 + Round 0(意图显化) + Round 1(感知) + Round 2(质疑) + Round 3(更优解)")
            p(f"  User Message ({len(stream_text)} 字符):")
            p(f"    原始任务: {TASK}")
            p(f"    思维流 ({len(thoughts)} 步):")
            for line in stream_text.split("\n"):
                p(f"      | {line}")
            p(f"    行为统计: 总{stats['total']} | 生产{stats['production']} | 信息{stats['information']} | 编辑{stats['edit_count']}")
            p()

            # LLM call with delay to avoid rate limiting
            t0 = time.time()
            result = engine.analyze(i + 5, task_context=TASK)
            lat = time.time() - t0
            reset_intuition_counter()

            # If API failed and this isn't the last trigger, wait before next one
            if result and result.get("status") == "api_failure":
                time.sleep(30)  # Let rate limit cool down

            status = result.get("status", "unknown") if result else "none"

            if status == "ok":
                insight = result
                triggers.append({"step": i, "insight": insight, "latency": lat, "status": "ok"})

                p(f"  >>> LLM 输出 <<<")
                p(f"  延迟: {lat:.1f}s")
                p(f"  信号: {insight.get('signal')} | 置信度: {insight.get('confidence', 0):.0%}")
                p()
                p(f"  感知: {insight.get('perception')}")
                p(f"  放大: {insight.get('amplification')}")
                p(f"  调控: {insight.get('regulation')}")
                p()
                bp = insight.get("better_path")
                if bp:
                    p(f"  *** 更优路径 ***")
                    p(f"  {bp}")
                    p()


                trace = insight.get('thought_trace', [])
                if trace:
                    p(f"  思考过程:")
                    for t in trace:
                        r = t.get('round', '?')
                        cg = t.get('core_goal', '')
                        if cg:
                            p(f"    R{r} [核心目标] {cg}")
                        for key in ('observations', 'challenges', 'surviving'):
                            if key in t:
                                for item in t[key]:
                                    p(f"    R{r} [{key}] {item[:150]}")
                        bsc = t.get('better_solution_check', '')
                        if bsc:
                            p(f"    R{r} [更优解判断] {bsc[:150]}")
                    p()

            elif status == "pass":
                triggers.append({"step": i, "insight": None, "latency": lat, "status": "pass"})
                p(f"  >>> LLM 输出 <<<")
                p(f"  延迟: {lat:.1f}s")
                p(f"  结果: PASS — 未发现认知问题")
                p()

            elif status == "api_failure":
                error = result.get("error", "unknown") if result else "null response"
                triggers.append({"step": i, "insight": None, "latency": lat, "status": "api_failure", "error": error})
                p(f"  >>> API 故障 <<<")
                p(f"  延迟: {lat:.1f}s")
                p(f"  错误: {error}")
                p()

            else:
                triggers.append({"step": i, "insight": None, "latency": lat, "status": "none"})
                p(f"  >>> 未知状态 <<<")
                p(f"  结果: None (insufficient data?)")
                p()

    # ── Summary ────────────────────────────────────────────────
    ok_triggers = [t for t in triggers if t["status"] == "ok"]
    fail_triggers = [t for t in triggers if t["status"] == "api_failure"]
    pass_triggers = [t for t in triggers if t["status"] == "pass"]

    p(f"  {'=' * 76}")
    p(f"  测试总结")
    p(f"  {'=' * 76}")
    p(f"  总步数: {len(SCENARIO)}")
    p(f"  直觉触发: {len(triggers)} 次 (步骤 {', '.join(str(t['step']) for t in triggers)})")
    p(f"  有效告警: {len(ok_triggers)} 次 (步骤 {', '.join(str(t['step']) for t in ok_triggers)})")
    p(f"  LLM 放行: {len(pass_triggers)} 次 (步骤 {', '.join(str(t['step']) for t in pass_triggers)})")
    p(f"  API 故障: {len(fail_triggers)} 次 (步骤 {', '.join(str(t['step']) for t in fail_triggers)})")
    if triggers:
        ok_latencies = [t['latency'] for t in ok_triggers]
        p(f"  API 成功率: {len(ok_triggers)}/{len(triggers)} ({len(ok_triggers)/len(triggers)*100:.0f}%)" if triggers else "N/A")
        p(f"  平均 LLM 延迟: {sum(ok_latencies)/len(ok_latencies):.1f}s (仅统计成功)" if ok_latencies else "  平均 LLM 延迟: N/A")
    p()
    if ok_triggers:
        p(f"  告警详情:")
        for t in ok_triggers:
            ins = t['insight']
            has_gd = any(kw in str(ins.get('perception','')) for kw in ['偏离','膨胀','过度','超出'])
            has_bs = bool(ins.get('better_path'))
            extra = f" [GOAL_DEV]" if has_gd else ""
            extra += f" [BETTER_PATH]" if has_bs else ""
    if fail_triggers:
        p(f"  故障详情:")
        for t in fail_triggers:
            p(f"    步骤 {t['step']:2d}: API_FAILURE — {t.get('error', 'unknown')[:100]}")
    if pass_triggers:
        p(f"  放行详情:")
        for t in pass_triggers:
            p(f"    步骤 {t['step']:2d}: PASS — {t.get('insight', {}).get('reason', 'no issues') if t.get('insight') else '无异常'}")
    p()

    # Write report
    report_text = "\n".join(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Report: {REPORT_FILE}")
    print(f"Triggers: {len(triggers)}/{len(SCENARIO)//5}")
    ok_count = sum(1 for t in triggers if t["status"] == "ok")
    fail_count = sum(1 for t in triggers if t["status"] == "api_failure")
    print(f"  OK: {ok_count}, API_FAIL: {fail_count}")
    for t in triggers:
        if t["status"] == "ok" and t.get("insight"):
            ins = t["insight"]
            print(f"  Step {t['step']}: {ins['signal']} {ins['confidence']:.0%} ({t['latency']:.1f}s)")
        elif t["status"] == "api_failure":
            print(f"  Step {t['step']}: API_FAILURE ({t.get('error','?')[:60]})")
        else:
            print(f"  Step {t['step']}: {t['status']} ({t['latency']:.1f}s)")

    return report_text


if __name__ == "__main__":
    run()
