# Prism 研究系统 — 详细设计文档

> 版本：v1.0 · 2026-05-08

---

## 1. 系统定位与设计哲学

Prism 是一个 **LLM 驱动的结构化投资研究系统**。用户在对话窗口指挥 Claude，Claude 按照 markdown 工作流逐步完成行业/竞技场/公司的深度研究，最终产出 8 份标准报告，可在 `/prism` Web 页面查看。

### 1.1 核心设计原则

**原则一：LLM 在对话里做，Python 只管读写**

所有分析、判断、内容生成都在 Claude 对话窗口发生。Python 脚本仅做文件 I/O 和 YAML 解析，绝不调用任何 API 或 LLM。这样：
- 用户完全掌控推理过程
- 脚本可测试、可审计
- 出错时不会隐藏在黑盒里

**原则二：工作流是给 Claude 读的说明书**

`prism/workflows/` 下的 markdown 文件不是代码，不是脚本，而是 Claude 在对话里逐步执行的操作手册。每个工作流定义「做什么、按什么顺序、产出写哪里」。

**原则三：Web 只读，数据在文件系统**

Web 界面（`/prism`）是研究状态的只读视图。数据真正的存储是 `prism/topics/{slug}/` 下的 YAML + markdown 文件。不需要数据库，不需要迁移，文件可以用 git 管理。

**原则四：单向数据流**

```
用户对话 → Claude 执行工作流 → 写文件 → Web 自动反映
```

没有反向路径。Web 不能触发写操作，Python 脚本不能触发 LLM 调用。

---

## 2. 系统架构

### 2.1 三层分离

```
┌─────────────────────────────────────────────┐
│         Layer 3: Web 视图层                   │
│   app/routes/prism.py                        │
│   app/templates/prism/{index,detail,output}  │
│   → 只读，读 topic.yaml + outputs/*.md        │
└────────────────────┬────────────────────────┘
                     │ 读
┌────────────────────▼────────────────────────┐
│         Layer 2: 数据层（文件系统）            │
│   prism/topics/{slug}/                       │
│   ├── topic.yaml                             │
│   ├── manifest.yaml                          │
│   ├── roadmap.yaml                           │
│   └── outputs/*.md                           │
└────────┬───────────────────────┬────────────┘
         │ 写（Claude 用脚本）   │ 读（Web 路由）
┌────────▼───────────┐  ┌───────▼────────────┐
│   Layer 1a: CRUD   │  │   Layer 1b: 工作流  │
│   prism/scripts/   │  │   prism/workflows/  │
│   topic.py         │  │   00～07, 99         │
│   manifest.py      │  │   → Claude 读并执行  │
│   outputs.py       │  └────────────────────┘
└────────────────────┘
```

### 2.2 目录结构

```
prism/
├── __init__.py
├── scripts/                    # Python CRUD（零 LLM）
│   ├── __init__.py
│   ├── topic.py                # topic.yaml 的增删改查
│   ├── manifest.py             # manifest.yaml 的资料管理
│   └── outputs.py              # 产出文件的列表与读取
├── workflows/                  # Claude 执行的操作手册
│   ├── 00-research-topic.md    # 开启新研究主题
│   ├── 01-build-roadmap.md     # 制定研究路线图
│   ├── 02-gather-materials.md  # 登记和处理资料
│   ├── 03-extract-findings.md  # 从资料提炼发现
│   ├── 04-synthesize/          # 生成 8 份标准产出
│   │   ├── _shared.md          # 前置检查规范
│   │   ├── 01-panorama.md      # 商业全景
│   │   ├── 02-cycle.md         # 周期定位
│   │   ├── 03-narrative.md     # 叙事生态
│   │   ├── 04-expectations.md  # 隐含预期
│   │   ├── 05-mirrors.md       # 历史镜子
│   │   ├── 06-risks.md         # 风险盲点
│   │   ├── 07-decision-kit.md  # 决策工具箱
│   │   └── 08-feed.md          # 持续跟踪
│   ├── 05-critic-review.md     # 批评者评审（Steelman）
│   ├── 06-daily-monitor.md     # 日常监控
│   ├── 07-drilldown.md         # 专题深挖
│   └── 99-decision-record.md   # 决策记录
├── templates/                  # YAML 模板（供 Claude 填充）
│   ├── topic.yaml.tmpl
│   ├── roadmap.yaml.tmpl
│   └── manifest.yaml.tmpl
├── prompts/                    # 写作风格规范
│   ├── analyst_voice.md        # 分析师笔法
│   └── output_quality_rubric.md # 质量自查清单
├── topics/                     # 研究主题数据（用户数据）
│   └── {slug}/
│       ├── topic.yaml
│       ├── manifest.yaml
│       ├── roadmap.yaml
│       └── outputs/
│           ├── 01_business_panorama.md
│           ├── 02_cycle_positioning.md
│           ├── 03_narrative_ecology.md
│           ├── 04_implied_expectations.md
│           ├── 05_historical_mirrors.md
│           ├── 06_risk_blindspots.md
│           ├── 07_decision_kit.md
│           └── 08_living_feed.md
└── inbox/
    ├── auto/                   # 脚本自动下载的资料
    └── manual/                 # 用户手动放入的资料

app/
├── routes/prism.py             # FastAPI 路由
└── templates/prism/
    ├── index.html              # /prism — 所有主题列表
    ├── detail.html             # /prism/{slug} — 主题仪表盘
    └── output.html             # /prism/{slug}/output/{key} — 产出渲染

.claude/skills/prism/
└── SKILL.md                    # Skill 路由表，触发关键词→工作流映射
```

