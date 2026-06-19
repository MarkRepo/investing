# 迁移 Plan — 把 investing 跑到另一台电脑

> 目标：新机器 `git clone` 本仓库后，**按本文逐节执行**即可让系统跑起来（web 看板 + prism 研究流程 + 宏观层 + 测试）。
>
> 前提：旧机器已把"除 `.gitignore` 明确忽略外的内容"全部提交并 push。被忽略的内容（`.env`、`data/*.db`、`prism/topics/*/inbox/`、`.gitnexus/` 等）**不会随 clone 过来**，本文会逐项给出在新机器上重建的方法。

---

## 0. 依赖盘点（clone 拿不到的部分）

| 类别 | 具体内容 | 为何拿不到 | 本 plan 处理节 |
|------|---------|-----------|---------------|
| 凭证 `.env` | `MINERU_TOKEN` `EXA_API_KEY` `BOCHA_API_KEY` `SERPER_API_KEY` `TAVILY_API_KEY` `FRED_API_KEY`（可选 `NASDAQ_API_KEY` `QUANDL_API_KEY` `EDINET_API_KEY` `SMTP_*`） | `.gitignore` 排除 `.env` | §3 |
| 用户级配置 | `~/.claude/settings.json`（`env` 段含 `MOMENTA_USERNAME/PASSWORD` + 上述检索 key；另有 `model`/`hooks`/`statusLine`） | 在主目录外，非仓库文件 | §3 |
| CLI | Claude Code（`claude`，`prism/scripts/claude_runner.py` 依赖） | 外部安装 | §1 |
| 运行时 | Node + npx、uv + uvx（`.mcp.json` 的 tavily/serper MCP 依赖） | 外部安装 | §1 |
| 索引 | GitNexus（`.gitnexus/` + `~/.claude/hooks/gitnexus/`） | gitignore + 主目录外 | §6（可选） |
| 本地数据 | `data/financials.db`、`prism/topics/*/inbox/`、`prism/topics/**/materials/`、`mineru_summaries/`、`prism/logs/` | gitignore | §4 |

> `.mcp.json` **在仓库里**（clone 会带），它用 `${TAVILY_API_KEY}` 等占位符引用环境变量——所以只要 §1 装好 Node/uv、§3 填好 key，MCP 即可用。

---

## 1. 新机器：装系统级依赖

```bash
# 1.1 Python（推荐 3.12；本仓库当前用 3.14，但 akshare/yfinance 在 3.14 上可能装不稳）
python3 --version    # 要求 >= 3.11

# 1.2 Node + npx（tavily MCP 用）
#    macOS: brew install node
#    Linux: 见 nodejs.org 官方源
node --version && npx --version

# 1.3 uv / uvx（serper MCP 用）
#    macOS: brew install uv
#    通用:  curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --version

# 1.4 Claude Code CLI（claude_runner.py / fetch_llm_batch.py 依赖）
#    按 https://claude.com/claude-code 官方指引安装，确认：
which claude          # 期望命中，或位于 ~/.local/bin/claude
```

---

## 2. 新机器：clone + Python 环境

```bash
git clone <repo-url> ~/investing
cd ~/investing

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> 若 `akshare` / `yfinance` 在当前 Python 版本装不上，回到 §1.1 换 3.12 重建 venv。

---

## 3. 新机器：恢复凭证与用户级配置

> ⚠️ **安全**：`.env` 与 `settings.json` 含密钥，**不要 git 提交**。用 scp / 1Password / U 盘等带外方式从旧机器迁移。

### 3.1 重建 `.env`

从旧机器拷贝 `~/investing/.env` 到新机器同路径。或手动新建，至少包含：

```dotenv
# 检索 / 抽取（prism 必需）
MINERU_TOKEN=<旧机器值>
EXA_API_KEY=<旧机器值>
BOCHA_API_KEY=<旧机器值>
SERPER_API_KEY=<旧机器值>
TAVILY_API_KEY=<旧机器值>

# 宏观层
FRED_API_KEY=<旧机器值>

# 可选（按需）
# NASDAQ_API_KEY=...
# QUANDL_API_KEY=...
# EDINET_API_KEY=...
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=...
# SMTP_PASS=...
# FROM_ADDR=...
# TO_ADDR=...
```

> 注：`.env.example` 只列了 SMTP + FRED，**不全**，以本表为准。

### 3.2 重建 `~/.claude/settings.json`

`prism/scripts/providers/{exa,tavily,serper}.py` 在 `os.environ` 找不到 key 时会**回退读 `~/.claude/settings.json` 的 `env` 段**。最省事的做法：直接从旧机器整体拷贝 `~/.claude/settings.json`。

若选择只在新机器放 `.env`（不重建 settings.json），则：
- 检索 key 能从 `.env` 读到，OK；
- 但 `MOMENTA_USERNAME/PASSWORD`（宏观层 momenta 网关）只在 settings.json，宏观层会缺凭证；
- `model` / `statusLine` / `enabledPlugins` 也不会有，Claude Code 行为可能与旧机器不一致。

**推荐：整体拷贝 `~/.claude/settings.json`**，然后检查其中 `hooks` 段——它指向绝对路径 `~/.claude/hooks/gitnexus/gitnexus-hook.cjs`，若不装 GitNexus（§6），先把 `hooks` 段删掉避免报错。

### 3.3 验证 key 能被读到

```bash
python3 -c "from prism.scripts.providers import exa, tavily, serper; \
  print('exa', bool(exa._load_key())); print('tavily', bool(tavily._load_key())); print('serper', bool(serper._load_key()))"
