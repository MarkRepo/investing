# 架构文档索引

| 文档 | 内容 |
|---|---|
| [00-overview.md](00-overview.md) | 系统概述、目录结构、技术栈、三层知识模型、核心设计原则 |
| [01-data-models.md](01-data-models.md) | Claim、Bundle、Narrative、Portfolio、Watchlist、Journal、SQLite 数据库、审计日志的完整数据结构 |
| [02-ingest-pipeline.md](02-ingest-pipeline.md) | Ingest 流水线 9 个阶段的详解，从 PDF 到 Claim 到 Narrative 的完整流程 |
| [03-narrative-system.md](03-narrative-system.md) | 叙事系统的维度映射、提案生成/验证/应用流程、标记扫描、Web 渲染逻辑 |
| [04-web-routes.md](04-web-routes.md) | 27 个 FastAPI 路由器的完整列表、注册顺序、模板结构、自定义过滤器 |
| [05-portfolio-journal.md](05-portfolio-journal.md) | 组合管理、触发器、催化事件、决策日志、季度审查、收益归因、行情数据 |

## 读者指南

- **新开发者**：先看 [00-overview](00-overview.md) 了解全局，再看 [01-data-models](01-data-models.md) 理解数据结构
- **修改 Web 页面**：看 [04-web-routes](04-web-routes.md)
- **修改 Ingest 流程**：看 [02-ingest-pipeline](02-ingest-pipeline.md)
- **修改叙事系统**：看 [03-narrative-system](03-narrative-system.md)
- **修改组合/纪律工具**：看 [05-portfolio-journal](05-portfolio-journal.md)

用户指南：[../user-guide.md](../user-guide.md)
