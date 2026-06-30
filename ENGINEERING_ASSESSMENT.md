# Newton-X v2.0 工程健康评估报告

> 诊断者：技术顾问 顾衡（纯诊断，不改代码）
> 诊断日期：2026-06-30
> 项目路径：`D:/TOOLS/cloude code/newton-v2`
> 代码规模：core/ 约 1100 行 Python，9 模块 + 4 测试剧本 + 3 报告快照
> Git：6 commit、单分支 master、零 tag、零 CHANGELOG、工作区干净

---

## 一句话结论

**架构是对的，但系统从未真正端到端跑通过。** 唯一的生产入口 `system2_daemon.py` 里有两个致命接线 bug——一个让 daemon 在有历史数据时直接崩，一个让最核心的"每 5 步外脑直觉"功能被静默吞错永久失效。所有"成功"的测试报告都绕过了 daemon、直接调底层引擎、且用的是和生产不同的调用签名，于是**测试全绿和生产全坏同时成立**。裁决是**重构（小手术级），不是重写**——别把唯一健康的资产（架构）也烧掉。

---

## 健康速览（9 维 × 严重度）

| 维度 | 严重度 | 半句话 |
|---|---|---|
| 架构连贯性 | 🟢 健康 | 模块边界清、分层干净、无循环依赖、无 god 模块——全项目最强一维，别动 |
| 设计质量 | 🟡 关注 | 三处"配置项假装可配"（api_url / intuition_interval / cooldown 都定义了但代码无视） |
| 构造健康 | ⚫ 烧钱 | daemon 两个致命 bug + 字段错配 + 静默吞错叠加 → 系统没真正工作过 |
| 测试态势 | ⚫ 烧钱 | 测试是写死的剧本不是验证网，且绕过生产路径，给的是**虚假安全感**（比没测试更危险） |
| 配置/发布成熟度 | 🟡 关注 | 有 setup/.gitignore/单分支，但零 tag、零 CHANGELOG、依赖范围非锁定、"2.0.0"名实不符 |
| 可运维性 | 🔴 该处理 | daemon 三处静默 except，出错无感；无结构化日志；外脑静默失效后"看起来还在跑" |
| 技术债/经济性 | 🔴 该处理 | 高利率债，集中在唯一生产入口——想用就被绊；但代码小、定位清，该现在还 |
| 可维护/可演进 | 🟢 健康 | 代码小而清晰、命名好、变更放大小、上手成本低——改起来不疼（一旦知道改哪） |
| 安全态势 | 🟡 关注 | 密钥扫描干净；但 key 走 curl 命令行参数 + standalone agent `shell=True` 无沙箱（仅特定场景兑现） |

分布：⚫×2、🔴×2、🟡×3、🟢×2。

---

## 发现（按严重度排序，带证据）

### ⚫-1 daemon 启动崩溃：`entries` 先用后定义
- **证据**：`core/system2_daemon.py:214` 在历史加载循环里 `entries.append(result)`，但 `entries` 直到 `:224` 才 `entries: list[dict] = []` 定义。
- **根因**：`entries` 是 `main()` 的局部变量（因 :224 有赋值），Python 把整个函数体内的 `entries` 都当局部名，:214 在 :224 之前执行 → `UnboundLocalError: local variable 'entries' referenced before assignment`。
- **触发条件**：`RAW_STREAM` 文件里有任意一行历史事件即触发。首次全新启动（空文件 touch 出来）不崩——但任何真实使用后（hook 写过事件）重启必崩。
- **影响**：daemon 是系统唯一的生产入口。这个 bug 意味着它只能在"空数据"状态下苟活一次，一旦真用过就起不来。

### ⚫-2 核心功能静默失效：`fire_intuition()` 签名不匹配 + 被吞
- **证据**：`core/system2_daemon.py:173` 定义 `def fire_intuition() -> dict | None:`（无参），但 `:252` 调用 `fire_intuition(current_task)`（传一个参数）→ `TypeError`。该调用位于 `:241-274` 的 `try`，被 `:273 except Exception: pass` **静默吞掉**。
- **根因**：函数签名与调用点不一致，且外层裸吞所有异常。
- **影响**：每到第 5 步（`should_fire_intuition()` 为真）就抛 TypeError 被吞 → `intuitions` 列表永远为空 → 监控终端永远不显示外脑直觉。**这是产品最核心的卖点（每 5 步 LLM 直觉），在生产路径里从开火第一刻起就死了，而且因为吞错，用户看不到任何报错，以为系统在正常工作。** 这比 ⚫-1 更隐蔽、更致命。
- **连带**：`:178 engine.analyze(17)` 把 17 当成 `look_back`（analyze 签名是 `analyze(look_back=15, task_context=None)`），`current_task` 自 `:226` 定义后从未赋值、恒为 None → 即便签名修好，README 重点宣传的 Round 0 意图显化在 daemon 路径也拿不到任务、永远是死的。

