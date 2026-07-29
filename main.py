"""FastAPI app entry point for the prism research system."""
from dotenv import load_dotenv

# 最早加载 .env（FRED_API_KEY 等密钥）——否则 monitor cycle 的 FRED 自动抓取拿不到 key 而静默跳过。
# 不覆盖已存在的真实环境变量（override=False 默认）。
load_dotenv()

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.monitor_runtime import scheduler_loop
from app.routes.financials import router as financials_router
from app.routes.mineru import router as mineru_router
from app.routes.prices import router as prices_router
from app.routes.prism import router as prism_router
from app.routes.wiki import router as wiki_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起 daily-monitor 后台调度循环(每日 6:00);关停时 cancel 干净退出。"""
    task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="investing · prism", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(prism_router)
app.include_router(financials_router)
app.include_router(prices_router)
app.include_router(mineru_router)
app.include_router(wiki_router)


@app.get("/")
def home():
    return RedirectResponse(url="/prism")


@app.get("/healthz")
def healthz():
    return {"ok": True}
