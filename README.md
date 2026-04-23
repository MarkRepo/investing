# 个人投资分析与决策系统

本地运行的个人投资决策系统。解决的核心痛点：**踏空（知道便宜但不敢重仓）和情绪卖出（被宏观叙事冲走原本正确的持仓）**。

- 设计总文档：[`DESIGN.md`](./DESIGN.md)
- V1 实施计划：[`docs/PLAN.md`](./docs/PLAN.md)
- 设计历史对话：[`archive/DESIGN-DIALOGUE.md`](./archive/DESIGN-DIALOGUE.md)

## 启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

开发时访问 <http://127.0.0.1:8000/>。

## 测试

```bash
pytest
```

## 目录索引

```
~/investing/
├── DESIGN.md                 权威设计文档
├── docs/PLAN.md              V1 实施计划
├── main.py                   FastAPI 入口
├── app/                      后端代码（io / routes / templates）
├── templates/                业务 markdown 模板（新建公司时拷贝）
├── static/                   CSS
├── controlled-vocab/         能力圈词表（通用 + 行业）
├── companies/                公司数据（V0 / 能力圈 / 估值 / 研报）
├── industries/               行业 landscape / players
├── watchlist/                观察池三段（预筛 / 研究中 / 价格触发）
├── portfolio/                持仓 + 组合级规则
├── macro/                    市场钟摆 + 催化剂日历（V3）
├── journal/                  投资日志
├── data/                     SQLite 等派生数据（V2）
├── tests/                    pytest
└── archive/                  历史设计对话
```

## V1 状态

开发中。参见 `docs/PLAN.md` 的任务分解。
