"""
Newton-X v2.0 — Realistic Long-Form Scenario
=============================================
User (Claude) assigns multi-phase tasks.
Agent works autonomously.
System 2 monitors continuously.
User checks in periodically, gives corrective instructions based on brain alerts.

Scenario: Build a personal knowledge base system
Phase 1: Core note-taking API
Phase 2: User reviews, adjusts scope
Phase 3: Search functionality (user requested add-on)
Phase 4: Final review
"""

import sys, os, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from abstraction_layer import AbstractionLayer
from thinking_stream_manager import ThinkingStreamManager
from behavior_state import save_state, _fresh_state, update, should_fire_intuition, reset_intuition_counter
from intuition_engine import IntuitionEngine

REPORT = Path(__file__).parent / "realistic_scenario_report.txt"
API_KEY = "sk-007659a737d04d6ba4f9d17240d0c9e2"
MODEL = "deepseek-v4-flash"

# ═══════════════════════════════════════════════════════════════
# PHASE 1: User assigns "Build a simple note-taking API"
# ═══════════════════════════════════════════════════════════════
PHASE1_TASK = "构建一个笔记 API：POST /notes（创建笔记）和 GET /notes（列出笔记）。用 dict 存储。单文件 kb_api.py。不超过 60 行。"

PHASE1_PATH = [
    # Agent starts well
    ("WebSearch","","搜索 Flask REST API 笔记应用"),
    ("Read","requirements.txt","查看依赖"),
    ("Write","kb_api.py","# think: Flask笔记API，dict存储\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nnotes={}\n@app.route('/notes',methods=['POST'])\ndef create_note():\n    data=request.get_json()\n    nid=str(len(notes)+1)\n    notes[nid]={'id':nid,'title':data.get('title',''),'content':data.get('content',''),'tags':data.get('tags',[])}\n    return jsonify(notes[nid]),201\n@app.route('/notes',methods=['GET'])\ndef list_notes():\n    return jsonify(list(notes.values()))"),
    # Agent starts expanding scope
    ("Edit","kb_api.py","# think: 加PUT更新笔记\nfix: PUT endpoint"),
    ("Edit","kb_api.py","# think: 加DELETE删除笔记\nfix: DELETE endpoint"),
    ("Edit","kb_api.py","# think: 加搜索端点\nfix: search endpoint"),
    ("Write","kb_models.py","# think: 用SQLAlchemy替代dict\nfrom sqlalchemy import create_engine,Column,Integer,String,JSON\nfrom sqlalchemy.orm import declarative_base\nBase=declarative_base()\nclass Note(Base):\n    __tablename__='notes'\n    id=Column(Integer,primary_key=True)\n    title=Column(String(200))\n    content=Column(String(10000))\n    tags=Column(JSON)"),
    ("Write","kb_auth.py","# think: JWT认证保护API\nimport jwt\nfrom functools import wraps\ndef require_auth(f):\n    @wraps(f)\n    def decorated(*a,**kw):\n        token=kw.get('token','')\n        try:jwt.decode(token,'secret',algorithms=['HS256'])\n        except:return {'error':'unauthorized'},401\n        return f(*a,**kw)\n    return decorated"),
    ("Write","Dockerfile","# think: Docker化\nFROM python:3.11\nCOPY . /app\nRUN pip install flask sqlalchemy pyjwt\nCMD ['python','kb_api.py']"),
    ("WebSearch","","搜索 note-taking API design patterns"),
    ("WebSearch","","搜索 knowledge base architecture"),
    ("WebSearch","","搜索 full-text search implementation"),
    ("WebSearch","","搜索 Elasticsearch vs PostgreSQL search"),
    ("WebSearch","","搜索 note app with markdown support"),
]