### ⚫-3 "更优解法"字段错配，静默丢失
- **证据**：`core/intuition_engine.py:65` 的 SYSTEM_PROMPT 要求 LLM 输出 `"better_path"`；但 daemon `:264` 与 render `:83` 读的是 `insight.get("better_solution")`。
- **根因**：产出方与消费方字段名不一致。
- **影响**：LLM 按 prompt 返回 `better_path`，代码到处 `get("better_solution")` → 永远拿到空字符串 → README 重点宣传的"更优解法 / Better Path"在 UI 上永远不显示。同类问题也存在于测试（`comprehensive_test.py:210/277` 读 `better_solution`、`:204` 读 `goal_deviation`，二者都不在当前 prompt 的输出契约里）。

### ⚫-4 测试是剧本，不是验证网（且绕过生产路径）
- **证据**：
  - `tests/feedback_loop_test.py` 的 **MODE A 根本不运行**——`:158-166` 只对硬编码列表 `PATH_A` 做 `len()/set()/sum()` 静态计数，从不调 LLM、从不跑 brain。
  - MODE B 的"agent 纠正"是**剧本预先写死的**——`:87` 直接写 `"# think: 纠正——删掉多余端点..."`，`:196` 注释自陈 `Simulate: agent sees alert and corrects in next steps`。brain 报不报警，后续步骤都一样。
  - 对比表 `:233/:236/:248` 的"最终偏离 严重 vs 轻微""节省 X 文件"是 `len(PATH_A)-len(PATH_B)`——**两个人工剧本相减**，LLM 对这些数字毫无因果贡献。`reports/long_task_report.txt:67` 的"节省 6 步、13 个多余文件被避免"即由此而来，也就是 README 的"15 files avoided"的真实来源。
  - **所有测试绕过 daemon、直调 engine、且用不同签名**：`comprehensive_test.py:181` 调 `analyze(i+5, task_context=TASK)`（正确传任务），而生产 daemon `:178` 调 `analyze(17)`（不传任务）。测试覆盖的代码路径 ≠ 生产代码路径。
- **根因**：把 demo/营销脚本当成了测试。这类"测试"无法失败（剧本设计成必触发），因此无法防回归、无法发现 ⚫-1/⚫-2。
- **影响**：测试全绿掩盖了生产全坏。`reports/` 还是**过时快照**——里面出现的 `[GOAL_DEV]`、`better_solution` 字段与当前 prompt 的输出契约都对不上，说明报告生成于改 prompt 之前（commit f96142d 才加 Round 0）。README 的 Test Results 表引用的是这些过时报告。**这是比"没有测试"更危险的状态——它制造了系统可用的错觉。**

### 🔴-5 静默吞错让所有 bug 隐形（可运维）
- **证据**：`core/system2_daemon.py:215`、`:273` 两处 `except Exception: pass`，`:286` 一处裸 `except: pass`（连 KeyboardInterrupt/SystemExit 都吞）。
- **根因**：事件处理、直觉触发、PID 清理的失败全部静默。
- **影响**：⚫-2 之所以能长期隐形，根因就是这里。daemon 出任何错都不留痕，用户无法判断系统是否在正常工作。全项目用 `print` + ANSI 终端渲染，无结构化日志、无错误监控；唯一的可观测产物 `audit_stream.jsonl` 没有任何消费方。
- **注**：`audit_hook.py:48` 的静默 except 是**正确的例外**——hook 绝不能阻塞用户工具（有注释 `Never block the tool`），这处别动。

### 🔴-6 技术债集中在生产入口（高利率）
- **证据**：上述 ⚫/🔴 全部集中在 `system2_daemon.py` 这一个文件——它是唯一的生产路径。另有死代码：cooldown 子系统 `intuition_engine.py:88 COOLDOWN_SECONDS=0`（`_in_cooldown` 永远 False，:87-95/:137/:146 全是 no-op）、`behavior_state.py:27 WARNING_COOLDOWN=600` 定义后从不使用、`system2_daemon.py:227/:278 last_render` 赋值后从不读取。
- **判据（疼不疼）**：这是**高利率债**——不是"碰都不敢碰的角落"，而是"每次想真正使用系统就被绊"。但代码量小、定位清晰、不是架构性的，该现在还。
- **诚实标注**：本维是构造健康(⚫)+可运维(🔴)的经济学投影，指向的是同一批接线问题，不是新增独立问题。给 🔴 是因为它落在生产入口、利率高。

