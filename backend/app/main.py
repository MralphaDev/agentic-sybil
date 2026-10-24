
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import forensic, realtime
from app.database.connection import open_pool, close_pool
from app.agent.sse_router import router as investigations_router
from app.agent.copilot.router import router as copilot_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    try:
        yield
    finally:
        close_pool()


app = FastAPI(
    title="Sybil Investigation API",
    description="Forensic analysis and real-time blockchain indexing",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(
    forensic.router,
    prefix="/api/forensic",
    tags=["Forensic"],
)

app.include_router(
    realtime.router,
    prefix="/api/realtime",
    tags=["Realtime"],
)

app.include_router(investigations_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")