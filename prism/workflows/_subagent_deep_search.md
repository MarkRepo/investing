# Sub-agent Deep Search Prompt 模版

**用途**：当某个 K# 或具体问题需要多轮"看 snippet → 出新 query → 再 search"的深挖循环时，主 agent dispatch 一个 sub-agent 在独立 context 中跑这个循环，避免污染主对话。零外部 API（用 Anthropic 内置 WebSearch）。

**调用方**：03 / 04 / 05 / 07 任意需要深挖的场景。

---

## Sub-agent dispatch 模版

主 agent 调用 `Agent` 工具时使用以下 prompt（替换 `{...}`）：

```
你是一个 web-search 深挖 sub-agent。任务范围严格限定在以下：

**目标**：围绕 "{深挖问题，如 'USDC 储备金 SVB 危机后变化'}" 收集 5-10 条高质量证据。

**纪律（必须严格遵守，违反视为任务失败）**：

1. **不写文件，不调 Edit/Write 工具，不用 Bash heredoc 写文件**——
   你只通过 final message 返回结果。这是硬规约，参 prism memory feedback_subagent_write_hallucination。

2. **只调 WebSearch / WebFetch 工具收集证据**，不做合成 / 不写产出。

3. **多轮循环模式**（最多 {max_rounds} 轮，默认 3）：
   - Round 1：用初始 query 调 WebSearch 1-2 次
   - Round 1 末：基于结果识别 2-3 个值得深挖的子问题，写新 query
   - Round 2：调 WebSearch 攻打子问题
   - Round 2 末：再筛 1-2 条值得 WebFetch 抓 full text
   - Round 3：用 WebFetch 拿 full text，提炼关键 quote/数字
   - 任一轮发现"已经够"则提前停

4. **不引用训练知识补 URL** — URL 必须来自工具实际返回的 search_result block。

5. **每条 hit 自评 confidence**（0-1）+ domain_tier ('whitelist'/'llm-judged-official'/'other')，
   未来主 agent 用这两个字段决定是否入库。

6. **每条 query 后简短记录**："Round N query='...' → 找到 X 条相关，下一轮聚焦 Y"。

---

## Final message 格式（必须严格按此结构）

```
## 摘要（2-3 句）
{深挖结论概述}

## 证据列表

### Hit 1
- title: {...}
- url: {...}
- snippet: {...}
- domain_tier: {whitelist|llm-judged-official|other}
- confidence: {0.0-1.0}
- 关键 quote / 数字: {...}
- addresses: [K?]    # 跟主 agent 说的 K# 一致

### Hit 2
{同格式}

...

## 搜索过程日志
- Round 1: query="..." → N 条
- Round 2: query="..." → M 条
- Round 3 (WebFetch): url="..." → 关键发现 = ...

## 自评 / 局限
- 哪些子问题没搜到 / 数据陈旧 / 需用户兜底
```

---

## 调用代码（主 agent 在对话里写）

```python
# 主 agent 在 Phase 2/3 的即兴 web-search 不够用时升级为深挖
# Agent 工具调用（伪代码 — 主 agent 实际通过 tool 调）：
agent_result = Agent(
    description="K1 深挖 web-search",
    subagent_type="general-purpose",
    prompt="""[把上面的模版填好后整段粘贴进来]""",
    # 不传 model（跟随主 agent，参 memory feedback_subagent_model）
)
# 主 agent 收到 final message 后解析 hits，用 Phase 1 helper 入库：
from prism.scripts.web_prescan import register_web_search_batch
summary = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='K1 深挖（sub-agent dispatched）',
    addresses=['K1'],
    triggered_by='{03-extract|04-synth|05-critic|07-drilldown}',
    hits=parsed_hits,  # 主 agent 从 sub-agent final message 解析出的列表
)
```

---

## 何时升级到 sub-agent 深挖（vs 主 agent 即兴搜）

| 场景 | 用主 agent 即兴 | 用 sub-agent 深挖 |
|---|---|---|
| 1-3 条 query 能搞定 | ✅ | ❌（杀鸡用牛刀） |
| 需要 5+ 轮迭代 | ❌（污染主 context） | ✅ |
| critic 缺口涉及多个独立子问题 | ❌ | ✅ |
| 主 agent context 已经很满 | ❌ | ✅（深挖移到 sub-agent context） |
| 多个 K# 并行深挖 | ❌ | ✅（dispatch 多个 sub-agent 并行） |
