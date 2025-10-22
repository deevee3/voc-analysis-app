"""FastAPI application entrypoint for the Voice of Customer analysis service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from voc_app.api import api_router

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="Voice of Customer Analysis API",
    description=(
        "Backend service for collecting, processing, and serving Voice of Customer insights "
        "built on Crawl4AI."
    ),
    version="0.1.0",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health", tags=["system"], summary="Health check")
def health_check() -> dict[str, str]:
    """Simple endpoint for uptime monitoring."""
    return {"status": "ok"}
