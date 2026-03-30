from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.core.database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Chay khi startup server
    await db.connect()
    yield
    # Chay khi shutdown server
    await db.close()

app = FastAPI(title="AI2D Knowledge Graph API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1", tags=["diagrams"])