### 🟡-7 三处"配置项假装可配"（设计质量）
- **证据**：
  - `config.py:21 api_url` 定义了，但 `intuition_engine.py:165` 的 `_call_api` 把 URL 硬编码成字面量 `"https://api.deepseek.com/..."`，无视配置。
  - `config.py:22 intuition_interval` 定义了，但 `behavior_state.py:175 INTUITION_INTERVAL = 5` 硬编码，从不读 config。
  - cooldown 同上（见 🔴-6）。
- **影响**：用户改 config.json 里这几项不生效，会困惑。要么接线、要么删掉假装可配的 default——别让契约撒谎。

### 🟡-8 发布成熟度名实不符（配置/发布）
- **证据**：`git tag` 为空，但 `setup.py:5 version="2.0.0"`；无 CHANGELOG；`requirements.txt` 仅 `rich>=13.0.0`（范围非锁定，无 lockfile）；代码实际依赖系统 `curl`（`intuition_engine.py:162`、`standalone_agent.py:208/216/226/280` 走 subprocess 调 curl）但未在依赖里声明。`__init__.py` 无版本号、无导出。
- **影响**：对个人项目可接受，但"2.0.0"无对应 tag、无 CHANGELOG 时，回滚和版本追溯无依据。curl 的隐式依赖在没装 curl 的环境会静默失败（被 ⚫-2 同款吞错路径吃掉）。

### 🟡-9 安全：凭据走命令行 + agent 无沙箱（特定场景兑现）
- **证据**：
  - API key 作为 curl 命令行参数：`intuition_engine.py:167`、`standalone_agent.py:230/284` 的 `f"Authorization: Bearer {API_KEY}"` → 进程列表 `ps` 可见。
  - `standalone_agent.py:208 subprocess.run(cmd, shell=True, ...)` 执行 LLM 生成的任意命令，无沙箱/无确认/无白名单，`cwd` 默认是用户 HOME（`:33 WORK_DIR=Path.home()`）。LLM 幻觉一条破坏性命令即可删 home。
- **触发条件（诚实）**：key 命令行泄露仅在**多用户/共享机**兑现（单机自己看自己 ps 风险低）；shell=True 自毁仅在**真跑 standalone agent 自主任务**时兑现。若主用法是"daemon + hook 监控自己的 Claude Code"，二者都不触发——故定 🟡 不定 🔴。
  - **好消息**：密钥残留扫描全库 0 命中（`sk-` 无匹配），commit 9c0a77d 的清理是干净的。README:145 说的 "hardcoded default" key 是**过时文档**，实际代码默认空字符串 + 报错退出，不是漏洞。

### 附：launcher 路径含空格会断（归入构造健康）
- **证据**：`cli.py:31` 把 `CORE_DIR` 直接拼进 shell 字符串 `cd /d {CORE_DIR}`。当前项目路径 `D:/TOOLS/cloude code/newton-v2` **含空格**，cmd 会把 `code\newton-v2` 当成第二个参数 → cd 失败 → python 找不到脚本。
- **影响**：`newton start/agent/all` 在当前路径下必然启动失败。可绕过（直接 `python system2_daemon.py`），故不单列严重度，并入构造健康。

---

## 重构 vs 重写裁决

**裁决：重构（小手术级），不重写。** 三条硬检验逐条判：

| 检验（三条全真才考虑重写） | 判定 | 依据 |
|---|---|---|
| ① 在既有代码上改的成本 > 重写成本？ | **假** | bug 全是接线级不是架构级：entries 移一行、fire_intuition 加个参数、字段名统一——每个 < 1 小时。架构本身 🟢，重写要把好架构一起扔，成本远大于改 5 个 bug。 |
| ② 需求已稳定？ | **假/存疑** | 实验性"外脑"项目，核心理念（纯直觉 vs 规则）还在探索，prompt 还在迭代（f96142d 刚加 Round 0）。需求未定。 |
| ③ 有测试/验证网？ | **假** | 测试是剧本（⚫-4），不能防回归。重写没有安全网兜着 = 裸奔。 |

三条**全假**。重写是"高估自己、低估既有代码隐含知识"的陷阱——而这个项目唯一值钱的隐含知识恰恰是那套**对的架构**。推倒它去重写，是亲手烧掉唯一健康的资产。

---

## 建议（按优先级排序，每条带成本）

