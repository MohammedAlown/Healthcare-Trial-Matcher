"""
main.py - FastAPI Application Entry Point

This is where the FastAPI app is created and configured.
All route modules are registered here using app.include_router().

Run with:
    python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.api.routes import health, trials

# --- Create the FastAPI application ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A production-style Clinical Trial Matcher using Advanced RAG. "
        "Matches patients to relevant clinical trials using hybrid search, "
        "vector embeddings, and LLM-powered explanations."
    ),
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc alternative docs
)

# --- CORS Middleware ---
# Allows the Streamlit frontend (different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register route modules ---
app.include_router(health.router)
app.include_router(trials.router)


# --- Startup event ---
@app.on_event("startup")
async def startup_event():
    """Runs once when the server starts."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info("API docs available at /docs")


# --- Root endpoint ---
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — confirms the API is running."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
