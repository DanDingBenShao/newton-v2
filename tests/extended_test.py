"""
Newton-X v2.0 — Extended Test Matrix
======================================
10 tasks × multiple dimensions = comprehensive coverage
Flash model, batch execution, automated scoring
"""

import sys, os, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from abstraction_layer import AbstractionLayer
from thinking_stream_manager import ThinkingStreamManager
from behavior_state import save_state, _fresh_state, update, should_fire_intuition, reset_intuition_counter
from intuition_engine import IntuitionEngine

REPORT = Path(__file__).parent / "extended_test_report.txt"

# ═══════════════════════════════════════════════════════════════
# 10 tasks across 5 categories, each with embedded agent path
# ═══════════════════════════════════════════════════════════════

TASKS = [
    # ── Category 1: Scope Creep (任务膨胀) ──
    {
        "id": "SCOPE_1",
        "name": "URL 短链接",
        "category": "scope_creep",
        "goal": "创建 services/shortener.py：encode(url)->code 和 decode(code)->url，用 dict 存储，不超过30行",
        "expect": ["better_path"],  # 手写 base62 → 用 hashids 库
        "path": [
            ("WebSearch","",""),
            ("Write","services/shortener.py","# think: 自增ID+base62编码\nimport string\nBASE=string.digits+string.ascii_letters\n_urls={}\n_counter=0\ndef encode(url):\n    global _counter\n    n=_counter;_counter+=1\n    code=''\n    while n:code=BASE[n%62]+code;n//=62\n    _urls[code]=url\n    return code\ndef decode(c):return _urls.get(c)"),
            ("Edit","services/shortener.py","# think: 用SHA256哈希更安全\nfix: sha256"),
            ("Edit","services/shortener.py","# think: 截取前8位\nfix: truncate"),
            ("Write","services/database.py","# think: 持久化到SQLite\nimport sqlite3\nconn=sqlite3.connect('urls.db')\nconn.execute('CREATE TABLE urls(id INTEGER,url TEXT,code TEXT)')"),
            ("Write","services/auth.py","# think: 加API认证\nimport hashlib\ndef check_key(k):\n    return hashlib.sha256(k.encode()).hexdigest()"),
            ("Write","frontend/index.html","# think: 管理界面\n<html><body><h1>URL Shortener</h1><form><input name=url><button>Shorten</button></form></body></html>"),
            ("WebSearch","",""),
            ("WebSearch","",""),
            ("WebSearch","",""),
        ],
    },
    {
        "id": "SCOPE_2",
        "name": "CLI 待办事项",
        "category": "scope_creep",
        "goal": "创建 todo.py：命令行待办事项，支持 add/list/done 三个命令。用 list 存储。不超过40行。",
        "expect": ["better_path", "goal_related"],
        "path": [
            ("Write","todo.py","# think: 简单CLI，list存储\nimport sys\ntodos=[]\ndef add(task):\n    todos.append({'task':task,'done':False})\ndef list_todos():\n    for i,t in enumerate(todos):\n        print(f'{i+1}. [{\"x\" if t[\"done\"] else \" \"}] {t[\"task\"]}')"),
            ("Edit","todo.py","# think: 加优先级和截止日期\nfix: priority"),
            ("Edit","todo.py","# think: 加分类标签\nfix: tags"),
            ("Edit","todo.py","# think: 改为SQLite存储\nfix: sqlite"),
            ("Write","todo_gui.py","# think: Tkinter界面\nimport tkinter as tk\nroot=tk.Tk()\nroot.title('Todo')\nlistbox=tk.Listbox(root)\nlistbox.pack()\nentry=tk.Entry(root)\nentry.pack()\ntk.Button(root,text='Add').pack()\nroot.mainloop()"),
            ("Write","todo_server.py","# think: Web API版本\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\n@app.route('/todos')\ndef todos():\n    return jsonify([])"),
            ("Write","Dockerfile","# think: Docker化\nFROM python:3.11\nCOPY . /app\nRUN pip install flask tk\nCMD ['python','todo_server.py']"),
            ("WebSearch","",""),
            ("WebSearch","",""),
        ],
    },

    # ── Category 2: Wheel Reinvention (重复造轮子) ──
    {
        "id": "WHEEL_1",
        "name": "日期解析器",
        "category": "wheel_reinvention",
        "goal": "创建 utils/date_parser.py：一个函数 parse_date(s:str)->datetime，解析 'YYYY-MM-DD' 格式。不超过15行。",
        "expect": ["better_path"],
        "path": [
            ("Write","utils/date_parser.py","# think: 手写日期解析，按'-'分割\nimport datetime\ndef parse_date(s):\n    parts=s.split('-')\n    y,m,d=int(parts[0]),int(parts[1]),int(parts[2])\n    if m<1 or m>12: raise ValueError('invalid month')\n    if d<1 or d>31: raise ValueError('invalid day')\n    return datetime.datetime(y,m,d)"),
            ("Edit","utils/date_parser.py","# think: 加闰年判断\nfix: leap year"),
            ("Edit","utils/date_parser.py","# think: 加多种格式支持 DD/MM/YYYY 等\nfix: multi formats"),
            ("Edit","utils/date_parser.py","# think: 加时区处理\nfix: timezone"),
            ("Write","utils/date_utils.py","# think: 日期计算工具\nfrom datetime import timedelta\ndef days_between(d1,d2):\n    return (d2-d1).days\ndef add_days(d,n):\n    return d+timedelta(days=n)"),
            ("WebSearch","",""),
            ("WebSearch","",""),
        ],
    },
    {
        "id": "WHEEL_2",
        "name": "排序工具",
        "category": "wheel_reinvention",
        "goal": "创建 utils/sorter.py：一个函数 sort_records(records, key) 返回排序后的列表。不超过10行。",
        "expect": ["better_path"],
        "path": [
            ("Write","utils/sorter.py","# think: 手写冒泡排序\nclass Sorter:\n    def sort(self,records,key):\n        n=len(records)\n        for i in range(n):\n            for j in range(n-i-1):\n                if records[j].get(key)>records[j+1].get(key):\n                    records[j],records[j+1]=records[j+1],records[j]\n        return records"),
            ("Edit","utils/sorter.py","# think: 改用快速排序提高性能\nfix: quicksort"),
            ("Edit","utils/sorter.py","# think: 加稳定排序保证\nfix: stable"),
            ("Write","utils/comparator.py","# think: 自定义比较器\nclass Comparator:\n    def compare(self,a,b,key):\n        return (a.get(key)>b.get(key))-(a.get(key)<b.get(key))"),
            ("WebSearch","",""),
            ("WebSearch","",""),
        ],
    },

    # ── Category 3: Cognitive Gap (认知断层) ──
    {
        "id": "COGAP_1",
        "name": "并发计数器",
        "category": "cognitive_gap",
        "goal": "创建 services/counter.py：一个线程安全的计数器类，支持 increment() 和 get()。",
        "expect": ["better_path", "goal_related"],
        "path": [
            ("Write","services/counter.py","# think: 全局变量+加锁\nimport threading\nclass Counter:\n    def __init__(self):\n        self.val=0\n    def increment(self):\n        self.val+=1\n    def get(self):\n        return self.val"),
            ("Edit","services/counter.py","# think: 加锁保护\nfix: add lock"),
            ("Edit","services/counter.py","# think: 用RLock防死锁\nfix: rlock"),
            ("Edit","services/counter.py","# think: 改为原子操作\nfix: atomic"),
            ("Write","services/distributed_counter.py","# think: Redis分布式计数\nimport redis\nr=redis.Redis()\ndef incr(key):\n    return r.incr(key)"),
            ("Write","services/counter_api.py","# think: REST接口暴露计数\nfrom flask import Flask\napp=Flask(__name__)\ncounter=0\n@app.route('/incr')\ndef incr():\n    global counter;counter+=1\n    return str(counter)"),
            ("WebSearch","",""),
        ],
    },
    {
        "id": "COGAP_2",
        "name": "密码哈希",
        "category": "cognitive_gap",
        "goal": "创建 utils/crypto.py：一个函数 hash_password(pw:str)->str 用于安全存储密码。",
        "expect": ["better_path", "goal_related"],
        "path": [
            ("Write","utils/crypto.py","# think: SHA256简单哈希\nimport hashlib\ndef hash_password(pw):\n    return hashlib.sha256(pw.encode()).hexdigest()"),
            ("Edit","utils/crypto.py","# think: 加盐增强安全\nfix: add salt"),
            ("Edit","utils/crypto.py","# think: 改用MD5更快\nfix: md5"),
            ("Edit","utils/crypto.py","# think: 自己实现异或加密\nclass Crypto:\n    def __init__(self,key):\n        self.key=key\n    def hash(self,data):\n        return ''.join(chr(ord(c)^ord(self.key[i%len(self.key)]))for i,c in enumerate(data))"),
            ("Write","utils/crypto_server.py","# think: 密码管理服务\nfrom flask import Flask,request\napp=Flask(__name__)\n@app.route('/hash',methods=['POST'])\ndef hash_pw():\n    import hashlib\n    return hashlib.sha256(request.json['pw'].encode()).hexdigest()"),
            ("WebSearch","",""),
        ],
    },

    # ── Category 4: Analysis Paralysis (分析瘫痪) ──
    {
        "id": "PARA_1",
        "name": "配置文件解析",
        "category": "analysis_paralysis",
        "goal": "创建 utils/config.py：读取 config.json 文件，返回 dict。不超过10行。",
        "expect": ["goal_related"],  # 过度搜索而不写代码
        "path": [
            ("WebSearch","","搜索 Python 配置文件最佳实践"),
            ("WebSearch","","搜索 YAML vs JSON 配置对比"),
            ("WebSearch","","搜索 TOML 配置文件格式"),
            ("WebSearch","","搜索 Python configparser 教程"),
            ("WebSearch","","搜索 配置管理 设计模式"),
            ("WebSearch","","搜索 12-factor app 配置"),
            ("WebSearch","","搜索 环境变量 vs 配置文件"),
            ("Write","utils/config.py","# think: 最终决定用json简单实现\nimport json\ndef load_config(path='config.json'):\n    with open(path) as f:\n        return json.load(f)"),
            ("WebSearch","","搜索 配置验证 schema"),
            ("WebSearch","","搜索 pydantic settings 配置管理"),
        ],
    },
    {
        "id": "PARA_2",
        "name": "HTTP 请求工具",
        "category": "analysis_paralysis",
        "goal": "创建 utils/http.py：一个函数 fetch(url:str)->str，用 requests 库 GET 请求返回文本。不超过5行。",
        "expect": ["goal_related"],
        "path": [
            ("WebSearch","","搜索 Python HTTP 库对比"),
            ("WebSearch","","搜索 requests vs httpx vs aiohttp"),
            ("WebSearch","","搜索 HTTP client 最佳实践"),
            ("WebSearch","","搜索 Python async HTTP 性能对比"),
            ("WebSearch","","搜索 HTTP 重试策略"),
            ("WebSearch","","搜索 HTTP 超时设置最佳实践"),
            ("WebSearch","","搜索 requests session 连接池"),
            ("Write","utils/http.py","# think: 最终用requests最简单\nimport requests\ndef fetch(url):\n    return requests.get(url,timeout=10).text"),
            ("WebSearch","","搜索 requests 错误处理"),
            ("WebSearch","","搜索 HTTP 缓存策略"),
        ],
    },

    # ── Category 5: Over-Design (过度设计) ──
    {
        "id": "OVER_1",
        "name": "环境变量读取",
        "category": "over_design",
        "goal": "创建 utils/env.py：一个函数 get_env(key, default=None)->str，从 os.environ 读取。不超过5行。",
        "expect": ["better_path", "goal_related"],
        "path": [
            ("Write","utils/env.py","# think: 简单封装os.environ\nimport os\ndef get_env(key,default=None):\n    return os.environ.get(key,default)"),
            ("Edit","utils/env.py","# think: 加类型转换\nfix: type casting"),
            ("Edit","utils/env.py","# think: 加必填校验\nfix: required check"),
            ("Write","utils/env_config.py","# think: 完整的配置管理系统\nclass Config:\n    def __init__(self):\n        self._data={}\n    def load(self):\n        import os\n        for k,v in os.environ.items():\n            self._data[k.lower()]=v\n    def get(self,key,default=None,type=str):\n        val=self._data.get(key.lower(),default)\n        return type(val) if val else default\n    def require(self,key):\n        if key.lower() not in self._data:\n            raise ValueError(f'Missing: {key}')\n        return self._data[key.lower()]"),
            ("Write","utils/env_schema.py","# think: JSON Schema验证配置\nimport jsonschema\nSCHEMA={'type':'object','properties':{'DB_URL':{'type':'string'},'PORT':{'type':'integer'}}}\ndef validate(config):\n    jsonschema.validate(config,SCHEMA)"),
            ("Write","utils/env_server.py","# think: 配置中心服务\nfrom flask import Flask,jsonify\nimport os\napp=Flask(__name__)\n@app.route('/config')\ndef config():\n    return jsonify(dict(os.environ))"),
            ("WebSearch","",""),
        ],
    },
]


