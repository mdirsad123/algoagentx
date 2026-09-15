from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
import time
import logging
import uuid
import os
import threading
from typing import Optional

from ..core.config import settings
from ..core.logging_config import get_activity_logger

logger = logging.getLogger(__name__)
activity_logger = get_activity_logger()
_ACTIVITY_LAST_SEEN: dict[str, float] = {}
_ACTIVITY_LOCK = threading.Lock()
_ACTIVITY_TTL_SECONDS = max(5, int(os.getenv("ACTIVITY_REQUEST_TTL_SECONDS", "60") or 60))
_ACTIVITY_MIN_GAP_SECONDS = max(0.0, float(os.getenv("ACTIVITY_REQUEST_MIN_GAP_SECONDS", "2") or 2))
_ACTIVITY_EXCLUDED_PREFIXES = (
    "/api/v1/mt5-agent/quotes",
    "/api/v1/mt5-agent/heartbeat",
    "/api/v1/mt5-agent/commands",
    "/api/v1/mt5-agent/alert-symbols",
    "/api/v1/jobs/",
)

def _should_log_activity_request(method: str, path: str, now: float) -> bool:
    if any(path.startswith(prefix) for prefix in _ACTIVITY_EXCLUDED_PREFIXES):
        return False
    if path.endswith("/status") and "/funded-backtests/" in path:
        return False
    key = f"{method.upper()} {path}"
    with _ACTIVITY_LOCK:
        last_any = _ACTIVITY_LAST_SEEN.get("__ANY__", 0.0)
        if now - last_any < _ACTIVITY_MIN_GAP_SECONDS:
            return False
        last = _ACTIVITY_LAST_SEEN.get(key, 0.0)
        if now - last < _ACTIVITY_TTL_SECONDS:
            return False
        _ACTIVITY_LAST_SEEN[key] = now
        _ACTIVITY_LAST_SEEN["__ANY__"] = now
        # Prevent an unbounded cache if dynamic URLs create many unique keys.
        if len(_ACTIVITY_LAST_SEEN) > 2000:
            cutoff = now - (_ACTIVITY_TTL_SECONDS * 2)
            stale = [k for k, ts in _ACTIVITY_LAST_SEEN.items() if ts < cutoff]
            for stale_key in stale[:1000]:
                _ACTIVITY_LAST_SEEN.pop(stale_key, None)
    return True

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add HSTS for production and staging
        if settings.is_production or settings.is_staging:
            hsts_value = f"max-age={settings.hsts_max_age}"
            if settings.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if settings.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Add CSP (Content Security Policy) - basic implementation
        if settings.is_production or settings.is_staging:
            csp_value = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
            response.headers["Content-Security-Policy"] = csp_value
        
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID tracking and enhanced logging."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state for access in endpoints
        request.state.request_id = request_id
        
        # Enhanced logging with request details
        user_id = "anonymous"
        job_id = "none"
        
        # Try to extract user info from headers (if available)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # In a real implementation, you'd decode the JWT to get user info
            # For now, we'll just log that there's an auth header
            user_id = "authenticated_user"
        
        # Try to extract job ID from path params
        if hasattr(request, "path_params") and "job_id" in request.path_params:
            job_id = request.path_params["job_id"]
        
        # Routine request traces are DEBUG-only so high-frequency polling stays silent.
        logger.debug(
            f"REQUEST_START - ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"User: {user_id} | "
            f"Job: {job_id} | "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            duration = time.time() - start_time
            
            # Keep normal 2xx/4xx traffic at DEBUG. Only server-side request
            # failures are promoted to ERROR in production.
            if response.status_code >= 500:
                logger.error(
                    f"REQUEST_FAILED - ID: {request_id} | "
                    f"Method: {request.method} | "
                    f"Path: {request.url.path} | "
                    f"Status: {response.status_code} | "
                    f"Duration: {duration:.3f}s | "
                    f"User: {user_id} | "
                    f"Job: {job_id}"
                )
            else:
                logger.debug(
                    f"REQUEST_END - ID: {request_id} | "
                    f"Status: {response.status_code} | "
                    f"Duration: {duration:.3f}s | "
                    f"User: {user_id} | "
                    f"Job: {job_id}"
                )
            
            # Emit one concise activity line per route per TTL window. This gives
            # a useful sign of page/API activity without bringing back request spam.
            if response.status_code < 500 and _should_log_activity_request(request.method, request.url.path, time.time()):
                activity_logger.info(
                    "API %s %s | status=%s | %.3fs",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration,
                )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration even for errors
            duration = time.time() - start_time
            
            # Log error with full stack trace
            logger.exception(
                f"REQUEST_ERROR - ID: {request_id} | "
                f"Method: {request.method} | "
                f"Path: {request.url.path} | "
                f"Error: {str(e)} | "
                f"Duration: {duration:.3f}s | "
                f"User: {user_id} | "
                f"Job: {job_id}"
            )
            
            # Return error response with request ID
            error_content = {
                "error": "Internal server error",
                "request_id": request_id,
                "message": "An error occurred while processing your request"
            }
            
            # In development, include debug error details
            if settings.is_development:
                error_content["debug_error"] = str(e)
            
            return JSONResponse(
                status_code=500,
                content=error_content
            )


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware to handle health check endpoints with minimal logging."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip detailed logging for health checks
        if request.url.path in ["/health", "/health/redis", "/ready"]:
            return await call_next(request)
        
        return await call_next(request)