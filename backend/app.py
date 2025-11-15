from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import time
from contextlib import asynccontextmanager

from api.routes.route_handler import router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_log_level_for_status(status_code: int) -> str:
    """Determine the appropriate log level based on status code"""
    if status_code >= 500:
        return "error"
    elif status_code >= 400:
        return "warning"
    else:
        return "info"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events
    """
    # Startup
    logger.info("Starting up Rapid Street Assessment API")
    yield
    # Shutdown
    logger.info("Shutting down Rapid Street Assessment API")


# Initialse FastAPI application
app = FastAPI(
    title="Rapid Street Assessment API",
    description="Rapid Street Assessments (RSAs) are designed to quickly retrieve comprehensive information about streets and the surrounding area.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests and responses
    """
    # Log request
    start_time = time.time()
    logger.info(
        f"Request: method={request.method}, "
        f"path={request.url.path}, "
        f"query_params={dict(request.query_params)}, "
        f"client={request.client.host if request.client else 'unknown'}, "
        f"time={datetime.now()}"
    )

    # Process request
    try:
        response = await call_next(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Log response based on status code
        log_level = get_log_level_for_status(response.status_code)
        log_message = (
            f"Response: status={response.status_code}, duration={duration:.3f}s"
        )

        if log_level == "error":
            logger.error(log_message)
        elif log_level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Request failed: {str(e)}, duration={duration:.3f}s")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


# Include router
app.include_router(
    router,
    responses={
        400: {"description": "Bad Request - Missing or invalid parameters"},
        500: {"description": "Internal Server Error"},
    },
)


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API health check
    """
    return {
        "status": "healthy",
        "message": "Rapid Street Assessment API is running",
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True, log_level="info")
