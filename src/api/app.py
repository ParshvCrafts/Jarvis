"""
FastAPI Application for JARVIS Mobile API.

Main entry point for the mobile backend API.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .routes import get_all_routers, set_jarvis_instance
from .websocket import websocket_router
from .voice import voice_router


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self._requests: dict = {}  # ip -> list of timestamps
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        if client_ip in self._requests:
            self._requests[client_ip] = [
                ts for ts in self._requests[client_ip] if ts > minute_ago
            ]
        else:
            self._requests[client_ip] = []
        
        # Check limit
        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Record request
        self._requests[client_ip].append(now)
        return True


# Global rate limiter
rate_limiter = RateLimiter(requests_per_minute=60)


# ============================================================================
# Application Factory
# ============================================================================

def create_app(
    jarvis_instance=None,
    title: str = "JARVIS Mobile API",
    version: str = "1.0.0",
    debug: bool = False,
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        jarvis_instance: Optional JarvisUnified instance for command processing.
        title: API title for documentation.
        version: API version.
        debug: Enable debug mode.
    
    Returns:
        Configured FastAPI application.
    """
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        logger.info("Starting JARVIS Mobile API...")
        
        # Set JARVIS instance if provided
        if jarvis_instance:
            set_jarvis_instance(jarvis_instance)
            logger.info("JARVIS instance connected to API")
        
        yield
        
        logger.info("Shutting down JARVIS Mobile API...")
    
    # Create app
    app = FastAPI(
        title=title,
        description="""
## JARVIS Mobile API

RESTful API for mobile app integration with JARVIS AI assistant.

### Features
- JWT authentication with refresh tokens
- Text command processing
- IoT device control
- Voice transcription and synthesis
- Real-time WebSocket communication
- Push notifications

### Authentication
All endpoints (except `/api/v1/auth/login`) require a valid JWT token.
Include the token in the `Authorization` header:
```
Authorization: Bearer <your_token>
```

### Rate Limiting
API requests are limited to 60 per minute per IP address.
        """,
        version=version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    # ========================================================================
    # Middleware
    # ========================================================================
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://jarvis.local",
            "*",  # Allow all for PWA (configure properly in production)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging and rate limiting middleware
    @app.middleware("http")
    async def log_and_rate_limit(request: Request, call_next):
        """Log requests and apply rate limiting."""
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for docs
        if request.url.path.startswith("/api/docs") or request.url.path.startswith("/api/redoc"):
            response = await call_next(request)
            return response
        
        # Rate limiting
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Too many requests", "detail": "Rate limit exceeded"},
            )
        
        # Process request
        response = await call_next(request)
        
        # Log request
        process_time = (time.time() - start_time) * 1000
        logger.debug(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.1f}ms"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.1f}ms"
        
        return response
    
    # ========================================================================
    # Exception Handlers
    # ========================================================================
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if debug else "An unexpected error occurred",
            },
        )
    
    # ========================================================================
    # Routes
    # ========================================================================
    
    # Health check (no auth required)
    @app.get("/api/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "jarvis-mobile-api",
            "version": version,
        }
    
    # Include all routers under /api/v1
    for router in get_all_routers():
        app.include_router(router, prefix="/api/v1")
    
    # Include WebSocket router
    app.include_router(websocket_router, prefix="/api/v1")
    
    # Include voice router
    app.include_router(voice_router, prefix="/api/v1")
    
    return app


# ============================================================================
# Singleton App Instance
# ============================================================================

_app: Optional[FastAPI] = None


def get_app() -> FastAPI:
    """Get or create the global FastAPI app instance."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


# ============================================================================
# Run Server
# ============================================================================

async def run_api_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    jarvis_instance=None,
):
    """
    Run the API server.
    
    Args:
        host: Host to bind to.
        port: Port to bind to.
        jarvis_instance: Optional JarvisUnified instance.
    """
    import uvicorn
    
    app = create_app(jarvis_instance=jarvis_instance)
    
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )
    
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_api_server())
