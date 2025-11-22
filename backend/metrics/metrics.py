from timeit import default_timer
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors by type and USRN validity',
    ['method', 'endpoint', 'error_type', 'usrn_status']
)

http_exceptions_total = Counter(
    'http_exceptions_total',
    'Total unhandled exceptions',
    ['method', 'endpoint', 'exception_type']
)


def get_route_template(request: Request) -> str:
    """
    Extract route template to avoid cardinality explosion.

    Returns '/api/streets/{usrn}' instead of '/api/streets/12345'.
    This is critical for preventing metric cardinality issues.
    """
    if request.scope.get("route"):
        return request.scope["route"].path

    return request.url.path

def normalise_status_code(status: int) -> str:
    """
    Group status codes to prevent cardinality explosion!
    """
    if status < 200:
        return "1xx"
    elif status < 300:
        return "2xx"
    elif status < 400:
        return "3xx"
    elif status < 500:
        return "4xx"
    else:
        return "5xx"

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track requests with Prometheus metrics
    """

    EXCLUDED_PATHS = {"/metrics", "/health", "/healthz", "/readiness"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        endpoint = get_route_template(request)
        method = request.method

        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        start = default_timer()
        status_code = 500
        exception_name: Optional[str] = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as exc:
            exception_name = type(exc).__name__
            status_code = 500
            
            http_exceptions_total.labels(
                method=method,
                endpoint=endpoint,
                exception_type=exception_name
            ).inc()

            raise  

        finally:
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

            duration = max(default_timer() - start, 0)

            status_group = normalise_status_code(status_code)

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_group  
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            if status_code >= 400:
                self._record_error_metrics(request, method, endpoint, status_code)

    def _record_error_metrics(
        self,
        request: Request,
        method: str,
        endpoint: str,
        status_code: int
    ) -> None:
        """
        Record error-specific metrics
        """
        error_type = "client_error" if 400 <= status_code < 500 else "server_error"

        has_usrn = "usrn" in request.query_params
        if has_usrn:
            usrn_status = "invalid" if status_code == 400 else "valid"
        else:
            usrn_status = "not_provided"

        http_errors_total.labels(
            method=method,
            endpoint=endpoint,
            error_type=error_type,
            usrn_status=usrn_status
        ).inc()


def metrics_endpoint():
    """
    Endpoint to expose Prometheus metrics.
    """
    return Response(
        content=generate_latest(), 
        media_type=CONTENT_TYPE_LATEST
    )