---

## 3. 数据模型

### 3.1 topic.yaml

每个研究主题的单一事实来源（Single Source of Truth）。

```yaml
slug: cn-pet-industry              # 唯一标识符，全小写连字符
display_name: 中国宠物行业          # 展示名
type: industry                     # industry | arena | company
created: "2026-05-08T10:00:00Z"   # 创建时间（ISO 8601）
status: active                     # active | paused | archived
stage: 03-extracting               # 当前所处阶段（见下方阶段表）
scope:
  geo: CN                          # 地理范围
  question: 中国宠物行业哪些细分赛道值得投资  # 核心研究问题
  depth: deep                      # quick | standard | deep
outputs_state:                     # 8 份产出的状态
  01_business_panorama:
    version: 2                     # 版本号（每次生成+1）
    last_updated: "2026-05-08T11:00:00Z"
    status: fresh                  # pending | fresh | stale
  02_cycle_positioning:
    version: 0
    last_updated: null
    status: pending
  # ... 其余 6 份同格式
next_actions:                      # Claude 下一步要做什么
  - "收集 Tier 1 资料后运行 workflow 02-gather-materials"
  - "有 3 份以上资料后运行 workflow 03-extract-findings"
user_todos:                        # 需要用户做的事情
  - "下载中信证券 2024 年宠物行业深度报告"
  - "获取头部公司 2023 年报"
monitoring:
  enabled: false                   # 是否开启日常监控
  cadence: daily                   # 监控频率
```

**阶段（stage）状态机：**

```
00-init → 01-roadmap-pending → 02-gathering → 03-extracting
       → 04-synthesizing → 05-reviewing → 06-monitoring
```

**产出状态含义：**
- `pending`：尚未生成
- `fresh`：已生成，资料没有更新，视为最新
- `stale`：有新资料入库后自动变为 stale，需要重新生成

### 3.2 manifest.yaml

资料清单，记录每份研究材料的元信息。

```yaml
slug: cn-pet-industry
materials:
  - id: mat-a1b2c3                  # 6位随机hex，由 add_material() 生成
    filename: citic-pet-2024.pdf    # 原始文件名
    source_type: sell-side-note     # 来源类型（见下）
    notes: 中信证券 2024 年宠物深度
    added_at: "2026-05-08T10:30:00Z"
    processed: true                 # 是否已经提炼 findings
  - id: mat-d4e5f6
    filename: yx-pet-annual-2023.md
    source_type: annual-report
    notes: 中宠股份 2023 年报
    added_at: "2026-05-08T11:00:00Z"
    processed: false
```

**source_type 枚举（开放词汇）：**
- `sell-side-note` — 卖方研报
- `annual-report` — 公司年报/季报
- `industry-data` — 行业数据/白皮书
- `policy-doc` — 政策文件
- `news-summary` — 新闻摘要
- `expert-interview` — 专家访谈
- `custom` — 其他

### 3.3 产出文件（outputs/*.md）

每份产出是带 YAML frontmatter 的 markdown 文件：

```markdown
---
slug: cn-pet-industry
output_key: 01_business_panorama
version: 2
generated: "2026-05-08T11:30:00Z"
---

# 商业全景：中国宠物行业

> 生成于 2026-05-08，训练知识占比约 60%，资料更新截至 2024-12

## 行业定义与边界
...

## 信息来源
- 训练知识（约 60%）
- mat-a1b2c3: citic-pet-2024.pdf
- mat-d4e5f6: yx-pet-annual-2023.md
```

