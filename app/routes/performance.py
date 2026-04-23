"""Performance comparison routes: /performance."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import performance as perf_io

router = APIRouter(prefix="/performance", tags=["performance"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _render(
    request: Request,
    benchmark: str = "",
    parse_errors: list | None = None,
    written: int | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    symbols = perf_io.list_benchmark_symbols()
    chosen = benchmark or (symbols[0] if symbols else "")
    compare = perf_io.compare(chosen) if chosen else {"rows": [], "cum_portfolio_pct": 0.0, "cum_benchmark_pct": 0.0, "spread_pct": 0.0}
    return templates.TemplateResponse(
        request,
        "performance/index.html",
        {
            "symbols": symbols,
            "chosen": chosen,
            "compare": compare,
            "parse_errors": parse_errors or [],
            "written": written,
        },
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse)
def index(request: Request, benchmark: str = ""):
    return _render(request, benchmark=benchmark)


@router.post("/benchmark-import", response_class=HTMLResponse)
def import_benchmark(
    request: Request,
    paste: str = Form(...),
    benchmark: str = Form(""),
):
    rows, errors = perf_io.parse_benchmark_freeform(paste)
    written = 0
    if rows and not errors:
        written = perf_io.upsert_benchmark_closes(rows)
    status = 200 if not errors else 400
    return _render(
        request,
        benchmark=benchmark,
        parse_errors=errors,
        written=written,
        status_code=status,
    )
