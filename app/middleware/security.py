"""
Security middleware for production environment.
Includes rate limiting, security headers, and request validation.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import time
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse.
    Tracks requests per IP address with configurable limits.
    """
    
    def __init__(self, app, requests_per_minute: int = 100, 
                 requests_per_hour: int = 1000, 
                 requests_per_day: int = 10000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        
        # Storage for request tracking
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)
        self.day_requests: Dict[str, list] = defaultdict(list)
        
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _clean_old_requests(self, requests_dict: Dict[str, list], 
                          time_window: timedelta) -> None:
        """Remove old requests outside the time window."""
        current_time = datetime.now()
        for ip in list(requests_dict.keys()):
            requests_dict[ip] = [
                req_time for req_time in requests_dict[ip]
                if current_time - req_time < time_window
            ]
            if not requests_dict[ip]:
                del requests_dict[ip]
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = datetime.now()
        
        # Clean old requests
        self._clean_old_requests(self.minute_requests, timedelta(minutes=1))
        self._clean_old_requests(self.hour_requests, timedelta(hours=1))
        self._clean_old_requests(self.day_requests, timedelta(days=1))
        
        # Check minute limit
        minute_count = len(self.minute_requests[client_ip])
        if minute_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {minute_count}/min")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute exceeded",
                    "retry_after": "60"
                },
                headers={"Retry-After": "60"}
            )
        
        # Check hour limit
        hour_count = len(self.hour_requests[client_ip])
        if hour_count >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {hour_count}/hour")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_hour} requests per hour exceeded",
                    "retry_after": "3600"
                },
                headers={"Retry-After": "3600"}
            )
        
        # Check day limit
        day_count = len(self.day_requests[client_ip])
        if day_count >= self.requests_per_day:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {day_count}/day")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_day} requests per day exceeded",
                    "retry_after": "86400"
                },
                headers={"Retry-After": "86400"}
            )
        
        # Record request
        self.minute_requests[client_ip].append(current_time)
        self.hour_requests[client_ip].append(current_time)
        self.day_requests[client_ip].append(current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.requests_per_minute - minute_count - 1
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.requests_per_hour - hour_count - 1
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Implements OWASP security best practices.
    """
    
    def __init__(self, app, hsts_max_age: int = 31536000,
                 content_security_policy: Optional[str] = None):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.content_security_policy = content_security_policy or "default-src 'self';"
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # HSTS - Force HTTPS
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.hsts_max_age}; includeSubDomains; preload"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.content_security_policy
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        # Remove sensitive headers
        response.headers.pop("X-Powered-By", None)
        response.headers.pop("Server", None)
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for security threats.
    Checks for common attack patterns and malicious payloads.
    """
    
    def __init__(self, app, max_content_length: int = 52428800):  # 50MB default
        super().__init__(app)
        self.max_content_length = max_content_length
        
        # Common SQL injection patterns
        self.sql_patterns = [
            "union select", "drop table", "delete from",
            "insert into", "update set", "exec(",
            "execute(", "xp_cmdshell", "sp_executesql"
        ]
        
        # Common XSS patterns
        self.xss_patterns = [
            "<script", "javascript:", "onerror=",
            "onload=", "onclick=", "alert(",
            "document.cookie", "window.location"
        ]
    
    def _check_suspicious_patterns(self, text: str) -> bool:
        """Check for suspicious patterns in text."""
        text_lower = text.lower()
        
        # Check SQL injection patterns
        for pattern in self.sql_patterns:
            if pattern in text_lower:
                return True
        
        # Check XSS patterns
        for pattern in self.xss_patterns:
            if pattern in text_lower:
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Validate request before processing."""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            logger.warning(f"Request too large: {content_length} bytes")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request too large",
                    "message": f"Maximum content length is {self.max_content_length} bytes"
                }
            )
        
        # Check for suspicious patterns in URL
        if self._check_suspicious_patterns(str(request.url)):
            logger.warning(f"Suspicious URL pattern: {request.url}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid request",
                    "message": "Request contains invalid characters"
                }
            )
        
        # Check for suspicious patterns in headers
        for header_name, header_value in request.headers.items():
            if self._check_suspicious_patterns(f"{header_name}: {header_value}"):
                logger.warning(f"Suspicious header: {header_name}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Invalid request",
                        "message": "Request headers contain invalid characters"
                    }
                )
        
        # Process request
        response = await call_next(request)
        return response


def configure_security_middleware(app, settings):
    """
    Configure all security middleware for the application.
    Should be called during app initialization.
    """
    # Only enable in production
    if settings.environment != "production":
        logger.info("Security middleware disabled in non-production environment")
        return
    
    # Add security headers
    if settings.security_headers_enabled:
        app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_max_age=settings.hsts_max_age,
            content_security_policy=settings.content_security_policy
        )
        logger.info("Security headers middleware enabled")
    
    # Rate limiting is DISABLED per requirements
    # The RateLimitMiddleware class is kept for future use if needed
    logger.info("Rate limiting is disabled")
    
    # Add request validation
    if settings.enable_request_validation:
        app.add_middleware(
            RequestValidationMiddleware,
            max_content_length=settings.max_request_size
        )
        logger.info("Request validation middleware enabled")