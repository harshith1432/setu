import os
import time
from fastapi import FastAPI, Response, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import (
    auth, sheds, telemetry, control, ai, admin, weather, voice,
    enterprise_platform, departments, roles_permissions, employees
)

from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_server_start_time = time.time()
_rate_limits = defaultdict(list)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Setu: Smart Sericulture Environment Management & Automated Control API for global sericulture farmers.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# SEC-09: Enterprise HTTP Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https: wss:;"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        return response

# SEC-10: Abuse & Brute-Force Rate Limiting Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register") or path.startswith("/api/v1/auth/invitations"):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_start = now - 60.0
            
            # Prune timestamps older than 60 seconds
            _rate_limits[client_ip] = [ts for ts in _rate_limits[client_ip] if ts > window_start]
            limit = 1000 if os.environ.get("PYTEST_CURRENT_TEST") else 30
            if len(_rate_limits[client_ip]) >= limit:  # 30 auth requests per minute limit in production
                return Response(
                    content='{"detail": "Too many requests. Please slow down and try again later."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"}
                )
            _rate_limits[client_ip].append(now)

        return await call_next(request)


# SEC-12: Payload Size Limit Middleware (OWASP A04 / A05 Resource Exhaustion Mitigation)
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    length = int(content_length)
                    max_allowed = 15 * 1024 * 1024 if ("/upload" in request.url.path or "/products" in request.url.path) else 2 * 1024 * 1024
                    if length > max_allowed:
                        return Response(
                            content='{"detail": "Payload Too Large. Maximum allowed request size is 2MB."}',
                            status_code=413,
                            media_type="application/json"
                        )
                except ValueError:
                    pass
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

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
app.include_router(enterprise_platform.router, prefix=settings.API_V1_STR)
app.include_router(departments.router, prefix=settings.API_V1_STR)
app.include_router(roles_permissions.router, prefix=settings.API_V1_STR)
app.include_router(employees.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_db_init():
    from app.services.db_service import init_db
    from app.services.enterprise_db import init_enterprise_tables
    try:
        init_db()
        init_enterprise_tables()
        from app.services.org_employee_db import init_org_employee_tables
        init_org_employee_tables()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Startup DB init deferred: %s", e)

# Mount Super Admin Web Application
admin_web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "admin_web"))
if os.path.exists(admin_web_dir):
    app.mount("/admin", StaticFiles(directory=admin_web_dir, html=True), name="admin_web")

# Mount Public Landing Page
landing_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "landing"))
landing_index = os.path.join(landing_dir, "index.html")
if os.path.exists(landing_dir):
    app.mount("/landing", StaticFiles(directory=landing_dir, html=True), name="landing")

# Mount Uploads Directory
uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(os.path.join(uploads_dir, "products"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/")
def root_check(request: Request):
    accept = request.headers.get("accept", "")
    # If a web browser visits root, serve the public landing page!
    if "text/html" in accept and not (accept == "*/*"):
        if os.path.exists(landing_index):
            return FileResponse(landing_index)

    # API / Automated test response
    return {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "network": settings.DEFAULT_REGION,
        "mode": "Dynamic / Worldwide Location & Real-Time Weather",
        "landing_page": "/landing",
        "login_portal": "/login",
        "app_portal": "/admin",
        "api_docs": None
    }

@app.get("/home")
def home_page():
    if os.path.exists(landing_index):
        return FileResponse(landing_index)
    return {"message": "Landing page available at /landing"}

@app.get("/login")
def unified_login_page():
    """Unified Official Authentication Gateway for all roles."""
    login_html = os.path.join(admin_web_dir, "index.html")
    if os.path.exists(login_html):
        return FileResponse(login_html)
    return {"message": "Login portal available at /admin"}

@app.get("/register")
def farmer_registration_page():
    """Public Farmer-Only Self-Service Registration Page."""
    register_html = os.path.join(admin_web_dir, "register.html")
    if os.path.exists(register_html):
        return FileResponse(register_html)
    return FileResponse(os.path.join(admin_web_dir, "index.html"))

# Root-level static fallback handlers for standalone /login & /register portals
admin_assets_dir = os.path.join(admin_web_dir, "assets")
if os.path.exists(admin_assets_dir):
    app.mount("/assets", StaticFiles(directory=admin_assets_dir), name="root_assets")

@app.get("/style.css")
def serve_root_style():
    style_path = os.path.join(admin_web_dir, "style.css")
    if os.path.exists(style_path):
        return FileResponse(style_path, media_type="text/css")
    return Response(status_code=404)

@app.get("/app.js")
def serve_root_app_js():
    js_path = os.path.join(admin_web_dir, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    return Response(status_code=404)

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
