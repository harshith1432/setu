import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, sheds, telemetry, control, ai, admin, weather

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Setu: Smart Sericulture Environment Management & Automated Control API for global sericulture farmers.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# SEC-07: Secure CORS Configuration (Restricting wildcard origins with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-Key", "X-API-Key"],
)

# Register Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(sheds.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)
app.include_router(control.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(weather.router, prefix=settings.API_V1_STR)

# Mount Super Admin Web Application
admin_web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "admin_web"))
if os.path.exists(admin_web_dir):
    app.mount("/admin", StaticFiles(directory=admin_web_dir, html=True), name="admin_web")

@app.get("/")
def health_check():
    return {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "network": settings.DEFAULT_REGION,
        "mode": "Dynamic / Worldwide Location & Real-Time Weather",
        "api_docs": "/docs",
        "super_admin_portal": "/admin"
    }
