# 建子 topic stub + 继承父 thesis_v0（通用工具规范）

> **工具规范，非独立产出步骤。** industry→arena（`_arena_select_spec.md` 环⑥）与 arena→company（`_peer_matrix_spec.md` 环⑥）「为深挖/深研档建 stub + 继承父 thesis_v0」同构，收敛到此处**逐字执行**。由两 spec 的环⑥ + type 卡 industry/arena 的 §sidecar **逐字引用**（查过程，不照搬结构）。
>
> **两处唯一差异（调用处指定参数）：**
> - `{child_type}`：`arena`（industry 选拔调）/ `company`（arena 选拔调）。
> - `{ticker}`：**仅 `company` 传**（`arena` 删掉 create_topic 里的 `ticker=` 行）。
> - **收窄视角**：`arena` = 公司/路线/客户；`company` = 本公司。
> - **检索词口径**：`arena` 如 `['ADC','出海 BD','双抗']`；`company` = 公司名/核心产品/赛道。
> - **强度基准**：均按**父级强度 -1** 起估（继承可信度低于亲自验证）。

---

## Step A：为深挖/深研档创建 stub topic

对每个深挖/深研档 {child_type}：

```bash
python3 -c "
from prism.scripts.topic import create_topic, read_topic
parent = read_topic('{slug}', '{variant}')
geo = parent.get('scope', {}).get('geo', 'cn')  # 从父 topic 继承 geo
create_topic(
    slug='{geo}-{child_slug}',
    display_name='{child_display_name}',
    topic_type='{child_type}',                 # arena（industry 选拔）/ company（arena 选拔）
    question='{child_question}',
    geo=geo,
    depth='deep',
    variant='{variant}',
    parent_topic='{slug}',
    ticker='{ticker}',                         # ⬅ 仅 company 传；arena 删掉本行
    short_name='{child_short_name}',           # 简称（dashboard 显示用）
    search_terms=['{词1}', '{词2}', '{词3}'],  # 见下 ⚠️：question >25 字必填
)
"
```

> ⚠️ **必传 `search_terms`（否则 create_topic 直接 raise）**：当 `question` >25 字时 create_topic 强制要求 `search_terms`（避免脚本自行从长问题里乱拆关键词）。arena / company stub 问题几乎都 >25 字 → **本步漏传必崩**。规则：`list[str]`，每项 ≤15 字，至少 1 个非空项。按上方「检索词口径」手挑 3-5 个，别整句塞进去。

## Step B：为 stub 写入继承自父 thesis 的 thesis_v0.md

create_topic 完成后，**立即**为 stub 写 thesis_v0.md，省去用户后续推进时再走 00-research-topic 的麻烦。

1. 读父 topic 当前 thesis：

```bash
python3 -c "
from prism.scripts.outputs import extract_killer_questions
from prism.scripts.topic import read_topic
parent = read_topic('{slug}', '{variant}')
cur_v = (parent.get('thesis') or {}).get('current_version', 0)
ks = extract_killer_questions('{slug}', '{variant}', cur_v)
print('父级 K# 数量:', len(ks))
for k in ks: print(' -', k[:80])
"
```

也读 `prism/topics/{slug}/{variant}/thesis_v{cur_v}.md`（**variant 根下，非 outputs/**）全文用作 narrowing 参考。**child=company 额外**读该公司在决策链④矩阵中的「入选理由 / 预期 thesis」段落作为 narrowing 输入。

2. 在对话里**收窄到子视角**：从父 K# 中挑出与该 {child_type} 直接相关的 2-4 条，重写措辞使其聚焦本 {child_type}（按上方「收窄视角」；company 例：「行业能否跑出 OEM 模式」收窄为「{公司}能否拿下 OEM 客户份额」）；如父 K# 不足，补 1-2 条 {child_type} 专属待验证假设（company 侧重管理层兑现 / 单一大客户依赖 / 估值锚）。

3. 按 thesis_v0 **四段式**（① 核心 thesis + 强度评分 / ② 支持理由 / ③ 反方观点 / ④ K1-K5；**不单列 V# 验证项**，与 workflow 00 Step 5.0 一致）写入 stub 的 `prism/topics/{geo}-{child_slug}/{variant}/thesis_v0.md`（**variant 根下，非 outputs/** —— 与 decomposition_v{N} 同级；错位到 outputs/ 会让 extract_killer_questions/5.7 闸门/web 全部读不到）。**核心 thesis ≤120 字**，强度先按**父级强度 -1** 起估。每条 K# 末尾标注「(继承自父 K#)」或「(新增)」。

4. 落入 stub 的 topic.yaml：

```bash
python3 -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{geo}-{child_slug}',
    variant='{variant}',
    version=0,
    summary='{≤120字 子视角 thesis}',
    stage_set_at='00-init-from-parent',
)
"
```

> 跳过条件：父 thesis 完全不可拆分到子维度（极少见）。此时 stub 仍创建，但不写 thesis_v0，由用户日后手动走 00-research-topic。
