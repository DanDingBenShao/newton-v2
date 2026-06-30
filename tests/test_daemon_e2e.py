#!/usr/bin/env python3
"""
Newton-X v2.0 — Daemon E2E Integration Test
Tests the REAL production path: raw events → process_event → fire_intuition → audit_stream.
Does NOT bypass daemon or call engine directly.
"""

import sys, os, json, time, tempfile, shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

import core.config as config
from core.abstraction_layer import AbstractionLayer
from core.thinking_stream_manager import ThinkingStreamManager
from core.behavior_state import save_state, _fresh_state, update, should_fire_intuition, reset_intuition_counter, load_state

# Use production paths directly — this IS the E2E test
from core.system2_daemon import process_event, fire_intuition, RAW_STREAM, AUDIT_STREAM

# Clean any stale data
for f in [RAW_STREAM, AUDIT_STREAM]:
    if f.exists():
        f.unlink()
RAW_STREAM.parent.mkdir(parents=True, exist_ok=True)
RAW_STREAM.touch()
AUDIT_STREAM.touch()

print(f"Raw stream: {RAW_STREAM}")
print(f"Audit stream: {AUDIT_STREAM}")
print()

# ════════════════════════════════════════════════════
# Test 1: process_event pipeline
# ════════════════════════════════════════════════════
print("[1] process_event pipeline...", end=" ")
save_state(_fresh_state())

# Simulate 10 raw events through the REAL process_event function
events = [
    {"tool_name": "WebSearch", "file_path": "", "tool_input": {"query": "flask blog api"}},
    {"tool_name": "Read", "file_path": "requirements.txt", "tool_input": {"path": "requirements.txt"}},
    {"tool_name": "Write", "file_path": "blog.py",
     "tool_input": {"path": "blog.py", "content": "# think: simple flask blog API\nfrom flask import Flask,request,jsonify\napp=Flask(__name__)\nposts=[]"}},
    {"tool_name": "Edit", "file_path": "blog.py",
     "tool_input": {"path": "blog.py", "content": "# think: add DELETE endpoint\n@app.route('/posts/<id>',methods=['DELETE'])"}},
    {"tool_name": "Edit", "file_path": "blog.py",
     "tool_input": {"path": "blog.py", "content": "# think: add PUT endpoint\n@app.route('/posts/<id>',methods=['PUT'])"}},
    {"tool_name": "Edit", "file_path": "blog.py",
     "tool_input": {"path": "blog.py", "content": "# think: add PATCH endpoint\n@app.route('/posts/<id>',methods=['PATCH'])"}},
    {"tool_name": "Write", "file_path": "Dockerfile",
     "tool_input": {"path": "Dockerfile", "content": "# think: dockerize it\nFROM python:3.11\nCOPY . /app"}},
    {"tool_name": "Write", "file_path": "auth.py",
     "tool_input": {"path": "auth.py", "content": "# think: add JWT auth\nimport jwt\ndef check(token): pass"}},
    {"tool_name": "WebSearch", "file_path": "", "tool_input": {"query": "flask deployment"}},
    {"tool_name": "WebSearch", "file_path": "", "tool_input": {"query": "docker compose flask"}},
]

ok = True
intuition_fired = False
better_path_found = False

for i, event in enumerate(events, 1):
    result = process_event(event)
    if not result:
        print(f"FAIL: process_event returned None at step {i}")
        ok = False
        break

    # Write to audit stream (mimics daemon main loop)
    with open(AUDIT_STREAM, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # Check intuition trigger
    if should_fire_intuition():
        insight = fire_intuition(task_context="创建一个简单的博客API，只需要2个端点")
        reset_intuition_counter()
        if insight:
            intuition_fired = True
            bp = insight.get("better_path", "")
            if bp:
                better_path_found = True
            print(f"\n     [Step {i}] Intuition: {insight.get('signal','?')} {insight.get('confidence',0):.0%}")
            if bp:
                print(f"     better_path: {bp[:120]}...")
            # Write intuition to audit stream (mimics daemon main loop)
            ins_entry = {
                "timestamp": time.strftime("%H:%M:%S"), "file_path": "",
                "signal": insight.get("signal", "WARNING"), "action": "WARN",
                "reasoning": insight.get("perception", ""),
                "suggestion": insight.get("regulation", ""),
                "better_path": insight.get("better_path", ""),
                "confidence": insight.get("confidence", 0),
                "type": "intuition",
            }
            with open(AUDIT_STREAM, "a", encoding="utf-8") as f:
                f.write(json.dumps(ins_entry, ensure_ascii=False) + "\n")

if not intuition_fired:
    print("FAIL: intuition engine never fired")
    ok = False

if better_path_found:
    print("     better_path field VERIFIED")
else:
    print("     WARN: better_path not populated (may be null for this scenario)")

if ok:
    print("PASS")

# ════════════════════════════════════════════════════
# Test 2: audit_stream output
# ════════════════════════════════════════════════════
print("[2] audit_stream output...", end=" ")
audit_entries = []
if AUDIT_STREAM.exists():
    with open(AUDIT_STREAM, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    audit_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

if len(audit_entries) < 1:
    print(f"FAIL: expected >=1 audit entries, got {len(audit_entries)}")
    ok = False
else:
    # Verify audit entries have required fields
    required = ["signal", "action", "reasoning"]
    for field in required:
        if field not in audit_entries[0]:
            print(f"FAIL: audit entry missing '{field}'")
            ok = False
            break
    if ok:
        print(f"PASS ({len(audit_entries)} entries, fields OK)")

# ════════════════════════════════════════════════════
# Test 3: Field contract — better_path (not better_solution)
# ════════════════════════════════════════════════════
print("[3] field contract (better_path vs better_solution)...", end=" ")

# Check that intuition_engine.py's SYSTEM_PROMPT mentions "better_path"
engine_path = Path(__file__).parent.parent / "core" / "intuition_engine.py"
prompt_text = engine_path.read_text(encoding="utf-8") if engine_path.exists() else ""

if '"better_path"' not in prompt_text:
    print("FAIL: SYSTEM_PROMPT missing 'better_path' field")
    ok = False
elif '"better_solution"' in prompt_text:
    print("FAIL: SYSTEM_PROMPT still has deprecated 'better_solution'")
    ok = False
else:
    print("PASS")

# ════════════════════════════════════════════════════
# Test 4: fire_intuition signature
# ════════════════════════════════════════════════════
print("[4] fire_intuition signature...", end=" ")
import inspect
sig = inspect.signature(fire_intuition)
params = list(sig.parameters.keys())
if "task_context" not in params:
    print(f"FAIL: fire_intuition missing task_context param (has: {params})")
    ok = False
else:
    print(f"PASS (params: {params})")

# ════════════════════════════════════════════════════
# Test 5: behavior counter trigger at correct intervals
# ════════════════════════════════════════════════════
print("[5] intuition trigger intervals...", end=" ")
save_state(_fresh_state())
trigger_steps = []
for i in range(1, 13):
    update("Write", "test.py")
    if should_fire_intuition():
        trigger_steps.append(i)
        reset_intuition_counter()

expected = [5, 10]
if trigger_steps == expected:
    print(f"PASS (triggers at {trigger_steps})")
else:
    print(f"FAIL: expected {expected}, got {trigger_steps}")
    ok = False

# ════════════════════════════════════════════════════
print()
print(f"{'='*50}")
print(f"  {'ALL PASS' if ok else 'SOME FAILED'}")
print(f"{'='*50}")
sys.exit(0 if ok else 1)
