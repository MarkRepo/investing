---
name: Investment Lens — Stage 3 write/edit layer
description: Interactive editing plan — narrative editing, claim writing, decision gates, review flags from lens pages
type: plan
status: pending
---

## 目标

将 Stage 1+2 的只读决策视图升级为可交互的编辑界面，用户可以在浏览 lens 的同时撰写/修改 narrative、创建/更新 claims、填写 stage gate 评估，不脱离当前视图上下文。

## 核心能力

### 1. 内联 narrative 编辑

- 每个 section 的 narrative excerpts 区域支持就地展开编辑
- 编辑区预填现有 narrative 内容（如存在），否则空白
- 保存触发 `POST /lens/{scope}/{ref}/narrative` 写入 archive narrative 文件
- 使用 Phase 3A/3B/3C 已建立的 narrative CLI 写入路径，HTTP 层只做薄路由转发

### 2. Claim 管理

- 每个 section 的 claims 列表支持三种操作：
  - **创建**: 在 lens 页内填写 claim_text / claim_type / confidence / dimension_hint，生成 claim_id
  - **更新**: 修改 claim_text / confidence，记录 edit history
  - **退役**: 将 status 置为 `retracted`（不物理删除）
- 通过 `POST /lens/{scope}/{ref}/claims` 和 `PUT /lens/{scope}/{ref}/claims/{claim_id}` 操作

### 3. Stage gate 交互

- industry/arena/company 的 stage_gates field 显示当前所有 gate
- 支持 toggle `crossed` 状态和追加 `what_would_cross_it` 条目
- 通过 `PUT /lens/{scope}/{ref}/stage-gates/{gate_index}` 操作

### 4. Review flags

- 每个 section 显示 auto_review_flags（来自现有 narrative 质量检查）
- 提供"标记已处理"操作，将 flag 状态从 `open` → `addressed`

## 实现顺序

1. **Phase 3A** — arena 写层（最具体，可验证）
2. **Phase 3B** — company 写层
3. **Phase 3C** — industry 写层

每层完成后做端到端验证（写 → 保存 → 刷新页面 → 确认内容持久化）。

## 路由设计

| Method | Route | 说明 |
|--------|-------|------|
| POST | `/lens/{scope}/{ref}/narrative` | 写/更新单个维度 narrative |
| POST | `/lens/{scope}/{ref}/claims` | 创建 claim |
| PUT | `/lens/{scope}/{ref}/claims/{claim_id}` | 更新 claim |
| PUT | `/lens/{scope}/{ref}/stage-gates/{gate_index}` | 更新 stage gate |
| POST | `/lens/{scope}/{ref}/review-flags/{flag_id}/address` | 标记 flag 已处理 |

## 安全约束

- narrative 写入走 `safe_write_narrative()` 确保原子写入（先写 tmp 再 rename）
- claims 写入走 ClaimRegistry 的事务性方法
- stage gate 更新在 bundle JSON 上做 in-place 修改前先备份原文件

## 不做的

- 实时协作/多人编辑冲突合并（单人使用场景）
- diff/revert 功能（git 层面解决）
- 权限/认证（本地单用户）
