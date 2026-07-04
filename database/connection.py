"""
connection.py - Database Connection & Session Management

SQLAlchemy needs two things to talk to PostgreSQL:
  1. Engine   — the connection to the database (like opening a phone line)
  2. Session  — a conversation on that line (send queries, get results)

We use a "session factory" pattern:
  - get_db() yields a session for each API request
  - The session auto-closes when the request finishes
  - This prevents connection leaks
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from backend.app.core.config import settings
from backend.app.core.logger import logger

# --- Create the engine ---
# The engine manages the actual connection pool to PostgreSQL.
# pool_pre_ping=True: checks if a connection is alive before using it
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,         # Keep 10 connections open
    max_overflow=20,      # Allow up to 20 extra under load
    echo=settings.DEBUG,  # Log SQL queries when DEBUG=true
)

# --- Session factory ---
# sessionmaker creates a "factory" that produces new Session objects.
# autocommit=False: we manually control when to commit
# autoflush=False: we manually control when to flush to DB
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# --- Base class for all models ---
# Every database model (table) will inherit from this Base.
# It gives them the ability to map Python classes to SQL tables.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session for each request.

    Usage in FastAPI:
        @router.get("/endpoint")
        async def my_endpoint(db: Session = Depends(get_db)):
            ...

    The 'yield' makes this a generator:
      - Before yield: create session
      - yield: hand session to the endpoint
      - After yield (finally): close session, even if there was an error
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables defined by models that inherit from Base.
    Called once at application startup.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
