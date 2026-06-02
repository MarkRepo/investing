"""FastAPI app entry point for the investing decision system."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import APP_TEMPLATES_DIR, STATIC_DIR
from app.routes.bundles import router as bundles_router
from app.routes.catalysts import router as catalysts_router
from app.routes.claim_audit import router as claim_audit_router
from app.routes.companies import router as companies_router
from app.routes.competence_map import router as competence_map_router
from app.routes.discipline import router as discipline_router
from app.routes.earnings_review import router as earnings_review_router
from app.routes.financials import router as financials_router
from app.routes.journal import router as journal_router
from app.routes.performance import router as performance_router
from app.routes.portfolio import router as portfolio_router
from app.routes.prices import router as prices_router
from app.routes.prompts import router as prompts_router
from app.routes.qa import router as qa_router
from app.routes.regime import router as regime_router
from app.routes.research import router as research_router
from app.routes.review import router as review_router
from app.routes.search import router as search_router
from app.routes.sources import router as sources_router
from app.routes.insights import router as insights_router
from app.routes.mineru import router as mineru_router
from app.routes.prism import router as prism_router
from app.routes.triggers import router as triggers_router
from app.routes.v0 import router as v0_router
from app.routes.valuation import router as valuation_router
from app.routes.watchlist import router as watchlist_router

app = FastAPI(title="investing")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

# Prompts: HTML index at /prompts, raw markdown at /prompts/raw/<file>.md
# - repo-fixed paths (resolve relative to this file, not BASE_PATH)
# - index router registered first so exact /prompts GET hits the index
app.include_router(prompts_router)
_PROMPTS_DIR = Path(__file__).resolve().parent / "docs" / "prompts"
if _PROMPTS_DIR.exists():
    app.mount("/prompts", StaticFiles(directory=_PROMPTS_DIR), name="prompts")

app.include_router(companies_router)
app.include_router(v0_router)
app.include_router(valuation_router)
app.include_router(financials_router)
app.include_router(watchlist_router)
app.include_router(portfolio_router)
app.include_router(research_router)
app.include_router(search_router)
app.include_router(journal_router)
app.include_router(earnings_review_router)
app.include_router(prices_router)
app.include_router(triggers_router)
app.include_router(performance_router)
app.include_router(review_router)
app.include_router(catalysts_router)
app.include_router(regime_router)
app.include_router(competence_map_router)
app.include_router(discipline_router)
app.include_router(claim_audit_router)
app.include_router(qa_router)
app.include_router(bundles_router)
app.include_router(sources_router)
app.include_router(insights_router)
app.include_router(mineru_router)
app.include_router(prism_router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # 首页告警区块已全部移除（多为与当前 prism 流程脱节的老 app 遗留：复盘/价格触发/
    # QA/财报对照均无活写入者，行情两告警按需手动拉取即可）。首页只留标题 + 导航。
    return templates.TemplateResponse(request, "home.html", {})


@app.get("/healthz")
def healthz():
    return {"ok": True}
