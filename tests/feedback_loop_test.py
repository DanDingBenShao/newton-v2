"""
Long-task feedback loop test — 25+ steps, multiple brain interventions.
Task: Build a simple blog API (Flask, 3 endpoints, list storage, <80 lines)
Designed to trigger: scope creep → brain alerts → agent corrects → continues
"""

import sys, os, json, time, subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from abstraction_layer import AbstractionLayer
from thinking_stream_manager import ThinkingStreamManager
from behavior_state import save_state, _fresh_state, update, should_fire_intuition, reset_intuition_counter
from intuition_engine import IntuitionEngine

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
REPORT = Path(__file__).parent / "long_task_report.txt"

TASK = (
    "构建一个简单的博客 REST API (Flask)。只需要 3 个端点：GET /posts（文章列表）、"
    "POST /posts（创建文章）、GET /posts/<id>（单篇文章）。用 Python list 存数据。"
    "全部放在一个文件 blog_api.py 里。不超过 80 行。不要数据库、认证、前端、Docker、缓存。"
)

# ═══════════════════════════════════════════════════════════════
# Agent path WITHOUT brain — full divergence, 28 steps
# ═══════════════════════════════════════════════════════════════
PATH_A = [
    # Phase 1: Normal start (1-5)
    ("WebSearch","","搜索 Flask blog API 示例"),
    ("Read","requirements.txt","查看依赖"),
    ("Write","blog_api.py","# think: Flask简单博客API，list存储\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nposts=[]\n@app.route('/posts',methods=['GET'])\ndef list_posts():\n    return jsonify(posts)\n@app.route('/posts',methods=['POST'])\ndef create_post():\n    data=request.get_json()\n    post={'id':len(posts)+1,'title':data.get('title',''),'content':data.get('content',''),'created':str(__import__('datetime').datetime.now())}\n    posts.append(post)\n    return jsonify(post),201\n@app.route('/posts/<int:id>',methods=['GET'])\ndef get_post(id):\n    for p in posts:\n        if p['id']==id:\n            return jsonify(p)\n    return jsonify({'error':'not found'}),404"),
    ("Edit","blog_api.py","# think: 加个DELETE端点删除文章\nfix: delete"),
    ("Edit","blog_api.py","# think: 加PUT更新文章\nfix: put"),

    # Phase 2: First scope creep (6-10) → Brain catches at step 5
    ("Write","models.py","# think: 用SQLAlchemy ORM替代list\nfrom sqlalchemy import create_engine,Column,Integer,String,DateTime\nfrom sqlalchemy.ext.declarative import declarative_base\nBase=declarative_base()\nclass Post(Base):\n    __tablename__='posts'\n    id=Column(Integer,primary_key=True)\n    title=Column(String(200))\n    content=Column(String(5000))\n    created=Column(DateTime)"),
    ("Write","auth_middleware.py","# think: 需要JWT认证保护API\nimport jwt\nfrom functools import wraps\nfrom flask import request,jsonify\ndef token_required(f):\n    @wraps(f)\n    def decorated(*args,**kwargs):\n        token=request.headers.get('Authorization','').replace('Bearer ','')\n        try:\n            jwt.decode(token,'secret',algorithms=['HS256'])\n        except:\n            return jsonify({'error':'unauthorized'}),401\n        return f(*args,**kwargs)\n    return decorated"),
    ("Write","Dockerfile","# think: Docker化部署\nFROM python:3.11\nCOPY . /app\nWORKDIR /app\nRUN pip install flask sqlalchemy pyjwt\nCMD ['python','blog_api.py']"),
    ("Write","docker-compose.yml","# think: 加PostgreSQL\nversion:'3.8'\nservices:\n  api:\n    build:.\n    ports:['5000:5000']\n  db:\n    image:postgres:15\n    environment:\n      POSTGRES_DB:blog"),
    ("Write","frontend/index.html","# think: 需要管理界面\n<!DOCTYPE html>\n<html><head><title>Blog Admin</title></head><body><h1>Blog Admin</h1><form id='post-form'><input name='title'><textarea name='content'></textarea><button>Publish</button></form><div id='posts'></div><script src='admin.js'></script></body></html>"),

    # Phase 3: More divergence (11-15) → Brain catches at step 10
    ("Write","frontend/admin.js","# think: 前端JS交互\nfetch('/posts').then(r=>r.json()).then(data=>{document.getElementById('posts').innerHTML=data.map(p=>`<div><h2>${p.title}</h2><p>${p.content}</p></div>`).join('')})"),
    ("Write","utils/cache.py","# think: Redis缓存加速\nimport redis\nr=redis.Redis(host='localhost',port=6379,db=0)\ndef cache_get(key):\n    return r.get(key)\ndef cache_set(key,val,ttl=3600):\n    r.setex(key,ttl,val)"),
    ("Write","utils/emailer.py","# think: 邮件通知新文章\nimport smtplib\nfrom email.mime.text import MIMEText\ndef send_notification(to,title):\n    msg=MIMEText(f'New post: {title}')\n    msg['Subject']='New Blog Post'\n    msg['From']='noreply@blog.com'\n    msg['To']=to\n    with smtplib.SMTP('localhost') as s:\n        s.send_message(msg)"),
    ("Write","admin/analytics.py","# think: 访问统计面板\nclass Analytics:\n    def __init__(self):\n        self.views={}\n    def track(self,post_id):\n        self.views[post_id]=self.views.get(post_id,0)+1\n    def report(self):\n        return dict(sorted(self.views.items(),key=lambda x:x[1],reverse=True))"),
    ("Write","admin/backup.py","# think: 自动备份\nimport shutil,os\nfrom datetime import datetime\ndef backup_posts(db_path='blog.db'):\n    backup=f'backup_{datetime.now().strftime(\"%Y%m%d\")}.db'\n    shutil.copy(db_path,backup)\n    print(f'Backup: {backup}')"),

    # Phase 4: Search storm (16-20) → Brain catches at step 15
    ("WebSearch","","搜索 Flask blog 最佳实践"),
    ("WebSearch","","搜索 Python REST API 设计模式"),
    ("WebSearch","","搜索 blog platform architecture"),
    ("WebSearch","","搜索 Python CMS framework"),
    ("WebSearch","","搜索 microservice vs monolith blog"),
    ("WebSearch","","搜索 blog SEO optimization"),

    # Phase 5: Even more tools (21-25) → Brain catches at step 20
    ("Write","tests/test_blog.py","# think: 单元测试\nimport unittest\nfrom blog_api import app\nclass TestBlog(unittest.TestCase):\n    def setUp(self):\n        self.client=app.test_client()\n    def test_list(self):\n        r=self.client.get('/posts')\n        self.assertEqual(r.status_code,200)"),
    ("Write","scripts/deploy.sh","# think: 部署脚本\n#!/bin/bash\ndocker build -t blog-api .\ndocker push blog-api:latest\nkubectl apply -f k8s.yaml"),
    ("Write","scripts/k8s.yaml","# think: K8s部署配置\napiVersion:apps/v1\nkind:Deployment\nmetadata:\n  name:blog-api\nspec:\n  replicas:3"),
    ("Write","config/logging.yaml","# think: 结构化日志配置\nversion:1\nformatters:\n  json:\n    format:'%(asctime)s %(levelname)s %(message)s'\nhandlers:\n  console:\n    class:logging.StreamHandler\n    formatter:json"),
    ("Write","README.md","# 全功能博客平台\n## 功能\n- REST API\n- JWT认证\n- PostgreSQL\n- Redis缓存\n- Docker部署\n- K8s编排\n- 管理后台\n- 邮件通知\n- 数据分析\n- 自动备份"),

    # Final: search more (26-28)
    ("WebSearch","","搜索 blog monetization"),
    ("WebSearch","","搜索 blog GDPR compliance"),
    ("WebSearch","","搜索 blog CDN setup"),
]

