"""Ads Manager API - FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from config.settings import settings
from api.campaigns import router as campaigns_router
from api.ad_groups import router as ad_groups_router
from api.ads import router as ads_router
from api.reports import router as reports_router
from api.recommendations import router as recommendations_router

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Ads Manager API

    Einheitliche API zur Verwaltung von Werbekampagnen auf verschiedenen Plattformen.

    ### Unterstützte Plattformen
    - ✅ Google Ads
    - 🔜 Meta Ads (Facebook/Instagram)
    - 🔜 LinkedIn Ads
    - 🔜 TikTok Ads

    ### Funktionen
    - Kampagnen erstellen, bearbeiten, pausieren, löschen
    - Anzeigengruppen verwalten
    - Anzeigen erstellen
    - Performance-Reports abrufen
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate Limiter State
app.state.limiter = limiter

# Trusted Host Middleware (gegen Host-Header-Angriffe)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["werbung.afm-software.com", "localhost", "127.0.0.1"]
)

# Rate Limiting Middleware
app.add_middleware(SlowAPIMiddleware)

# CORS Middleware (eingeschränkt auf eigene Domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://werbung.afm-software.com",
        "http://localhost:8001",
        "http://127.0.0.1:8001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Router einbinden
app.include_router(campaigns_router, prefix="/api")
app.include_router(ad_groups_router, prefix="/api")
app.include_router(ads_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")


@app.get("/")
async def root():
    """Redirect to Dashboard"""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
async def dashboard():
    """Dashboard UI"""
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health():
    """Health Check & Info"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/providers")
async def list_providers():
    """Liste aller verfügbaren Ads-Provider"""
    from services.ads_manager import get_ads_manager  # pylint: disable=import-outside-toplevel
    manager = get_ads_manager()
    return {
        "providers": manager.list_providers()
    }


if __name__ == "__main__":
    import uvicorn  # pylint: disable=import-outside-toplevel
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