---

## 4. 工作流系统

### 4.1 工作流目录

| 文件 | 触发条件 | 产出 |
|------|----------|------|
| `00-research-topic.md` | 「研究 X」 | topic.yaml + manifest.yaml |
| `01-build-roadmap.md` | stage=01-roadmap-pending | roadmap.yaml |
| `02-gather-materials.md` | 有新资料要登记 | manifest.yaml 更新 |
| `03-extract-findings.md` | 有未处理资料 | findings_*.md |
| `04-synthesize/01～08` | 「生成产出 X」 | 对应 outputs/*.md |
| `05-critic-review.md` | 「评审 {slug}」 | 对话输出 + next_actions |
| `06-daily-monitor.md` | 「监控 {slug}」 | living_feed 追加 |
| `07-drilldown.md` | 「深挖 {slug} 的问题」 | 对话输出 |
| `99-decision-record.md` | 「记录决策 {slug}」 | decision_YYYYMMDD.md |

### 4.2 Prism Skill 路由

当用户说出触发词，Prism skill 负责路由到正确的工作流：

```
用户输入 → SKILL.md 匹配触发词 → 读取对应 workflow → Claude 逐步执行
```

路由逻辑（从 SKILL.md）：

| 用户说 | 执行 |
|--------|------|
| 「研究 X」/ 「开始研究 X」 | workflow 00 |
| 「prism 推进 {slug}」/ 「继续研究 {slug}」 | 读 topic.yaml 判断 stage，跳转对应 workflow |
| 「生成产出 {output}」/ 「更新 {slug} 的 {output}」 | 对应 04-synthesize/{N}-*.md |
| 「评审 {slug}」 | workflow 05 |
| 「监控 {slug}」 | workflow 06 |
| 「深挖 {slug} 的 {问题}」 | workflow 07 |
| 「记录决策 {slug}」 | workflow 99 |
| 「查看 {slug} 进度」 | 直接读 topic.yaml 输出状态表格 |

### 4.3 8 份标准产出

| # | key | 中文名 | 定位 | 训练知识占比 |
|---|-----|--------|------|-------------|
| 01 | `01_business_panorama` | 商业全景 | 行业基础认知地图 | ~60% |
| 02 | `02_cycle_positioning` | 周期定位 | 当前在周期哪个位置 | ~40% |
| 03 | `03_narrative_ecology` | 叙事生态 | 市场上流传哪些故事 | ~30% |
| 04 | `04_implied_expectations` | 隐含预期 | 当前估值隐含了什么假设 | ~20% |
| 05 | `05_historical_mirrors` | 历史镜子 | 历史类比案例 | ~70% |
| 06 | `06_risk_blindspots` | 风险盲点 | 市场可能低估的风险 | ~50% |
| 07 | `07_decision_kit` | 决策工具箱 | Kill criteria + signposts | ~30% |
| 08 | `08_living_feed` | 持续跟踪 | 流动追加的观察记录 | 0%（纯资料） |

---

## 5. Python Scripts API

### 5.1 topic.py

```python
from prism.scripts.topic import (
    create_topic,        # 创建新 topic（FileExistsError if slug exists）
    read_topic,          # 读取 topic（FileNotFoundError if missing）
    update_topic,        # 批量更新字段
    set_stage,           # 更新 stage
    set_output_status,   # 更新单个产出的状态和版本
    set_next_actions,    # 更新 next_actions 列表
    set_user_todos,      # 更新 user_todos 列表
    list_topics,         # 列出所有 topic（按创建时间降序）
)
```

**create_topic 签名：**
```python
def create_topic(
    slug: str,
    display_name: str,
    topic_type: str,        # 'industry' | 'arena' | 'company'
    question: str,
    geo: str,               # 'CN' | 'US' | 'GLOBAL'
    depth: str,             # 'quick' | 'standard' | 'deep'
) -> Path:                  # 返回 topic.yaml 路径
```

**set_output_status 签名：**
```python
def set_output_status(
    slug: str,
    output_key: str,        # '01_business_panorama' 等
    status: str,            # 'pending' | 'fresh' | 'stale'
    version: int | None,    # None = 不更新版本号
) -> None:
```

### 5.2 manifest.py

```python
from prism.scripts.manifest import (
    create_manifest,     # 初始化空 manifest
    read_manifest,       # 读取（FileNotFoundError if missing）
    add_material,        # 添加一份资料，返回 mat_id
    mark_processed,      # 标记资料为已处理
    list_unprocessed,    # 列出未处理资料
    material_count,      # 返回 {"total": N, "processed": N, "unprocessed": N}
)
```

**add_material 签名：**
```python
def add_material(
    slug: str,
    filename: str,
    source_type: str,
    notes: str = "",
) -> str:               # 返回 mat_id，格式 "mat-{6hex}"
```

### 5.3 outputs.py

```python
from prism.scripts.outputs import (
    list_outputs,        # 列出 8 份产出的状态（含 file_exists 字段）
    read_output_html,    # 读取产出 markdown 并转为 HTML（FileNotFoundError if missing）
)
```

**list_outputs 返回格式：**
```python
[
    {
        "key": "01_business_panorama",
        "label": "商业全景",
        "status": "fresh",          # 来自 topic.yaml
        "version": 2,
        "last_updated": "2026-05-08T11:00:00Z",
        "file_exists": True,        # 实际文件是否存在
    },
    ...
]
```

---

## 6. Web 路由

| 路由 | 描述 | 模板 |
|------|------|------|
| `GET /prism` | 所有主题列表，含产出完成度 | `prism/index.html` |
| `GET /prism/{slug}` | 单个主题仪表盘（topic.yaml + 8产出状态） | `prism/detail.html` |
| `GET /prism/{slug}/output/{output_key}` | 渲染单份产出 markdown 为 HTML | `prism/output.html` |

**错误处理：**
- slug 不存在 → 404
- output_key 对应文件不存在 → 404（提示「尚未生成」）

**模板变量（detail.html）：**
```python
{
    "topic": dict,          # topic.yaml 全量
    "outputs": list[dict],  # list_outputs() 返回值
    "request": Request,
}
```

---

## 7. 质量保障体系

### 7.1 产出前置检查（_shared.md）

每份产出生成前，Claude 必须检查：
- 已处理资料 ≥ 3 份（否则停止并提示）
- topic.yaml 存在且 stage 正常
- 记录训练知识 vs 资料的来源比例

### 7.2 分析师笔法（analyst_voice.md）

写作规范：
- 先结论后论据
- 有数字就用数字，不用「较高」「较快」等模糊描述
- 区分 `[数据]` 和 `[判断]`
- 禁止无信息量的描述（「错综复杂」「千丝万缕」）
- 禁止无来源的宏观数据

### 7.3 质量 Rubric（output_quality_rubric.md）

每份产出完成后必须自检：

| 检查项 | 通过标准 |
|--------|----------|
| 有具体数字 | 至少 3 处具体数据 |
| 多空兼顾 | 乐观 + 悲观视角都有 |
| 有「哪里可能是错的」 | 明确指出判断风险 |
| 来源透明 | 训练知识 vs 资料有区分 |
| 结论在前 | 核心判断不埋在末尾 |

---

## 8. 测试覆盖

### 8.1 脚本测试（tests/test_prism_scripts.py）

- 18 个测试，覆盖 topic.py / manifest.py / outputs.py 全部公开函数
- 使用 `tmp_path` fixture + `monkeypatch` 隔离 `_PRISM_ROOT`，不污染生产数据
- 测试异常路径：FileExistsError / FileNotFoundError

### 8.2 路由测试（tests/test_prism_routes.py）

- 5 个 smoke test，覆盖 3 条路由的 200/404 场景
- 使用 `TestClient` + 完整 fixture（创建 fixture topic + 拷贝模板）

---

## 9. 扩展点

### 9.1 添加新的产出类型

1. 在 `prism/scripts/topic.py` 的 `_OUTPUT_KEYS` 列表添加新 key
2. 在 `prism/scripts/outputs.py` 的 `_OUTPUT_KEYS_LABELS` 添加对应中文标签
3. 在 `prism/workflows/04-synthesize/` 添加新 workflow 文件
4. 更新 `SKILL.md` 的触发词路由表

### 9.2 添加新的 source_type

`source_type` 是开放词汇，直接在 `add_material()` 调用时传入即可，不需要修改代码。

### 9.3 监控自动化

`topic.yaml` 的 `monitoring.enabled=true` + `cadence` 字段预留了监控接入点。未来可通过 cron 触发 workflow 06。
