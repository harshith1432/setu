import os
import time
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, sheds, telemetry, control, ai, admin, weather, voice

_server_start_time = time.time()

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
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(sheds.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)
app.include_router(control.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(weather.router, prefix=settings.API_V1_STR)
app.include_router(voice.router, prefix=settings.API_V1_STR)

# Mount Super Admin Web Application
admin_web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "admin_web"))
if os.path.exists(admin_web_dir):
    app.mount("/admin", StaticFiles(directory=admin_web_dir, html=True), name="admin_web")

@app.get("/")
def root_check():
    return {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "network": settings.DEFAULT_REGION,
        "mode": "Dynamic / Worldwide Location & Real-Time Weather",
        "api_docs": "/docs",
        "super_admin_portal": "/admin"
    }

@app.get("/health")
def liveness_probe():
    """Liveness probe for orchestrators (Kubernetes / Render / Nomad)."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "uptime_seconds": round(time.time() - _server_start_time, 1)
    }

@app.get("/ready")
def readiness_probe():
    """Readiness probe checking database connection pool and services."""
    from app.services.db_service import get_pool
    p = get_pool()
    return {
        "status": "ready" if p is not None else "degraded",
        "database_pool": "connected" if p is not None else "disconnected",
        "uptime_seconds": round(time.time() - _server_start_time, 1)
    }

@app.get("/metrics")
def prometheus_metrics():
    """Prometheus-compatible plain text metrics exporter."""
    from app.services.telemetry_service import telemetry_service
    uptime = time.time() - _server_start_time
    active_ws = sum(len(c) for c in telemetry_service.ws_manager.shed_connections.values()) + len(telemetry_service.ws_manager.global_connections)
    metrics_text = f"""# HELP setu_uptime_seconds Total server uptime in seconds.
# TYPE setu_uptime_seconds gauge
setu_uptime_seconds {uptime:.1f}
# HELP setu_active_websocket_connections Active real-time client WebSocket connections.
# TYPE setu_active_websocket_connections gauge
setu_active_websocket_connections {active_ws}
# HELP setu_telemetry_history_buffer_count Items in telemetry ring buffer.
# TYPE setu_telemetry_history_buffer_count gauge
setu_telemetry_history_buffer_count {len(telemetry_service.history)}
"""
    return Response(content=metrics_text, media_type="text/plain")
