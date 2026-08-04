"""
FinAtlas — FastAPI Backend
AI Financial Product Research Agent API
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routers import research, products, countries, compare, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    print(f"🌍 FinAtlas API starting — {settings.APP_NAME} v{settings.VERSION}")
    yield
    print("FinAtlas API shutting down.")


app = FastAPI(
    title="FinAtlas API",
    description=(
        "FinAtlas is an AI Financial Product Research Agent that finds, verifies, and compares loans, savings, "
        "FDRs, DPS, and other financial products from official sources. It analyzes rates, fees, eligibility, "
        "and returns to deliver trusted, evidence-backed recommendations."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(countries.router, prefix="/api/countries", tags=["Countries"])
app.include_router(compare.router, prefix="/api/compare", tags=["Compare"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "markets_live": settings.LIVE_COUNTRIES,
    }


@app.get("/api/")
async def root():
    return {
        "name": "COMPARE AI",
        "description": "Global AI Financial Product Research API",
        "docs": "/api/docs",
        "health": "/api/health",
        "markets": "/api/countries",
    }