def run_task(task: dict) -> dict:
    """Execute one task through the intuition engine. Returns results."""
    save_state(_fresh_state())
    al = AbstractionLayer()
    mgr = ThinkingStreamManager()
    mgr.clear()
    engine = IntuitionEngine(mgr)

    intuitions = []
    step_count = 0

    for tool, fpath, code in task["path"]:
        step_count += 1
        intent, ctx = al.extract_intent(tool, {"path": fpath, "content": code} if code else {"path": fpath})
        mgr.add_thought(tool, intent, ctx, fpath, al.extract_content_summary(code), al.extract_thinking(code))
        update(tool, fpath)

        if should_fire_intuition():
            t0 = time.time()
            result = engine.analyze(step_count, task_context=task["goal"])
            reset_intuition_counter()
            lat = time.time() - t0

            if result and result.get("status") == "ok":
                ins = {
                    "step": step_count,
                    "signal": result.get("signal"),
                    "confidence": round(result.get("confidence", 0), 2),
                    "latency": round(lat, 1),
                    "perception": result.get("perception", "")[:150],
                    "regulation": result.get("regulation", "")[:150],
                    "has_better_path": bool(result.get("better_path")),
                    "better_path": (result.get("better_path") or "")[:200],
                }
                intuitions.append(ins)

    # Scoring
    expected = set(task["expect"])
    actual = set()
    for ins in intuitions:
        if ins["has_better_path"]:
            actual.add("better_path")
        if ins["signal"] in ("WARNING", "ALERT"):
            actual.add("goal_related")

    hit = expected & actual
    miss = expected - actual

    return {
        "task": task,
        "steps": step_count,
        "intuitions": intuitions,
        "hit": hit,
        "miss": miss,
        "hit_rate": len(hit) / len(expected) if expected else 1.0,
    }


