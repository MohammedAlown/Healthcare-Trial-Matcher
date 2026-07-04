"""
main.py - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.api.routes import health, trials, ingestion, documents
from backend.app.api.routes.pipeline import router as pipeline_router
from database.connection import init_db

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(trials.router)
app.include_router(ingestion.router)
app.include_router(documents.router)
app.include_router(pipeline_router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        init_db()
        logger.info("Database connected successfully.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    logger.info("API docs available at /docs")


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
