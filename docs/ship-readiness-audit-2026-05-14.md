# Ship-readiness audit (Enterprise Knowledge Agent v4)

> Date: 2026-05-14. Audit-only. 不改任何代码或文档, 仅产出 punch list 供 Fei 决策。
> Viewpoint: 资深 hiring manager / staff engineer 给一个 NL AI Engineer 候选人 portfolio 提诚实意见。
> Audit 范围: README + docs/ + live deploy (https://enterprise-knowledge-agent.fly.dev) + pytest + git。
> `gh` CLI 在本审计环境不可用, GitHub Actions 状态用 git log + workflow yml 推断而非真实查询。

## TL;DR

整体 ship-ready 度 **78 / 100**。可以投, 但有一个明确 blocker + 三个 should-fix 影响第一印象。

- **Blocker (1)**: 根 URL `https://enterprise-knowledge-agent.fly.dev/` 返回 `{"detail":"Not Found"}` 404。LinkedIn / 简历点进来第一眼就是 JSON 404, 即使 API 本体没问题, 给非技术 recruiter 的观感是"挂了"。
- **Should-fix (3)**: (1) 仓库根没有 `LICENSE` 文件 (只有 `pyproject.toml` 里的 `license = "Apache-2.0"` metadata); (2) `docs/demo-script.md` 和当前 live deploy 漂移严重 (Gradio UI 在线上根本没暴露, 假数字 `$0.018 / 47s` 跟 leaderboard 的 `$0.0036 / 150s` 冲突); (3) `docs/eval-methodology.md` line 11 还在说 "HotpotQA F1 of 0.077", README 已经是 0.29, 同站不同数。
- **Nice-to-have (4)**: README hero 段缺一个"无真实客户数据"的 disclaimer 在第一屏; Quickstart 在新 clone 上 `docker compose up` 会因为 `data/synthetic/` 是 gitignored 而启动失败; Codex CLI pair-programming 的 attribution 只在 `docs/index.md` 露面, README 看不到; `docs/a3_semantic_cache.md` 留了三个 `TBD` 格子在公开 nav 路径外, 但是 site/ 已 build 进去, 会被搜索引擎索引。

差异化卖点 (cross-source policy + honest ablation + multi-judge consensus) 站得住脚。Self-Refine -0.08 / DSPy Goodhart / MoE Pareto / Counterfactual governance-held 这四张表都是真材实料, 不是 cherry-pick。

---

## A. 上线可用性

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| A1 | `GET /health` → 200 OK, 60ms (Amsterdam → 测试机)。warm machine 已生效。 | informational | 保持。 |
| A2 | `POST /query` 跑 README 的 curl one-liner, SSE 5 节点全部触发: plan → tool_select → tool_execute → reflect → synthesize → final → done。citation 形式正确 `[calendar_query:2026-05-11]`。 | informational | 保持。 |
| A3 | Langfuse 集成代码逻辑正确: `@observe` 装饰 `query()`, `record_generation` 在缺 keys 时静默 no-op, v4 OTel 客户端 lazy import。Fly secrets 配置已 set (LANGFUSE_PUBLIC_KEY / SECRET_KEY / BASE_URL)。trace 应该有数据。 | informational | 在 README "Observability" 一行加一个 "trace UI 截图" 链接或 "ping me for read-only access" 注脚, 不然读者只能信你不能验证。 |
| A4 | warm machine 配置 `min_machines_running = 1`, fly.toml 注释把 2-3 分钟 import cold-start 原因写清楚了。HA replica auto-stop 也对。 | informational | 保持。 |
| A5a | `user_name=nonexistent_user_xyz` → 404 JSON `{"detail":"User not found: ..."}`。干净。 | informational | 保持。 |
| A5b | `query="aaa..." × 2500 字符` → 422 JSON, Pydantic `string_too_long` ctx.max_length=2000。干净。 | informational | 保持。 |
| A5c | `user_role=engineer` 越权查 HR 文档 → governance 拒绝。Agent 回 "No HR private salary documents are visible to you" + 明确解释 ACL `hr`/`leadership` 对 engineer 不可见 + "I can't help you bypass it"。**这条做得漂亮**, 而且 agent 没幻觉。 | informational | 这条值得在 demo video 单独拿出来讲。 |
| A5d | `user_role` 字段是 free-form `str` 接受任何值 (例如 "engineer" 这个不在 description 列表 "IC \| manager \| HR" 里的角色), 下游 RBAC 视未知角色为最小权限处理。功能没事, 但 API 表面看起来像缺字段校验。 | nice-to-have | 把 `user_role` 改成 `Literal["IC", "manager", "HR", "exec"]` 之类的 enum, 或者在 description 里说明"任何未在列表内的值视为最小权限"。 |
| A6 | 根 URL `GET /` → 404 `{"detail":"Not Found"}`。 | **blocker** | 加一个最小 `GET /` 返回 HTML 落地页: "Enterprise Knowledge Agent · API only. /health · POST /query · GET /users · Repo: ..."。或者 302 重定向到 GH Pages docs site。**这条是 portfolio 第一接触点, 必须修。** |
| A7 | `GET /users` 暴露全部 30 人 PII (姓名 + 角色 + 部门 + 办公地), 没有任何 auth 保护。Fei 自己知道是合成数据, recruiter 不知道。 | nice-to-have | 在 `/users` 返回里加一个 "synthetic_data": true 字段或在 root 落地页里点明。或者直接限速 + 加 `note` 字段。 |

---

## B. README & docs 可读性

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| B1 | README 前 7 行命中卖点: 跨源 6 SaaS, 实盘 URL, Langfuse trace, 还附了一条可点的 curl。**5 分钟评分 7/10**, 缺一个一句话的"hero claim"在最顶上回答"为啥 recruiter 要花 10 分钟"。当前第一行 "Production-grade open-source enterprise knowledge agent" 是个名词短语, 不是 claim。 | should-fix | 在第一行下补一句 hero claim, e.g. "Ships 4 frontier-technique ablations with honest with-vs-without tables, including 3 negatives. Live demo + 101/101 tests + audit log." 这就是你的差异化。 |
| B2 | Leaderboard 表 + 每类 breakdown + 4 行 frontier ablation 表都在第一屏 (前 60 行 README)。**做得好**, 比 95% 的 portfolio 直观。 | informational | 保持。 |
| B3 | `grep -rn "TBD\|TODO\|FIXME\|XXX\|placeholder" docs/ README.md` 结果: (a) `docs/a3_semantic_cache.md` 三处 TBD 是真实 placeholder; (b) `docs/blog-outline.md` 一处 `{INSERT_NUMBERS_HERE}`; (c) `docs/v3-frontier-plan.md` 多处 TBD, 是历史草稿, mkdocs nav 把它放在 "History (superseded)" 下, 可以接受; (d) `docs/v2-plan-opus-review.md` 一处 TBD, 也是 superseded。 | should-fix | a3_semantic_cache.md 改成 "Not measured in v4 (deferred to v1.5)" 之类明确说法, 或从 mkdocs nav 拿掉。blog-outline.md 的 `{INSERT_NUMBERS_HERE}` 现在已经能填: DSPy 段就把 sprint4_dspy_agent_ablation.md 的数字搬过来。 |
| B4 | `https://huangf06.github.io/enterprise-knowledge-agent/` → HTTP 200, mkdocs material 已 render。site/ 目录已 build 进 repo (35 个 md 都 export 了)。 | informational | 保持。site/ 目录 commit 进 repo 看起来是 GH Pages 用 docs.yml workflow 自动 deploy, 不是手 push, 可以确认一下。 |
| B5 | 整体 voice: 偏技术、偏自信、honest negative 自己点名。没有装人情味, 也没有过度卖。**适合 NL hiring 风格**。Dutch/Nordic recruiter 喜欢这种"don't oversell"。 | informational | 保持。如果想加一点温度, 在 README 末尾或 `docs/index.md` 加一段 1-2 句的 "为什么我做这个 project / 为什么我搬到 NL" 比 emoji 有效得多。 |
| B6 | `docs/eval-methodology.md` line 11: "HotpotQA F1 of 0.077 is documented as a v1 known gap"。但 README + STATUS.md + w4_report.md 都是 F1=0.29 (lift from 0.077 naive baseline)。同站不同数, 而且 eval-methodology.md 还出现在 mkdocs nav 顶部 "Architecture · Eval methodology"。 | **should-fix** | 把那行改成 "F1 lifted from 0.077 (naive span) to 0.29 (llm-answer mode in W6) — still below the 0.70 target."。一句话就解决。 |
| B7 | README "Quickstart" 段的 `docker compose up -d qdrant postgres` 顺序之后才是 `generate_data.py`, 但 `docker compose up` (full stack) 会启动 api 服务, api 在 `infra/Dockerfile` 里 `COPY data /app/data`。问题: 新 clone 时 `data/synthetic/` 是 gitignored 空的, COPY 进去就是空, agent 启不来。 | should-fix | Quickstart 加一行 "Run `uv run python scripts/generate_data.py --seed 42` BEFORE `docker compose up` (the API image bakes data in)" 或者把 generate_data 加进 Dockerfile entrypoint。 |
| B8 | `docs/case-study-hr-helpdesk.md` 和 `docs/architecture.md` 在 mkdocs nav 内, 都 reference Gradio UI 作为"已 shipped"。但 live deploy 上没有 Gradio。如果 recruiter 顺着 nav 去找 UI, 找不到。 | nice-to-have | Architecture / case-study 文档里加一句脚注 "Live Fly deploy is API-only; Gradio UI runs locally via `uv run python -m src.ui.app`"。 |

---

## C. Frontier ablation 诚实性

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| C1 | 4 个 ablation 都有 with-vs-without 表: Self-Refine `frontier3_self_refine.md` (n=30), DSPy `sprint4_dspy_agent_ablation.md` (n=10 fast-tier, 双 judge regime), MoE `sprint5_moe_pareto.md` (4 vendors × n=10), Counterfactual `sprint6_counterfactual_result.md` (3 perturbations × n=10)。 | informational | 保持。 |
| C2 | Negative 没有被淡化: Self-Refine 是 "**OFF default**: -0.05 to -0.08", DSPy 是 "**OFF default**: +0.05 on correctness BUT -1.0 on cite_source_coverage"。README leaderboard 表里 "Verdict" 列就明说 OFF default + 数字给出来。**这是这个 portfolio 最强的差异化, 没有 cherry-pick**。 | informational | 保持。 |
| C3 | DSPy 2-judge vs 3-judge Goodhart 双 regime 写得**非常清楚**, sprint4_dspy_agent_ablation.md "Critical finding" 段直接点出 "**The compiled prompt's correctness lift is a Goodhart effect**. DSPy optimized against a metric that excluded the agent's own model class, and adding it back flips the sign of the headline delta. This is exactly the failure mode that v4.1 N1 + P15 were designed to surface."。这是 staff-level 才能看出的细节, **portfolio 黄金**。 | informational | 这段应当在 blog 里独立成节, 不要让它埋在一个 ablation doc 里。可以考虑在 README leaderboard 表的 DSPy 行 Verdict 列里直接出现 "Goodhart" 这个词, 给 hiring manager 一个钩子。 |
| C4 | MoE n=10 noise floor caveat: sprint5_moe_pareto.md line 23 明确说 "n=10 has roughly a ±0.07 noise floor on answer_correctness; any claimed lift smaller than that is not statistically meaningful at this scale. A v1.5 follow-up with n=30 + 95% bootstrap CI"。**做得对**。 | informational | 保持。但 README leaderboard 表里的 MoE 行只说 "+0.07 (within n=10 noise floor)" 一行, 没有提示读者去看 v1.5 followup 计划。值得在 v1.5_backlog.md 里有一个 "MoE n=30 bootstrap" 条目, 给读者证明你知道下一步在哪。 |
| C5 | Counterfactual governance hold-rate **1.00 across 3 perturbations**, 在 sprint6_counterfactual_result.md 第一段就显眼: "**Governance held across all three perturbations**", 在 README leaderboard 第四行 Verdict 列直接 "**Governance held at 1.00 across all perturbations**"。 | informational | 保持。 |
| C6 | 一个轻微的诚实瑕疵: README 第 51 行 DSPy 行 Verdict 是 "OFF default: +0.05 on correctness BUT -1.0 on cite_source_coverage and -0.17 on action_recommend_quality"。这个 +0.05 是**单 judge / 2-judge regime** 的, 3-judge regime 是 -0.03 (即 Goodhart 的反转)。在 README 这一行没有提 3-judge, 读者直觉会以为 "DSPy 在 correctness 上还是正的"。 | should-fix | 改一下行文为 "+0.05 (2-judge, training metric) → -0.03 (3-judge, comparison metric, the Goodhart reversal)"。一行内 self-contained。 |
| C7 | Self-Refine "Footnote A" cost contamination 自己写出来, 而且引用 fix commit hash `e332937`。**这种自我披露 hiring 会非常看重**。 | informational | 保持。 |

---

## D. 代码质量 + 可复现

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| D1 | `uv run pytest -q` → 101 passed in 27.89s, 0 fail。 | informational | 保持。 |
| D2 | 不能直接查 GH Actions (本环境无 `gh` CLI)。从 git log 推: 最近 commits 都是 docs / deploy 修复 (`e1b6861` `62f3b05` `e00828a` `336b3d3`), 涉及 fly.toml + Dockerfile + min_machines_running, 这些不会触发 eval-gate.yml 但会触发 docs.yml 和 test.yml。test.yml 只跑 pytest (除 retrieval/), 应该绿。eval-gate.yml + eval-nightly.yml 依赖 secrets, 在 commit `aef14b1` 里说 "fix(ci): eval workflows - move secrets check from job-level if to step gate", 表明这两个 workflow 之前 misconfigured, 现在按 step-gate 跳过 — 也就是不会真正 run eval, 只会通过。 | informational | 给 Fei 自己跑一下 `gh run list --limit 10` 验证。如果 eval-nightly 是 step-gated skip, 没问题, 但 README 不要说 "CI runs nightly eval" 类似话术 (检查了一下, 没说, 安全)。 |
| D3 | 外人 clone + `cp .env.example .env` + 填一个 DEEPSEEK_API_KEY → 跑 Quickstart 第一个 query, **会失败**。原因: `docker compose up` 会启 api 容器, 容器内 `data/synthetic/` 是空的 (因为 .gitignored, COPY 进去也是空)。 | should-fix | Quickstart 加 `uv run python scripts/generate_data.py --seed 42` 在 `docker compose up` 之前, 或者在 docker compose 的 api service 加一个 entrypoint 先跑 generate_data。或者在 Dockerfile 里加 `RUN uv run python scripts/generate_data.py --seed 42`。**实际上**生产 Fly image 已经把生成好的 1.5MB synth data baked 进去了, 因为 Fei 是先 generate 后 build, 但新 contributor 不会这么走。 |
| D4 | `git log --all --pretty= --name-only \| sort -u \| grep -iE "env\|secret\|key"` → empty。`.env` gitignored, `.env.example` 不含 secret。**clean**。 | informational | 保持。 |
| D5 | `data/synthetic/` 1.5MB 在本地存在, gitignored, 但 Dockerfile `COPY data /app/data` 把它 baked 进 image。一致性 OK, 但 (a) 任何 clone 必须先 generate_data.py 才能 docker build (见 D3); (b) `.dockerignore` 没排除 `data/synthetic`, 所以本地 stale data 也会跟着 baked。 | nice-to-have | 在 `.dockerignore` 里加一条 `data/synthetic/` 然后改成 image 内 `RUN uv run python scripts/generate_data.py`。让 build 自洽。或者反过来, 把 `data/synthetic/` un-gitignore (它是 deterministic 的 1.5MB, 不会污染历史), 然后所有人 clone 就能直接跑。两个方向选一个, 现在是混合状态。 |
| D6 | 仓库根没有 `LICENSE` 文件 (find -iname "license*" empty)。`pyproject.toml` 声明 `license = "Apache-2.0"`, GitHub 会从 metadata 识别, 但 corporate compliance / SPDX scanner 通常找 root `LICENSE` 文件。 | **should-fix** | 一行命令 `curl -sL https://www.apache.org/licenses/LICENSE-2.0.txt > LICENSE`, commit。一次性。 |

---

## E. Differentiation 叙事

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| E1 | README 三条卖点 (cross-source policy / honest eval / self-hostable) 在 leaderboard + ablation 表之后还成立。但 "Self-hostable" 那条说 "Deploy to Fly.io / HF Spaces is documented at `docs/deploy.md` (pending W7 completion)" — 实际上 Fly 已 live, deploy 不 pending 了。 | nice-to-have | 把 "(pending W7 completion)" 去掉, 链接改成直接指 `docs/deploy.md` + 在该 doc 头部加一行 "Status: Fly deploy live since 2026-05-13"。 |
| E2 | `docs/blog-outline.md` hook: "I shipped Self-Refine, DSPy, and Multi-LLM MoE in my enterprise agent. Two hurt the metric and one barely paid for itself. Here is the math."。**hook 抓人**, 数字也都对上了。但有一个内容上的小问题: outline 里没有把 Counterfactual 那一节 (governance held under perturbation) 写进 6 节 outline 的第 5 节框架里, Counterfactual 章节标题是 "Section 5 - Counterfactual robustness", 但开头 hook 只说了 3 个 frontier (Self-Refine + DSPy + MoE), 漏算 Counterfactual。 | nice-to-have | 把 working title 改成 "Three frontier techniques, three honest results — plus one robustness ablation" 之类。或者把 Counterfactual 放进 hook 但说 "and one positive: governance held"。 |
| E3 | `docs/demo-script.md` 与当前实际 API 漂移严重: (a) Scene 1 报 "$0.018, 47s", leaderboard 实际 $0.0036 + 150s, 数字夸张了一个量级; (b) 整个脚本假设 "Gradio UI at http://localhost:7860" 作为录制 surface, live deploy 没有 Gradio; (c) Scene 5 报 `git rev-parse HEAD` → `b172cb8` (那是 W1 时期的 hash, 早就 obsolete, 现在 HEAD 是 `e1b6861`); (d) demo 是按本地 Gradio 录的, 但 README 主推 live URL, 跟 portfolio narrative 不一致。 | **should-fix** | 重写一版 demo script 针对 live deploy 录制: 用 `curl -N` 在 terminal 里跑 SSE, 屏幕一半 terminal 一半浏览器开 GH Pages docs, voice-over 走 6 个场景但是录制 surface 是 SSE 流 + audit log。或者承认 Gradio 是本地选项, demo 主线就在本地录但镜头要切到 live URL 验真。否则 demo video 录出来跟 README 自相矛盾。 |
| E4 | 跟典型 LLM agent portfolio 比较, 差异点是: (1) governance 不是"agent 会拒绝", 而是 RBAC + ACL yaml + audit log 三层 + 10/10 adversarial 通过; (2) honest ablation 含 negative; (3) multi-judge consensus 解决 closed-loop。README "Differentiation" 段 line 96-100 把 (1) (2) 都喊出来了, **但 (3) multi-judge consensus 没在 README 顶部 / Differentiation 段出现**。`docs/eval-methodology.md` 有提"v4 adds multi-judge consensus", README leaderboard 段 line 17 也有一笔带过 ("v4 adds multi-judge consensus (Anthropic Haiku 4.5 + OpenAI gpt-4o-mini + DeepSeek) on every published ablation per the v4.1 honesty calibration policy")。但 Differentiation 三条 bullet 没有给它一条专门的 bullet。 | should-fix | Differentiation 段加第 4 条 bullet: "**Multi-judge consensus on every ablation**: Anthropic + OpenAI + DeepSeek 三家 LLM judge, 双 regime 把 N1 judge-pool isolation 显式表达。See `docs/sprint4_dspy_agent_ablation.md` 'Critical finding' 段 — N1 + P15 在 DSPy ablation 上直接 surface 一个 Goodhart effect。"这是你跟 90% 的同类 portfolio 真正拉开差距的点。 |

---

## F. Risk surface

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| F1 | `governance_compliance = 1.0` 五类全过, README + 表里都是 1.00。**hiring manager 会问 "你怎么知道 governance layer 没有覆盖盲区?"**。当前回答只在 w5_report.md / adversarial.json 里, README 没单独点出"失败案例 / 不覆盖范围"。 | should-fix | README leaderboard 表下面加一行: "Governance is perfect on this 30-scenario set + 10 adversarial vectors. The blind spot we know about: federation across real Slack workspace / Jira project / GitHub org permission models is **NOT** in scope; this is a *pattern demo* on synthetic identity. Real federation is v1.5 (see `docs/governance-design.md` first paragraph)."。这种"知道自己不知道什么"的话术比辩护更有信号。 |
| F2 | n=30 LLM-judge 的可信度: `docs/eval-methodology.md` 已经 head-on 处理 closed-loop (single-author calibration only), 列了 4 个 mitigation。**做得对**。但: (a) eval-methodology.md 是 "blog draft" 状态; (b) line 11 的 HotpotQA F1 0.077 数字 stale (见 B6); (c) "External reviewer slot" 那条 "If we can't get that pre-launch, the README declares 'single-author calibration only'" — 现在 README 在 leaderboard 段 line 17 写了 "LLM-judge with single-author calibration" 一句, 完成了这个 commitment。 | nice-to-have | eval-methodology.md 改成正式 doc (去掉 "blog draft" 标记); 修 line 11 数字; 在头部加一行 "Status: calibrated, single-author scope。 External reviewer review is v1.5 scope."。 |
| F3 | "No real customer data, no PII, synthetic identity" disclaimer 没有显式出现在 README 第一屏。`docs/governance-design.md` 第一段写了 "pattern demo on synthetic identity, not Okta/Azure AD"。README "Differentiation" 第一 bullet 也说 "*pattern demo* on synthetic identity"。但**缺一行最顶上的合规免责**, 例如靠近 leaderboard 表上方。 | should-fix | README hero 区 (line 5-7) 加一行: "All data is synthetic and byte-deterministic from `seed=42` — no real customer data, no PII。 Governance is a pattern demo over synthetic identity, not Okta/Azure AD federation。"。一行解决三个问题 (PII / 合规 / scope)。 |
| F4 | License: `pyproject.toml` declares Apache-2.0, root 无 `LICENSE` 文件 (见 D6)。Attribution: `docs/index.md` line 33 有 "built solo with Claude Code + Codex CLI pair-programming; design decisions, architecture, and trade-offs are mine, code execution is paired"。**这条做得非常好** (NL 文化非常看重诚实标注 AI assist), 但 **README 没有同样的话**, 只有 docs index 有。hiring manager 不一定点进 GH Pages, 大概率只看 GitHub README。 | **should-fix** | README 末尾或 "Differentiation" 段下方加一段 "Attribution" / "Build process" 块, 复用 `docs/index.md` line 33 那一行原文。透明度是 portfolio 的资产。 |

---

## Punch list (ROI 排序)

打勾即修, 跳过即接受。优先级是 P0 (blocker) > P1 (should-fix) > P2 (nice-to-have)。

- [ ] **P0** 加一个 `GET /` 落地页 (HTML 或 302 → docs site), 解决 fly.dev root URL 显示 404 JSON 的问题。10 分钟。
- [ ] **P1** 加 `LICENSE` 文件 Apache-2.0 至 repo root。1 行 curl + 1 commit。
- [ ] **P1** 修 `docs/eval-methodology.md` line 11: F1 从 0.077 改成 "lifted from 0.077 (naive) to 0.29 (llm-answer)"。1 行。
- [ ] **P1** README hero 区加 synthetic-data + scope disclaimer 一行 (F3)。
- [ ] **P1** README "Differentiation" 段加第 4 条 bullet "multi-judge consensus + Goodhart-aware" (E4)。
- [ ] **P1** README leaderboard 表 DSPy 行 Verdict 改成 "+0.05 (2-judge) → -0.03 (3-judge), Goodhart reversal" (C6)。
- [ ] **P1** README 底部加一段 "Built with Claude Code + Codex CLI pair-programming" attribution (F4)。
- [ ] **P1** README leaderboard 下加一行 "governance 1.00 on this set; federation is v1.5 scope" (F1)。
- [ ] **P1** 重录 / 重写 `docs/demo-script.md`, 对齐 live deploy (SSE 而非 Gradio, 真实 timing / cost, 当前 HEAD hash)。最贵但 ROI 最高: 这是 portfolio 的"动作戏"。
- [ ] **P1** Quickstart 加一行 "generate synthetic data before docker compose up" (D3)。
- [ ] **P2** `docs/a3_semantic_cache.md` 把 3 个 TBD 改成 "Not measured in v4 (v1.5)"。
- [ ] **P2** `docs/blog-outline.md` 填掉 `{INSERT_NUMBERS_HERE}` (用 `sprint4_dspy_agent_ablation.md` 的真实数字)。
- [ ] **P2** `user_role` 改 `Literal` 或在 description 里说明 fallback (A5d)。
- [ ] **P2** `docs/eval-methodology.md` 摘掉 "blog draft" 标签, 升正式 doc (F2)。
- [ ] **P2** `.dockerignore` 加 `data/synthetic/` + Dockerfile `RUN generate_data` (或反之 un-gitignore data/synthetic), 让 docker build 自洽 (D5)。
- [ ] **P2** `docs/deploy.md` 去掉 "(pending W7 completion)" + 加 "Status: live since 2026-05-13" (E1)。
- [ ] **P2** `docs/blog-outline.md` working title 把 Counterfactual 算进去 (E2)。
- [ ] **P2** `/users` endpoint 加 `synthetic_data: true` 字段或 root 落地页里点明 (A7)。

如果只修 P0 + 一半 P1 (最上面 5 条), portfolio 从 78/100 拉到 88/100, 大概 3 小时工作量。

---

## What you cannot fault

不光列短板, 也列做得好的地方, 给 Fei 一个 confidence 基线。

- **Live deploy 真的活着**: /health 200 OK 60ms, SSE 5 节点全部触发, citation 正确 grounded, RBAC 拒绝逻辑 produce a coherent refusal answer instead of crashing。warm-machine 解决 cold-start 设计正确。
- **DSPy Goodhart 双 regime 发现是 staff-engineer-级洞察**, 而且写得很清楚: "DSPy optimized against a metric that excluded the agent's own model class, and adding it back flips the sign of the headline delta. This is exactly the failure mode that v4.1 N1+P15 were designed to surface."。**这一段单拎出来发 blog 就值这个 portfolio 一半的分量**。
- **MoE n=10 noise floor caveat 写在 doc 里, 而非藏起来**。Pareto 分析 + 投入产出比 + v1.5 follow-up 路径都列了。
- **Counterfactual 三个 perturbation 真跑了, governance 真的 1.00, doc_deletion 真的导致 ac → 0.20 但 cite_id_grounded 没崩 (agent 不幻觉)**。这是 robustness 真有研究, 不是 PR-talk。
- **Self-Refine `Footnote A` 自己披露 cost ledger contamination + 指向 fix commit `e332937`**。这种自我披露在 portfolio 里是稀缺品。
- **101/101 pytest pass**, 27 秒, 含 retrieval 之外的所有路径。
- **没有秘密入 git history**, `.env` gitignored, `.env.example` 干净。
- **Adversarial 10/10 blocked**, prompt-fence + RBAC 双层。
- **Input validation 三道线**: 404 (user not found) + 422 (string too long) + governance refusal (role 越权)。三种错都返回 clean JSON, 没堆栈泄漏。
- **mkdocs site 真在线**, GH Pages 200 OK, material theme + navigation tabs + 35 doc 都 indexed。
- **Apache-2.0 license declare 在 pyproject.toml** (只是缺 root LICENSE 文件)。
- **closed-loop risk 在 eval-methodology.md 第一段 head-on 处理**, 而不是 hiding。

---

## Recruiter pitch (LinkedIn DM 风格, 5 句)

假装 Fei 在给一个 NL staff engineer DM 推荐这个 project, 5 句话, 30 秒说清楚, 5 分钟值得看:

> "I built an enterprise knowledge agent over 6 SaaS surfaces with a yaml-based cross-source RBAC + audit log, self-authored 30-scenario eval, multi-LLM-judge consensus, and live-on-Fly + Langfuse tracing — `https://enterprise-knowledge-agent.fly.dev/health`. The differentiator is honesty: 4 frontier-technique ablations all ship with with-vs-without tables, including 3 negatives — Self-Refine is -0.08, DSPy compilation produces a Goodhart-effect where 2-judge says +0.05 but 3-judge says -0.03 (exactly what the judge-pool-isolation policy was designed to surface), and MoE Sonnet 4.6 lift is within the n=10 noise floor. The one positive: counterfactual perturbations hold governance compliance at 1.00 across entity-swap / noise-injection / doc-deletion. All synthetic data, byte-deterministic from seed=42, 101/101 tests, Apache-2.0, ~$0.0036 / query at DeepSeek list price. If you have 5 minutes, the DSPy Goodhart section in `docs/sprint4_dspy_agent_ablation.md` is the one I'd point at."

---

## Audit metadata

- 审计 commit: `e1b6861 docs: v4 final polish -- live URL, deploy DONE, blog+demo remain`
- 审计耗时: ~25 minutes, 实验 spend < $0.05 (5 次 curl 到 live API)
- 工具: curl (live), pytest (local), grep + git log (静态)
- 限制: `gh` 不可用 → GH Actions runs 推断而非确认; 看不到 Langfuse trace dashboard → 只能审代码逻辑