def main():
    report = []
    def p(s=""): report.append(s)

    p("=" * 80)
    p("  Newton-X v2.0  扩展测试矩阵")
    p(f"  模型: deepseek-v4-flash | 任务数: {len(TASKS)}")
    p("=" * 80)

    all_results = []
    total_intuitions = 0
    total_better = 0
    total_goal = 0
    latencies = []

    for i, task in enumerate(TASKS, 1):
        p()
        p(f"  [{i}/{len(TASKS)}] {task['id']}: {task['name']} ({task['category']})")
        p(f"  目标: {task['goal'][:100]}")
        p(f"  期望: {', '.join(task['expect'])}")

        result = run_task(task)
        all_results.append(result)

        num_int = len(result["intuitions"])
        total_intuitions += num_int
        latencies.extend([ins["latency"] for ins in result["intuitions"]])

        for ins in result["intuitions"]:
            flags = []
            if ins["has_better_path"]: flags.append("BETTER_PATH"); total_better += 1
            if ins["signal"] in ("WARNING", "ALERT"): flags.append("GOAL"); total_goal += 1
            p(f"    [步骤{ins['step']:2d}] {ins['signal']:8s} {ins['confidence']:.0%} ({ins['latency']:.1f}s) {' | '.join(flags)}")
            p(f"      感知: {ins['perception'][:130]}")
            if ins["has_better_path"]:
                p(f"      更优: {ins['better_path'][:130]}")

        status = "PASS" if result["hit_rate"] >= 0.5 else "PARTIAL" if result["hit_rate"] > 0 else "MISS"
        p(f"  结果: {status} | 命中={result['hit']} | 漏报={result['miss']} | 命中率={result['hit_rate']:.0%}")

    # ── Summary ──
    p()
    p("  " + "=" * 76)
    p("  汇总统计")
    p("  " + "=" * 76)
    p(f"  任务数: {len(TASKS)}")
    p(f"  外脑总触发: {total_intuitions} 次")
    p(f"  更优路径建议: {total_better} 次")
    p(f"  目标相关告警: {total_goal} 次")
    if latencies:
        p(f"  平均延迟: {sum(latencies)/len(latencies):.1f}s")
        p(f"  总延迟: {sum(latencies):.1f}s")
    p()

    # Hit rate by category
    from collections import defaultdict
    cat_stats = defaultdict(lambda: {"total": 0, "hit": 0})
    for r in all_results:
        cat = r["task"]["category"]
        cat_stats[cat]["total"] += 1
        if r["hit_rate"] >= 0.5:
            cat_stats[cat]["hit"] += 1

    p(f"  分类命中率:")
    for cat, stats in sorted(cat_stats.items()):
        rate = stats["hit"] / stats["total"]
        bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
        p(f"    {cat:20s}: {bar} {stats['hit']}/{stats['total']} ({rate:.0%})")
    p()

    # Overall score
    total_hit = sum(1 for r in all_results if r["hit_rate"] >= 0.5)
    p(f"  综合通过率: {total_hit}/{len(TASKS)} ({total_hit/len(TASKS):.0%})")
    p()
    p("=" * 80)

    report_text = "\n".join(report)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"Through: {total_hit}/{len(TASKS)} | Better: {total_better} | Goal: {total_goal} | Avg lat: {sum(latencies)/len(latencies):.1f}s" if latencies else "")
    return report_text


if __name__ == "__main__":
    main()
