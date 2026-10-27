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
        allow_origins=["http://localhost:8080", "http://localhost:5173"],
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

    from app.api.health import router as health_router
    from app.api.meta import router as meta_router

    # Register under /api prefix and also root for direct routing
    app.include_router(health_router, prefix="/api")
    app.include_router(health_router)
    app.include_router(meta_router, prefix="/api")
    app.include_router(meta_router)

    return app


app = create_app()
