import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import SyncResultResponse
from app.service import OrderSynchronizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("order_synchronizer")

synchronizer = OrderSynchronizer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform initial sync on startup
    try:
        logger.info("Performing initial synchronization on startup...")
        await synchronizer.synchronize()
        logger.info("Startup synchronization completed successfully.")
    except Exception as e:
        logger.warning(f"Could not perform startup synchronization: {e}")
    yield

app = FastAPI(
    title="Order Synchronizer API",
    description="Microservice for raw order intake, phone normalization, deduplication, and stats aggregation.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/result", response_model=SyncResultResponse)
async def get_result():
    """
    Primary endpoint returning normalized, deduplicated clients and synchronization statistics.
    Fetches fresh data and stores idempotently in database.
    Falls back to cached database state if upstream API is unavailable.
    """
    try:
        result = await synchronizer.synchronize()
        return result
    except Exception as e:
        logger.error(f"Error during live synchronization: {e}. Attempting fallback to database cache.")
        cached = synchronizer.get_latest_from_db()
        if cached:
            return cached
        raise HTTPException(
            status_code=502,
            detail=f"Failed to synchronize with upstream API and no cached data available: {str(e)}"
        )

@app.get("/", response_model=SyncResultResponse)
async def get_root():
    """
    Root endpoint also returns the JSON result directly to support checkers pointing to root domain.
    """
    return await get_result()

@app.post("/sync", response_model=SyncResultResponse)
async def trigger_sync():
    """
    Explicit endpoint to trigger synchronization run.
    """
    return await get_result()

@app.get("/healthz")
async def health_check():
    """Health check endpoint for container orchestrators and monitoring."""
    return {"status": "ok", "service": "order-synchronizer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
