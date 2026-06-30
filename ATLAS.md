# Newton-X v2.0 — 项目模块图索引 (ATLAS)

> 索引规则：文件名 = 完整语义。Agent `ls` 即知要先读哪个。

## 核心引擎 (core/)

| 文件 | 职责 | 依赖 | 入口 |
|---|---|---|---|
| `cli.py` | 统一命令行入口 (`newton init/start/agent/all/test/demo`) | config, system2_daemon, standalone_agent | `newton` |
| `config.py` | 配置管理 — `~/.newton-x/config.json` + 环境变量 fallback | 无 | `load()`, `init_config()`, `get()` |
| `intuition_engine.py` | LLM 直觉引擎 — Round 0 意图显化 + 2轮发散 + 1轮收敛 | thinking_stream_manager, config | `IntuitionEngine(stream_mgr).analyze()` |
| `abstraction_layer.py` | 抽象层 — 正则提取意图标签、`# think:` 注解、代码摘要。零 LLM | 无 | `extract_intent()`, `extract_thinking()`, `extract_content_summary()` |
| `thinking_stream_manager.py` | 思考流管理器 — JSON 持久化，图标摘要，行为统计 | config | `ThinkingStreamManager().add_thought()` |
| `behavior_state.py` | 行为状态机 — 跨调用计数器，每5步触发直觉 | config | `update()`, `should_fire_intuition()` |
| `system2_daemon.py` | 常驻守护进程 + 实时监控终端 — tail 原始事件，跑完整 v2.0 管道 | 全部 core 模块 | `python system2_daemon.py` |
| `audit_hook.py` | Claude Code Hook 适配器 — 只写原始事件 (<1ms)，退出 | config | PostToolUse hook |
| `standalone_agent.py` | 独立 Agent — DeepSeek 驱动，全工具，轮询任务文件 | abstraction_layer, config | `python standalone_agent.py` |

## 测试 (tests/)

| 文件 | 内容 | 运行 |
|---|---|---|
| `extended_test.py` | 9 任务 × 5 类别矩阵测试 | `newton test` |
| `feedback_loop_test.py` | A/B 对比 — 无外脑 vs 有外脑+反馈闭环 | `python tests/feedback_loop_test.py` |
| `realistic_scenario.py` | 3 阶段真实用户场景模拟 | `newton demo` |
| `comprehensive_test.py` | 单任务全维度触发测试 | `python tests/comprehensive_test.py` |

## 报告样本 (reports/)

| 文件 | 来源 |
|---|---|
| `extended_test_report.txt` | `newton test` 输出 |
| `long_task_report.txt` | `feedback_loop_test.py` 输出 |
| `realistic_scenario_report.txt` | `newton demo` 输出 |

## 数据流

```
Agent 工具调用
  │
  ├─→ [Hook 模式] audit_hook.py → newton_raw.jsonl
  │
  ├─→ [直接模式] 你的 Agent 直接写 JSONL 到 newton_raw.jsonl
  │
  ▼
system2_daemon.py (常驻)
  ├─ tail newton_raw.jsonl
  ├─ abstraction_layer → intent 标签
  ├─ behavior_state → 计数器
  ├─ thinking_stream_manager → 持久化
  ├─ intuition_engine → 每5步 LLM 直觉
  └─ 终端实时显示
```

## 快速开始

```bash
pip install -e .
newton init              # 创建 ~/.newton-x/config.json
export DEEPSEEK_API_KEY=sk-xxx
newton all               # 启动 daemon + agent
```

## 接入你的 Agent

你的 Agent 每步工具调用写一行 JSON 到 `~/.newton-x/newton_raw.jsonl`：

```json
{"tool_name": "Write", "file_path": "api.py", "tool_input": {"path": "api.py", "content": "# think: 实现REST端点\ncode..."}, "timestamp": "14:30:05"}
```

`# think:` 注解自动提取为 Agent 意图。System 2 实时读取，无需 SDK。