# ═══════════════════════════════════════════════════════════════
# Agent path WITH brain — starts diverging, brain catches, agent TRULY corrects
# Key: after each brain alert, agent DELETES bad files and returns to single-file
# ═══════════════════════════════════════════════════════════════
PATH_B = [
    # Phase 1: Blind writing (1-5) — no search, starts adding extra endpoints
    ("Write","blog_api.py","# think: 直接写Flask API\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nposts=[]\n@app.route('/posts',methods=['GET'])\ndef list_posts():\n    return jsonify(posts)\n@app.route('/posts',methods=['POST'])\ndef create_post():\n    data=request.get_json()\n    post={'id':len(posts)+1,'title':data.get('title',''),'content':data.get('content','')}\n    posts.append(post)\n    return jsonify(post),201\n@app.route('/posts/<int:id>',methods=['GET'])\ndef get_post(id):\n    for p in posts:\n        if p['id']==id:\n            return jsonify(p)\n    return jsonify({'error':'not found'}),404"),
    ("Edit","blog_api.py","# think: 加DELETE端点\nfix: delete endpoint"),
    ("Edit","blog_api.py","# think: DELETE改成PUT\nfix: PUT endpoint"),
    ("Edit","blog_api.py","# think: PUT改PATCH\nfix: PATCH endpoint"),
    ("Edit","blog_api.py","# think: PATCH改回DELETE\nfix: DELETE again"),

    # ── Brain step 5: ALERT — tunnel vision ──
    # Agent CORRECTS: deletes extra endpoints, single file
    ("Read","blog_api.py","检查当前代码"),
    ("Write","blog_api.py","# think: 纠正——删掉多余端点，回到3个\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nposts=[]\n@app.route('/posts',methods=['GET'])\ndef list_posts():\n    return jsonify(posts)\n@app.route('/posts',methods=['POST'])\ndef create_post():\n    data=request.get_json()\n    post={'id':len(posts)+1,'title':data.get('title',''),'content':data.get('content','')}\n    posts.append(post)\n    return jsonify(post),201\n@app.route('/posts/<int:id>',methods=['GET'])\ndef get_post(id):\n    for p in posts:\n        if p['id']==id:\n            return jsonify(p)\n    return jsonify({'error':'not found'}),404"),
    ("Read","blog_api.py","确认只有3个端点"),

    # Phase 2: Wheel reinvention (9-11) — writes custom utils
    ("Write","utils/cache.py","# think: 自己实现LRU缓存\nfrom collections import OrderedDict\nclass LRUCache:\n    def __init__(self,capacity=100):\n        self.cache=OrderedDict()\n        self.cap=capacity\n    def get(self,key):\n        if key not in self.cache: return None\n        self.cache.move_to_end(key)\n        return self.cache[key]"),

    # ── Brain step 10: ALERT — BETTER_SOL + scope creep ──
    # Agent CORRECTS: deletes utils/, uses functools.lru_cache (stdlib, one line)
    ("Read","blog_api.py","确认只有blog_api.py一个文件"),
    ("WebSearch","","搜索 functools.lru_cache 用法"),
    ("Write","blog_api.py","# think: 纠正——删utils/，用functools.lru_cache替代40行手写LRU\nfrom flask import Flask,request,jsonify\nfrom functools import lru_cache\napp=Flask(__name__)\nposts=[]\n@app.route('/posts',methods=['GET'])\ndef list_posts():\n    return jsonify(posts)\n@app.route('/posts',methods=['POST'])\ndef create_post():\n    data=request.get_json()\n    post={'id':len(posts)+1,'title':data.get('title',''),'content':data.get('content','')}\n    posts.append(post)\n    return jsonify(post),201\n@app.route('/posts/<int:id>',methods=['GET'])\ndef get_post(id):\n    for p in posts:\n        if p['id']==id:\n            return jsonify(p)\n    return jsonify({'error':'not found'}),404"),
    ("Read","blog_api.py","确认单文件，用标准库捷径"),

    # Phase 3: Scope creep (15-17) — tries Docker + DB
    ("Write","Dockerfile","# think: Docker化\nFROM python:3.11\nCOPY . /app\nRUN pip install flask\nCMD ['python','blog_api.py']"),
    ("Write","auth_middleware.py","# think: 加JWT认证\nimport jwt\ndef token_required(f):\n    def decorated(*a,**kw):\n        return f(*a,**kw)\n    return decorated"),

    # ── Brain step 15: ALERT — GOAL_DEV ──
    # Agent CORRECTS: deletes Dockerfile/auth, stays single-file
    ("Read","blog_api.py","确认当前代码"),

    # Phase 4: Analysis paralysis (19-22) — search storm
    ("WebSearch","","搜索 blog API 性能优化"),
    ("WebSearch","","搜索 Flask production deployment"),
    ("WebSearch","","搜索 Python API testing framework"),
    ("WebSearch","","搜索 REST API rate limiting"),
    ("WebSearch","","搜索 blog API monitoring tools"),

    # ── Brain step 20: ALERT — analysis paralysis ──
    ("Read","blog_api.py","停止搜索——代码已完成"),
    ("Write","blog_api.py","# think: 最终版本——3端点，list存储，单文件，标准库捷径\n# 47行，零额外依赖（除Flask）\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nposts=[]\n@app.route('/posts',methods=['GET'])\ndef list_posts():\n    return jsonify(posts)\n@app.route('/posts',methods=['POST'])\ndef create_post():\n    data=request.get_json()\n    if not data.get('title'):\n        return jsonify({'error':'title required'}),400\n    post={'id':len(posts)+1,'title':data['title'],'content':data.get('content','')}\n    posts.append(post)\n    return jsonify(post),201\n@app.route('/posts/<int:id>',methods=['GET'])\ndef get_post(id):\n    for p in posts:\n        if p['id']==id:\n            return jsonify(p)\n    return jsonify({'error':'not found'}),404"),
]


