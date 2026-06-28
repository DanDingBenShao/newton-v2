# Newton-X v2.0 — AI Cognitive Boundary System

An external brain that monitors AI agents in real-time, detecting cognitive blind spots through pure intuition — not rule matching.

## What it does

- **Monitors** an AI agent's tool-call stream (Write, Edit, Read, Search, etc.)
- **Abstracts** tool calls into intent labels (zero LLM cost — pure regex)
- **Builds** a thinking stream with `# think:` annotations extracted from the agent's code
- **Feeds** the compressed thinking stream to an LLM intuition engine every 5 tool calls
- **Produces** structured alerts: WARNING / ALERT with perception, amplification, regulation
- **Detects**: scope creep, wheel reinvention, cognitive gaps, analysis paralysis, goal deviation
- **Suggests** better paths (standard library alternatives, simpler architectures)

## Architecture

```
Agent Tool Calls
     │
     ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  audit_hook  │────▶│  system2_daemon  │────▶│ intuition_engine │
│  (<1ms)      │     │  (real-time)     │     │  (LLM, ~8s)     │
│  raw events  │     │  abstraction     │     │  cognitive       │
│              │     │  thinking stream │     │  intuition       │
└─────────────┘     └──────────────────┘     └─────────────────┘
                            │
                            ▼
                     ┌──────────────────┐
                     │  Monitor Terminal │
                     │  (live display)   │
                     └──────────────────┘
```

## Quick Start

```bash
# 1. Launch the monitor (visible terminal)
python core/system2_daemon.py

# 2. Launch the agent (or use your own agent that writes to newton_raw.jsonl)
python core/standalone_agent.py

# 3. Send tasks by writing to ~/.claude/newton_task.jsonl
echo '{"task": "Build a simple blog API"}' >> ~/.claude/newton_task.jsonl
```

Or double-click `core/launch_all.bat` (Windows).

## Run Tests

```bash
# 9-task category matrix
python tests/extended_test.py

# A/B comparison (with vs without brain)
python tests/feedback_loop_test.py

# Realistic 3-phase user scenario
python tests/realistic_scenario.py
```

## Core Modules

| Module | Purpose | Cost |
|---|---|---|
| `abstraction_layer.py` | Extract intent labels from tool calls (regex) | 0 tokens |
| `behavior_state.py` | Cross-call counters + trigger logic | 0 tokens |
| `thinking_stream_manager.py` | Persistent log of agent actions | 0 tokens |
| `intuition_engine.py` | LLM-powered cognitive monitor | ~500 tokens/call |
| `system2_daemon.py` | Real-time daemon + live monitor display | N/A |
| `audit_hook.py` | Minimal Claude Code hook (<1ms) | 0 tokens |
| `standalone_agent.py` | Autonomous DeepSeek-powered agent | Per-task |

## Intuition Engine Prompt

The System Prompt defines only **thinking directions**, not pattern rules:

- **Round 1**: What intuition does this behavior sequence trigger?
- **Round 2**: Is my intuition correct? What would the agent's defense be?
- **Round 3**: Converge — distill into actionable insight + better path

No predefined "blind writing" or "tunnel vision" rules. The LLM discovers cognitive patterns from its training experience.

## Test Results (deepseek-v4-flash)

| Test | Tasks | Through Rate | Better Path | Avg Latency |
|---|---|---|---|---|
| Extended Matrix | 9 tasks × 5 categories | 100% | 9 | 11.7s |
| A/B Comparison | 29-step blog task | — | — | 5 interventions, 15 files avoided |
| Realistic Scenario | 3-phase, 27 steps | — | 5/5 alerts | 2 user check-ins |

## Requirements

- Python 3.10+
- DeepSeek API key (hardcoded default or `DEEPSEEK_API_KEY` env var)
- `rich` library (optional, for enhanced monitor display)

## Design Philosophy

- **Not a code reviewer** — v1.0 does code audit. v2.0 does cognitive monitoring.
- **Not a rule engine** — no predefined "correct" or "wrong" patterns.
- **Universal thinking directions** — same approach works for any task, any domain.
- **Feedback loop** — brain alerts → user corrects → agent adjusts → brain monitors again.
