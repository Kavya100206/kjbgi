"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_VERSION


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://localhost:5173",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:5173",
        ],
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware

    class VercelRewriteMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # If deployed on Vercel with rewrites, restore the original requested path
            path = request.url.path
            matched = request.headers.get("x-matched-path")
            query_path = request.query_params.get("__path__")
            if matched and matched != path and not matched.endswith(".py"):
                request.scope["path"] = matched
            elif query_path:
                request.scope["path"] = "/api/" + query_path.lstrip("/")
            return await call_next(request)

    app.add_middleware(VercelRewriteMiddleware)

    from app.api.accuracy import router as accuracy_router
    from app.api.forecast import router as forecast_router
    from app.api.health import router as health_router
    from app.api.meta import router as meta_router
    from app.api.risk import router as risk_router

    # Register all routers under /api prefix and also root for direct routing
    for r in [health_router, meta_router, forecast_router, accuracy_router, risk_router]:
        app.include_router(r, prefix="/api")
        app.include_router(r)

    return app


app = create_app()