```

---

## 4. 新机器：重建本地数据

### 4.1 financials.db（行情/财务缓存）

`data/financials.db` 被 gitignore，需用 fetch 脚本重建：

```bash
# 行情（EOD），默认回填 5 年
python3 -m scripts.fetch_quotes_eod --markets SSE,SZSE,BSE,US --backfill-years 5

# CN 财务（akshare）
python3 -m scripts.fetch_financials_cn --all

# US 财务（yfinance）
python3 -m scripts.fetch_financials_us --all
```

> 这三步会命中真实外部 API，耗时较长；也可先跳过，等 prism 研究某个 ticker 时按需补 `python3 -m scripts.fetch_financials_cn SSE_600519`。

### 4.2 宏观层种子数据（若要用宏观层）

```bash
python3 -m prism.scripts.seed_macro_inputs
```

### 4.3 已有 prism topic 的原始材料

旧机器 `prism/topics/*/inbox/` 与 `materials/` 被 gitignore，**clone 不会带来**。两个选择：
- **A（推荐）**：从旧机器 rsync 这些目录过来——
  ```bash
  rsync -av 旧机器:~/investing/prism/topics/ prism/topics/ --include='*/' --include='inbox/***' --include='materials/***' --exclude='*'
  ```
- **B**：不迁移材料，只保留 topic 状态/产出（clone 已带），新机器上对这些 topic 的 drilldown/critic 若要重跑需重新抓材料。

> topic 的 `topic.yaml` / `manifest.yaml` / `outputs/` / `state/whitelist/` 都在 git 里，clone 即有。

### 4.4 其余自动重建项（无需操作）

`mineru_summaries/`（/digest 路由自动重建）、`prism/logs/`（运行时生成）——不用管。

---

## 5. 新机器：验证

### 5.1 测试

```bash
pytest                 # 默认跳过 live 标记（不命中真实 API）
# pytest -m live       # 想跑联网测试时单独跑
```

### 5.2 web 看板

```bash
uvicorn main:app --reload
# 浏览器开 http://127.0.0.1:8000/prism
```

### 5.3 MCP 可用性

在 Claude Code 会话里确认 exa/tavily/serper 三个 MCP 已加载（`.mcp.json` 自动生效）。prism 的 00 Step 4.5 prescan 走 adapter，可跑一个轻量 topic 验证检索链路：

```bash
python3 -m prism.scripts.web_search status   # 看 key 池状态
python3 -m prism.scripts.web_search search "test query" --intent news --max-results 3
```

---

## 6. 可选：GitNexus（按 CLAUDE.md 改代码才需要）

CLAUDE.md 要求编辑符号前跑 `gitnexus_impact`、提交前跑 `detect_changes`。**prism 研究流程本身不依赖 GitNexus**，只看研究/不改代码可跳过。

```bash
# 装索引
npx gitnexus analyze

# 确认 hooks 路径存在（settings.json 里指向 ~/./.claude/hooks/gitnexus/gitnexus-hook.cjs）
ls ~/.claude/hooks/gitnexus/
```

若 §3.2 删掉了 hooks 段，装完 GitNexus 后把它加回去。

---

## 7. 速查清单

```
[ ] §1  装 Python 3.12 / Node / uv / Claude Code CLI
[ ] §2  clone + venv + pip install -r requirements.txt
[ ] §3.1 从旧机器带外拷 .env（6 个必需 key + 可选）
[ ] §3.2 从旧机器拷 ~/.claude/settings.json（或仅靠 .env + 手动补 momenta 凭证）
[ ] §3.3 跑 providers key 自检
[ ] §4.1 重建 financials.db（fetch_quotes_eod / fetch_financials_cn/us）
[ ] §4.2 (用宏观层) seed_macro_inputs
[ ] §4.3 (要旧材料) rsync prism/topics/*/inbox + materials
[ ] §5   pytest + uvicorn + web_search status
[ ] §6   (改代码) npx gitnexus analyze + 恢复 hooks
```

---

## 8. 已知坑

1. **`~/.claude/settings.json` 的 hooks 绝对路径**：指向 `/Users/yangqi/.claude/hooks/gitnexus/...`，新机器用户名不同或未装 GitNexus 时会找不到文件 → 建议先删 hooks 段，装完 GitNexus 再加。
2. **Python 3.14 + akshare/yfinance**：可能装包失败或运行时异常，优先用 3.12。
3. **`.env.example` 不完整**：别照它建 `.env`，以本文 §3.1 表为准。
4. **`data/financials.db` 缺失不会立刻报错**：prism 读财务数据时会返回空，容易被误判为"系统正常但没数据"——务必跑 §4.1 或确认按需 fetch。
5. **MCP 占位符**：`.mcp.json` 用 `${TAVILY_API_KEY}` 等，若 §3 没把 key 放进 env 或 settings.json，MCP server 启动即失败。
