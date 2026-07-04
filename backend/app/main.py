"""
main.py - FastAPI Application Entry Point

This is where the FastAPI app is created and configured.
All route modules are registered here using app.include_router().
The database tables are created automatically on startup.

Run with:
    python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.api.routes import health, trials
from database.connection import init_db

# --- Create the FastAPI application ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A production-style Clinical Trial Matcher using Advanced RAG. "
        "Matches patients to relevant clinical trials using hybrid search, "
        "vector embeddings, and LLM-powered explanations."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    # Initialize database — create tables if they don't exist
    try:
        init_db()
        logger.info("Database connected successfully.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.warning("API will run but database features won't work.")

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
