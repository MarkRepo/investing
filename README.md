# prism — 投资研究系统

本地运行的 LLM 驱动投资研究系统。对**行业 / 竞技场 / 公司**开展结构化研究，产出单份决策链 case + 配套 sidecar，可在 `/prism` 查看。

- 设计文档：[`DESIGN.md`](./DESIGN.md) · [`docs/architecture/prism-design.md`](./docs/architecture/prism-design.md)
- 使用手册：[`docs/USER-GUIDE-PRISM.md`](./docs/USER-GUIDE-PRISM.md)
- 开发指南：[`docs/DEVELOPER-GUIDE.md`](./docs/DEVELOPER-GUIDE.md)
- 工作流（Claude skill）：`.claude/skills/prism/`

## 启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

开发时访问 <http://127.0.0.1:8000/prism>。

## 测试

```bash
pytest
```

## 目录索引

```
~/investing/
├── DESIGN.md          prism 设计概览
├── main.py            FastAPI 入口（/ 跳 /prism；另挂 /financials /prices /digest）
├── app/               web 看板：routes/{prism,financials,prices,mineru} + templates/ + 数据层 io/{quotes,financials,company,adapters}
├── prism/             研究系统本体
│   ├── scripts/       CRUD 脚本（零 LLM 调用）
│   ├── workflows/     研究工作流（LLM 推断在对话里做）
│   ├── topics/{slug}/ 每个研究主题的状态 / 资料 / 产出
│   └── dashboard.md   生成的看板
├── scripts/           抓取/解析链：报告抓取（多市场）、MinerU、行情/财务
├── static/            CSS
├── data/              financials.db（行情/财务缓存，本地，gitignore）
├── docs/              prism 文档
└── tests/             pytest
```

## 工作方式

- 所有 LLM 推断在对话里由 Claude 完成；`prism/scripts/` 只做文件读写与查询。
- 研究数据按 topic 存于 `prism/topics/{slug}/`，web 看板自动反映最新状态。
- 触发研究：对 Claude 说「研究 X」/「prism 推进 {slug}」等，详见 prism skill。
