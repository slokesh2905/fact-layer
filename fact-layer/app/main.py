from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, migrate_db
from app.api import router as api_router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fact Knowledge Layer API")
    init_db()
    migrate_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Fact Knowledge Layer",
    description="Extract, ground, and cross-reference facts from documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Fact Knowledge Layer",
        "version": "0.1.0",
        "description": "Extract, ground, and cross-reference facts from documents",
        "docs": "/docs",
        "api": "/api"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}