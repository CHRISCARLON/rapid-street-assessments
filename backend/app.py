import time
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api.routes.route_handler import router
from logging_config import setup_logging, get_logger
from metrics.metrics import PrometheusMiddleware, metrics_endpoint
from metrics.security import MetricsSecurityMiddleware


enable_file_logging = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(
    log_level=log_level, log_dir="logs", enable_file_logging=enable_file_logging
)
logger = get_logger(__name__)


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
    logger.info("Starting up Rapid Street Assessment API")
    yield
    logger.info("Shutting down Rapid Street Assessment API")


app = FastAPI(
    title="Rapid Street Assessment API",
    description="Rapid Street Assessments (RSAs) are designed to quickly retrieve comprehensive information about streets and the surrounding area.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(MetricsSecurityMiddleware)

app.add_middleware(PrometheusMiddleware)

@app.middleware("http")

async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests and responses
    """
    start_time = time.time()
    usrn = request.query_params.get("usrn", "N/A")

    logger.info(
        f"Incoming request: method={request.method}, "
        f"path={request.url.path}, "
        f"query_params={dict(request.query_params)}, "
        f"client={request.client.host if request.client else 'unknown'}",
        extra={"usrn": usrn},
    )

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        log_level = get_log_level_for_status(response.status_code)
        log_message = (
            f"Response completed: method={request.method}, "
            f"path={request.url.path}, "
            f"status={response.status_code}"
        )

        extra_context = {
            "status_code": response.status_code,
            "duration": f"{duration:.3f}",
            "usrn": usrn,
        }

        if log_level == "error":
            logger.error(log_message, extra=extra_context)
        elif log_level == "warning":
            logger.warning(log_message, extra=extra_context)
        else:
            logger.info(log_message, extra=extra_context)

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: method={request.method}, "
            f"path={request.url.path}, "
            f"error={str(e)}",
            extra={"duration": f"{duration:.3f}", "usrn": usrn, "status_code": 500},
            exc_info=True,
        )
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


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

@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint
    """
    return metrics_endpoint()