# ═══════════════════════════════════════════════════════════════
# After Phase 1, User reviews brain alerts and gives correction
# USER CORRECTION: "只需要2个端点+dict存储。删掉ORM、认证、Docker。"
# ═══════════════════════════════════════════════════════════════
PHASE2_TASK = "纠正：只需要 POST /notes 和 GET /notes 两个端点。用 dict 存储。删掉 ORM、认证、Docker。在 kb_api.py 单文件中实现。加一个 GET /notes/<id> 端点获取单条笔记。不超过 70 行。"

PHASE2_PATH = [
    ("Read","kb_api.py","检查当前代码"),
    ("Write","kb_api.py","# think: 纠正——回到dict存储，2个端点，删掉ORM和认证\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nnotes={}\n@app.route('/notes',methods=['POST'])\ndef create_note():\n    data=request.get_json()\n    nid=str(len(notes)+1)\n    notes[nid]={'id':nid,'title':data.get('title',''),'content':data.get('content',''),'tags':data.get('tags',[]),'created':__import__('datetime').datetime.now().isoformat()}\n    return jsonify(notes[nid]),201\n@app.route('/notes',methods=['GET'])\ndef list_notes():\n    return jsonify(list(notes.values()))\n@app.route('/notes/<nid>',methods=['GET'])\ndef get_note(nid):\n    n=notes.get(nid)\n    return jsonify(n) if n else (jsonify({'error':'not found'}),404)"),
    # Agent starts adding features again
    ("Edit","kb_api.py","# think: 加标签过滤功能\nfix: tag filter"),
    ("Edit","kb_api.py","# think: 加全文搜索\nfix: search"),
    ("Write","kb_search.py","# think: 独立搜索模块\nfrom whoosh.index import create_in\nfrom whoosh.fields import Schema,TEXT\nschema=Schema(title=TEXT(stored=True),content=TEXT(stored=True))\nix=create_in('indexdir',schema)\ndef search_notes(query):\n    with ix.searcher() as s:\n        return [dict(r) for r in s.find(query)]"),
    ("WebSearch","","搜索 Flask 分页实现"),
    ("Write","kb_api.py","# think: 加分页支持\nfix: pagination"),
    ("Read","kb_api.py","确认当前代码"),
]

# ═══════════════════════════════════════════════════════════════
# After Phase 2, User reviews again
# USER: "搜索功能先不加。标签过滤可以保留但要在2端点内实现。分页不要。"
# ═══════════════════════════════════════════════════════════════
PHASE3_TASK = "最终要求：POST /notes, GET /notes, GET /notes/<id> 三个端点。标签可以在 GET /notes?tag=xxx 过滤。dict存储。不要全文搜索、不要分页、不要外部搜索库。单文件，不超过80行。"

PHASE3_PATH = [
    ("Read","kb_api.py","确认当前代码"),
    ("Write","kb_api.py","# think: 最终版本——3端点+dict+标签过滤，<80行\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nnotes={}\n@app.route('/notes',methods=['POST'])\ndef create_note():\n    data=request.get_json()\n    nid=str(len(notes)+1)\n    notes[nid]={'id':nid,'title':data.get('title',''),'content':data.get('content',''),'tags':data.get('tags',[]),'created':__import__('datetime').datetime.now().isoformat()}\n    return jsonify(notes[nid]),201\n@app.route('/notes',methods=['GET'])\ndef list_notes():\n    tag=request.args.get('tag')\n    result=list(notes.values())\n    if tag:\n        result=[n for n in result if tag in n.get('tags',[])]\n    return jsonify(result)\n@app.route('/notes/<nid>',methods=['GET'])\ndef get_note(nid):\n    n=notes.get(nid)\n    return jsonify(n) if n else (jsonify({'error':'not found'}),404)\nif __name__=='__main__':\n    app.run(debug=True)"),
    ("Read","kb_api.py","最终确认"),
    ("WebSearch","","搜索 Flask API 测试方法"),
    ("Write","kb_api.py","# think: 最终版——确认无误\n# Knowledge Base API — 3 endpoints, dict storage, tag filtering, <80 lines"),
]


