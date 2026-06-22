# Sub-agent Fetch Material Prompt 模版

**用途**：当 web-search 拿到一个公开财报 / 公告 PDF 的 URL 后，主 agent dispatch sub-agent 跑下载脚本，让主 agent 自己不必离开当前任务流。

## 硬规约（不可省）

1. **本 subagent 内所有 web 检索必须走 adapter**（即 `python3 -m prism.scripts.web_search`），
   禁止调 `mcp__tavily__*` / `mcp__exa__*` / `mcp__serper__*` / Anthropic WebSearch tool。
   理由：MCP 调用每次进 turn 预算，多 query 撞 60min 硬墙；adapter 一次 Bash 把多 query 串
   起来跑（`search` + 多 `--triggered-by`），且自带 KeyPool 轮换 + 失败 fallback。
   （参 [[feedback_subagent_bulk_synthesis]] / [[feedback_subagent_write_hallucination]]）
2. 退出码 40（all_exhausted）时本 subagent **直接 raise 给主 agent**，
   不要自己 fallback 到 WebSearch tool —— 双向 fallback 由主 agent 编排。
3. sidecar 入库一律 `--output sidecar` 模式；不要把 hits stdout 二次解析后再手工 register。

详见 [[_web_search_routing]]。

**调用 prompt 模版**：

```
你是 prism 系统的 fetch-material sub-agent。任务范围：

**目标**：下载 {标的} 的 {资料类型} 到 prism/topics/{slug}/inbox/。

**可用工具**：
- Bash：跑 fetch_report_prism / curl / wget 等
- Read：检查下载文件是否完整（看大小）

**纪律**：
1. 不写其他文件、不改 manifest（manifest 由主 agent 走 workflow 02 处理）
2. 下载完成后用 Bash `ls -la` 验证文件存在 + 大小 > 50KB（小于即视为失败）
3. 失败时 final message 必须写明原因（404? 鉴权? URL 错？）

**调用例**：

```bash
python3 -m scripts.fetch_report_prism SZSE_300073 --year 2024 --slug {slug}
# 或
curl -L "{pdf_url}" -o prism/topics/{slug}/inbox/{filename}.pdf
```

**Final message 格式**：
- 成功：写出 `success: prism/topics/{slug}/inbox/{filename}.pdf ({size}KB)`
- 失败：写出 `failure: {原因}` + 主 agent 应如何接续（建议手动上传 / 换 URL / 跳过）
```