### R1 — 修 daemon 三个接线 bug【⚫，不可推迟】
- **做什么**：(a) `entries` 定义上移到历史加载循环之前；(b) `fire_intuition` 加 `task_context` 参数并把 `current_task` 真正传进 `analyze`；(c) 统一字段名 `better_path`（prompt、daemon、render、测试四处对齐）。
- **为什么**：见 ⚫-1/⚫-2/⚫-3。这是让系统**第一次真正端到端跑通**的前提。
- **工时**：2-3h。
- **不做的代价**：系统从未真正可用，所有"成功"都是假象。
- **能否推迟**：不能。这是产品存在的前提。

### R2 — 加一个真正的端到端冒烟测试【⚫，与 R1 配对】
- **做什么**：写几行 raw 事件进 `RAW_STREAM` → 跑 daemon 一个循环（或抽出可测的 `process_event`+`fire_intuition` 主流程）→ 断言 `audit_stream` 有输出、intuition 真触发、`better_path` 真出现。覆盖**生产路径本身**，不是绕过它调 engine。
- **为什么**：见 ⚫-4。没有这个，R1 修好的 bug 会再次悄悄回归，下次还是静默失效。
- **工时**：3-4h。
- **不做的代价**：R1 白修——回归后又是测试全绿、生产全坏。
- **能否推迟**：不能。和 R1 是一对，单做 R1 不做 R2 等于没修。

### R3 — 收口静默吞错【🔴，可短期推迟】
- **做什么**：daemon `:215/:273/:286` 三处 except 至少把异常打到 stderr 或日志文件；裸 `except:` 改为具体异常类型。保留 `audit_hook.py:48` 的静默（那处是对的）。
- **为什么**：见 🔴-5。⚫-2 长期隐形的根因就是这里。
- **工时**：1-2h。
- **不做的代价**：下次出 bug 还是看不见，调试靠猜，每次 debug 成本翻倍。
- **能否推迟**：可推迟几天，但每推迟一天 debug 成本上升。建议紧跟 R1/R2。

### R4 — 接线或删除"假装可配"的配置项【🟡，可推迟】
- **做什么**：`api_url`/`intuition_interval` 二选一：要么让代码真读 config，要么删掉 default 别让契约撒谎；cooldown 子系统要么启用要么删（现在是死代码）。
- **为什么**：见 🟡-7。
- **工时**：1h。
- **不做的代价**：用户改 config 不生效会困惑，但不影响核心功能。
- **能否推迟**：可。等 R1-R3 落地后顺手做。

### R5 — 凭据不走命令行 + agent 加最小边界【🟡，按使用场景决定】
- **做什么**：curl 的 Authorization 改从 stdin/`--config` 传，消除 `ps` 泄露面；`standalone_agent` 的 `shell=True` 加命令白名单/确认，`WORK_DIR` 收窄到专用沙箱目录而非 HOME。
- **为什么**：见 🟡-9。
- **工时**：2-3h。
- **不做的代价**：单机自用风险低；**若要在共享机部署或让 agent 长时间自主跑，这条升级为 🔴，必须先做**。
- **能否推迟**：取决于使用场景。daemon+hook 主用法可推迟；standalone agent 自主跑则不可推迟。

---

## 建议不动（健康的东西，动它就是制造工作）

- **`abstraction_layer.py`** — 纯函数、静态方法、零副作用、正则集中、职责单一。全项目最干净的模块，别碰。
- **整体分层架构 + ATLAS 数据流** — 模块边界、单向数据流、lazy import 解循环依赖都是对的。重构只修 daemon 内部接线，**不要动模块划分**。
- **`config.py` 三级优先级加载（file > env > default）** — 干净，有损坏 JSON 容错（:35）。
- **`audit_hook.py` 的极简 + "Never block" 静默吞错** — 这是**正确的**静默（hook 不能阻塞用户工具）。别把它"修"成会抛错的——那是制造 bug。
- **`thinking_stream_manager.py` 的 MAX_ENTRIES 上限 + 损坏 JSON 容错** — 防无限增长 + 容错都做了，健康。
- **`.gitignore` 对 `*.jsonl` 的忽略** — 防止含密钥/数据的流文件入库，正确。

---

## 一页纸总结

这个项目的诊断很反直觉：**它不是写得烂，是没接通。** 架构、命名、模块解耦都是优等生水平（🟢🟢），但 daemon 这一个文件里的几处接线断裂，加上一套"测不出问题"的剧本测试，让系统从未真正工作过、却一直以为自己在工作。好消息是修复成本极低（2 个 ⚫ bug 加起来一个上午），坏消息是没有 R2 的真测试，修了也守不住。**先 R1+R2 让它第一次真跑通并锁住，再 R3 让以后的 bug 看得见，其余按场景推迟。重构，不重写。**