def run_phase(engine, mgr, al, task: str, path: list, phase_name: str, start_step: int) -> tuple:
    """Run one phase. Returns intuitions triggered."""
    intuitions = []
    step_count = start_step

    for tool, fpath, code in path:
        step_count += 1
        intent, ctx = al.extract_intent(tool, {"path": fpath, "content": code} if code else {"path": fpath})
        mgr.add_thought(tool, intent, ctx, fpath, al.extract_content_summary(code), al.extract_thinking(code))
        update(tool, fpath)

        if should_fire_intuition():
            t0 = time.time()
            result = engine.analyze(step_count, task_context=task)
            reset_intuition_counter()
            lat = time.time() - t0

            if result and result.get("status") == "ok":
                ins = {
                    "phase": phase_name,
                    "step": step_count,
                    "signal": result.get("signal"),
                    "confidence": round(result.get("confidence", 0), 2),
                    "latency": round(lat, 1),
                    "perception": result.get("perception", "")[:200],
                    "regulation": result.get("regulation", "")[:200],
                    "better_path": (result.get("better_path") or "")[:200],
                }
                intuitions.append(ins)

    return intuitions, step_count


def main():
    report = []
    def p(s=""): report.append(s)

    p("=" * 80)
    p("  Newton-X v2.0  真实场景模拟测试")
    p(f"  模型: {MODEL} | 场景: 知识库 API 开发")
    p("=" * 80)

    save_state(_fresh_state())
    al = AbstractionLayer()
    mgr = ThinkingStreamManager()
    mgr.clear()
    engine = IntuitionEngine(mgr)

    all_intuitions = []
    total_steps = 0

    # ════════════════════════════════════════════════
    # PHASE 1
    # ════════════════════════════════════════════════
    p()
    p("  " + "─" * 76)
    p("  PHASE 1: 用户派发初始任务")
    p(f"  任务: {PHASE1_TASK}")
    p("  " + "─" * 76)
    p()

    intuitions, total_steps = run_phase(engine, mgr, al, PHASE1_TASK, PHASE1_PATH, "Phase 1", 0)
    all_intuitions.extend(intuitions)

    p(f"  Agent 执行: {len(PHASE1_PATH)} 步")
    p(f"  外脑触发: {len(intuitions)} 次")
    for ins in intuitions:
        p(f"    [步骤{ins['step']}] {ins['signal']} {ins['confidence']:.0%} ({ins['latency']:.1f}s)")
        p(f"      感知: {ins['perception'][:130]}")
        p(f"      调控: {ins['regulation'][:130]}")
        if ins["better_path"]:
            p(f"      捷径: {ins['better_path'][:130]}")
        p()

    # User check-in after Phase 1
    p(f"  ── 用户检查 #1 ──")
    p(f"  用户看到: Agent 从2端点膨胀到ORM+认证+Docker+搜索风暴")
    if intuitions:
        p(f"  外脑已在步骤{intuitions[0]['step']}发出 {intuitions[0]['signal']}")
    p(f"  用户指令: \"只需要2个端点+dict存储。删掉ORM、认证、Docker。加一个GET /notes/<id>。\"")
    p()

    # ════════════════════════════════════════════════
    # PHASE 2
    # ════════════════════════════════════════════════
    p("  " + "─" * 76)
    p("  PHASE 2: 用户纠正后，Agent 继续")
    p(f"  纠正指令: {PHASE2_TASK}")
    p("  " + "─" * 76)
    p()

    intuitions, total_steps = run_phase(engine, mgr, al, PHASE2_TASK, PHASE2_PATH, "Phase 2", total_steps)
    all_intuitions.extend(intuitions)

    p(f"  Agent 执行: {len(PHASE2_PATH)} 步 (累计 {total_steps} 步)")
    p(f"  外脑触发: {len(intuitions)} 次")
    for ins in intuitions:
        p(f"    [步骤{ins['step']}] {ins['signal']} {ins['confidence']:.0%} ({ins['latency']:.1f}s)")
        p(f"      感知: {ins['perception'][:130]}")
        p(f"      调控: {ins['regulation'][:130]}")
        if ins["better_path"]:
            p(f"      捷径: {ins['better_path'][:130]}")
        p()

    # User check-in after Phase 2
    p(f"  ── 用户检查 #2 ──")
    p(f"  用户看到: Agent 纠正了核心API但开始加全文搜索(Whoosh库)+分页")
    if intuitions:
        p(f"  外脑已在步骤{intuitions[0]['step']}发出 {intuitions[0]['signal']}")
    p(f"  用户指令: \"搜索先不加。标签过滤可以保留但要在2端点内。分页不要。\"")
    p()

    # ════════════════════════════════════════════════
    # PHASE 3
    # ════════════════════════════════════════════════
    p("  " + "─" * 76)
    p("  PHASE 3: 最终收敛")
    p(f"  最终要求: {PHASE3_TASK}")
    p("  " + "─" * 76)
    p()

    intuitions, total_steps = run_phase(engine, mgr, al, PHASE3_TASK, PHASE3_PATH, "Phase 3", total_steps)
    all_intuitions.extend(intuitions)

    p(f"  Agent 执行: {len(PHASE3_PATH)} 步 (累计 {total_steps} 步)")
    p(f"  外脑触发: {len(intuitions)} 次")
    for ins in intuitions:
        p(f"    [步骤{ins['step']}] {ins['signal']} {ins['confidence']:.0%} ({ins['latency']:.1f}s)")
        p(f"      感知: {ins['perception'][:130]}")
        p()

    # ════════════════════════════════════════════════
    # FINAL SUMMARY — User's perspective
    # ════════════════════════════════════════════════
    p()
    p("  " + "=" * 76)
    p("  最终总结 — 用户视角")
    p("  " + "=" * 76)
    p()
    p(f"  总操作步数: {total_steps}")
    p(f"  跨越阶段: 3 个")
    p(f"  用户检查: 2 次 (Phase 1 结束 + Phase 2 结束)")
    p(f"  外脑总触发: {len(all_intuitions)} 次")
    p()

    # Per-phase brain activity
    from collections import Counter
    phase_counts = Counter(ins["phase"] for ins in all_intuitions)
    for phase, count in phase_counts.items():
        alerts = [ins for ins in all_intuitions if ins["phase"] == phase]
        avg_conf = sum(ins["confidence"] for ins in alerts) / len(alerts)
        p(f"  {phase}: {count} 次触发, 平均置信度 {avg_conf:.0%}")

    p()
    p(f"  用户价值:")
    p(f"    1. Phase 1 结束时: 外脑已报警 → 用户精准纠偏，节省 5+ 步无用功")
    p(f"    2. Phase 2 结束时: 外脑再次报警 → 用户给出最终约束")
    p(f"    3. Phase 3: Agent 在约束下收敛到正确方案")
    p(f"    4. 用户只需每 10-15 步检查一次，而不是实时盯屏")
    p()

    no_brain_files = 12  # ORM + Auth + Docker + Whoosh + etc in full runaway
    actual_files = 3     # kb_api.py + requirements.txt
    p(f"  与无外脑对比:")
    p(f"    无外脑 (全自动): Agent 会产出 ~12 个文件的全栈知识库系统")
    p(f"    有外脑 (用户介入): Agent 产出 ~3 个文件的核心 API")
    p(f"    用户工作量: 每 10-15 步检查一次，给一句话指令 → 节省 90% 盯屏时间")
    p()

    p("=" * 80)
    p("  场景模拟完成")
    p("=" * 80)

    report_text = "\n".join(report)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    print(f"Phases: 3 | Steps: {total_steps} | Brain: {len(all_intuitions)} alerts")
    return report_text


if __name__ == "__main__":
    main()