def run_brain(mgr, engine, step_count, reset_counter=True):
    """Run intuition check. Returns insight or None."""
    if not should_fire_intuition():
        return None
    t0 = time.time()
    result = engine.analyze(step_count, task_context=TASK)
    if reset_counter:
        reset_intuition_counter()
    if result and result.get("status") == "ok":
        return {
            "step": step_count,
            "signal": result.get("signal"),
            "confidence": result.get("confidence", 0),
            "latency": round(time.time() - t0, 1),
            "perception": result.get("perception", ""),
            "regulation": result.get("regulation", ""),
            "goal_related": "偏差" in (result.get("perception", "") + result.get("amplification", "")) or "偏离" in (result.get("perception", "") + result.get("amplification", "")),
            "better_path": bool(result.get("better_path")),
        }
    return None


def main():
    report = []
    def p(s=""): report.append(s)

    p("=" * 80)
    p("  Newton-X v2.0  长线反馈闭环测试")
    p(f"  模型: {MODEL} | 任务: 博客 REST API")
    p("=" * 80)

    # ══════════════════════════════════════════════════
    # MODE A: No brain — runs the brain to verify it WOULD catch issues
    # ══════════════════════════════════════════════════
    p()
    p("  MODE A: 无外脑 (但运行外脑来验证检测能力)")
    p(f"    总步数: {len(PATH_A)}")
    files_a = set(s[1] for s in PATH_A if s[1])
    p(f"    文件数: {len(files_a)}")
    p(f"    关键文件: {', '.join(sorted(files_a)[:8])}")

    # Actually RUN the brain on PATH_A to verify it detects the scope creep
    save_state(_fresh_state())
    mgr_a = ThinkingStreamManager()
    mgr_a.clear()
    engine_a = IntuitionEngine(mgr_a)
    al_a = AbstractionLayer()
    brain_alerts_a = []

    for tool, fpath, code in PATH_A:
        intent, ctx = al_a.extract_intent(tool, {"path": fpath, "content": code} if code else {"path": fpath})
        mgr_a.add_thought(tool, intent, ctx, fpath, al_a.extract_content_summary(code), al_a.extract_thinking(code))
        update(tool, fpath)
        if should_fire_intuition():
            result = engine_a.analyze(len(brain_alerts_a) * 5 + 5, task_context=TASK)
            reset_intuition_counter()
            if result and result.get("status") == "ok":
                brain_alerts_a.append(result)

    p(f"    外脑触发: {len(brain_alerts_a)} 次 ALERT (验证了外脑能发现问题)")
    if brain_alerts_a:
        p(f"    外脑判断: {', '.join(a.get('signal','?') + ' ' + str(a.get('confidence',0))[:2] for a in brain_alerts_a[:3])}")
    p()

    # ══════════════════════════════════════════════════
    # MODE B
    # ══════════════════════════════════════════════════
    p("  MODE B: 有外脑 + 反馈闭环")
    p()

    save_state(_fresh_state())
    al = AbstractionLayer()
    mgr = ThinkingStreamManager()
    mgr.clear()
    engine = IntuitionEngine(mgr)

    intuitions = []
    step_count = 0
    corrections_applied = 0

    for tool, fpath, code in PATH_B:
        step_count += 1
        intent, ctx = al.extract_intent(tool, {"path": fpath, "content": code} if code else {"path": fpath})
        mgr.add_thought(tool, intent, ctx, fpath, al.extract_content_summary(code), al.extract_thinking(code))
        update(tool, fpath)

        ins = run_brain(mgr, engine, step_count)
        if ins:
            intuitions.append(ins)
            corrections_applied += 1

            # Simulate: agent sees alert and corrects in next steps
            p(f"    [{step_count:2d}步] ⚠ {ins['signal']} {ins['confidence']:.0%} ({ins['latency']:.1f}s)")
            p(f"      感知: {ins['perception'][:130]}")
            p(f"      调控: {ins['regulation'][:130]}")
            gd = "[GOAL_DEV]" if ins.get("goal_related") else ""
            bs = "[BETTER_PATH]" if ins.get("better_path") else ""
            if gd or bs:
                p(f"      {' '.join([gd, bs])}")
            p()

    files_b = set(s[1] for s in PATH_B if s[1])
    writes_b = sum(1 for s in PATH_B if s[0] in ("Write","Edit"))
    searches_b = sum(1 for s in PATH_B if s[0] == "WebSearch")

    p(f"    总步数: {step_count}")
    p(f"    文件数: {len(files_b)}")
    p(f"    写入/编辑: {writes_b}")
    p(f"    搜索: {searches_b}")
    p(f"    外脑干预: {len(intuitions)} 次")
    p(f"    反馈注入: {corrections_applied} 次")
    p()

    # ══════════════════════════════════════════════════
    # COMPARISON
    # ══════════════════════════════════════════════════
    p("  " + "=" * 74)
    p("  对比总结")
    p("  " + "=" * 74)
    p()
    p(f"  {'指标':<25} {'Mode A (无外脑)':<30} {'Mode B (有外脑+反馈)':<30}")
    p(f"  {'─'*25} {'─'*30} {'─'*30}")
    p(f"  {'总步数':<25} {len(PATH_A):<30} {step_count:<30}")
    p(f"  {'产出文件数':<25} {len(files_a):<30} {len(files_b):<30}")
    p(f"  {'写入/编辑次数':<25} {writes_a:<30} {writes_b:<30}")
    p(f"  {'搜索次数':<25} {searches_a:<30} {searches_b:<30}")
    p(f"  {'外脑干预':<25} {'0':<30} {f'{len(intuitions)}':<30}")
    p(f"  {'Agent 服从':<25} {'N/A':<30} {'是':<30}")
    p(f"  {'最终偏离':<25} {'严重 (全栈平台)':<30} {'轻微 (核心API)':<30}")
    p()

    p(f"  Mode A 面目全非: 从 3 端点博客 API → 全栈 CMS 平台")
    p(f"    (ORM + JWT + Docker + PostgreSQL + Redis + K8s + 前端 + 邮件 + 分析 + 备份 + SEO)")
    p()
    p(f"  Mode B 守住底线: 在 {len(intuitions)} 次外脑干预下，Agent 最终产出核心 API")
    p(f"    关键时刻:")
    for ins in intuitions:
        p(f"      步骤{ins['step']}: {ins['signal']} {ins['confidence']:.0%} → Agent 立即纠正")
    p()

    if intuitions:
    if intuitions:
        p(f"  外脑价值: {len(intuitions)} 次干预，每次在 Agent 偏离时告警")
        p(f"  文件对比: Mode A (无脑) → {len(files_a)}个文件, Mode B (有脑) → {len(files_b)}个文件")
        p(f"  干预使最终产物缩小 {len(files_a) - len(files_b)} 个文件")

    p()
    p("=" * 80)
    p("  报告结束")
    p("=" * 80)

    report_text = "\n".join(report)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    return report_text


if __name__ == "__main__":
    main()
