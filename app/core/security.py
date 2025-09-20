import time
import hmac
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.core.config import settings
from app.core.logging import get_logger, SecurityLogger

logger = get_logger("app.security")
security_logger = SecurityLogger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to all responses.

    Implements OWASP security recommendations for web applications.
    """

    def __init__(self, app):
        super().__init__(app)
        self.security_headers = self._get_security_headers()

    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers based on environment configuration."""
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Disable Adobe Flash and PDF plugins
            "X-Permitted-Cross-Domain-Policies": "none",

            # Remove server information
            "Server": settings.APP_NAME,

            # Cache control for sensitive pages
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        # Add HSTS header for HTTPS in production
        if settings.is_production:
            headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"
            )

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'",
        ]

        # Relax CSP for development
        if settings.is_development:
            csp_directives.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* 127.0.0.1:*",
                "connect-src 'self' localhost:* 127.0.0.1:* ws: wss:",
            ])

        headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions Policy (formerly Feature Policy)
        permissions_policy = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()",
        ]
        headers["Permissions-Policy"] = ", ".join(permissions_policy)

        return headers

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to response."""
        # Process request
        response = await call_next(request)

        # Add security headers if enabled
        if settings.SECURITY_HEADERS_ENABLED:
            for header, value in self.security_headers.items():
                response.headers[header] = value

        # Add custom headers for API responses
        if request.url.path.startswith("/api/"):
            response.headers["X-API-Version"] = settings.APP_VERSION
            response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with different limits for different endpoints.

    Implements sliding window rate limiting with Redis backend.
    """

    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = self._get_rate_limits()
        self._memory_store = {}  # Fallback when Redis is unavailable

    def _get_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limits configuration."""
        return {
            "/api/": {
                "requests": settings.API_RATE_LIMIT_PER_MINUTE,
                "window": 60,  # seconds
                "burst": settings.API_RATE_LIMIT_BURST
            },
            "/health": {
                "requests": 30,
                "window": 60,
                "burst": 10
            },
            "/metrics": {
                "requests": 10,
                "window": 60,
                "burst": 5
            },
            "default": {
                "requests": 100,
                "window": 60,
                "burst": 20
            }
        }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply rate limiting."""
        if not settings.API_RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Get rate limit for this endpoint
        rate_limit = self._get_rate_limit_for_path(request.url.path)

        # Check rate limit
        allowed, remaining, reset_time = await self._check_rate_limit(
            client_id, request.url.path, rate_limit
        )

        if not allowed:
            # Log rate limit violation
            security_logger.log_suspicious_activity(
                "rate_limit_exceeded",
                {
                    "endpoint": request.url.path,
                    "client_id": client_id,
                    "rate_limit": rate_limit
                },
                self._get_client_ip(request)
            )

            # Return rate limit error
            response = Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        else:
            # Process request
            response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_limit["requests"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use API key if available
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Use user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit_for_path(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for a specific path."""
        for pattern, limit in self.rate_limits.items():
            if pattern != "default" and path.startswith(pattern):
                return limit
        return self.rate_limits["default"]

    async def _check_rate_limit(
        self, client_id: str, endpoint: str, rate_limit: Dict[str, int]
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed, remaining_requests, reset_timestamp)
        """
        try:
            # Try to use Redis for distributed rate limiting
            from app.core.redis import redis_manager

            if redis_manager._is_connected:
                return await self._check_rate_limit_redis(
                    client_id, endpoint, rate_limit
                )
        except Exception as e:
            logger.warning("Redis unavailable for rate limiting", error=str(e))

        # Fall back to memory-based rate limiting
        return self._check_rate_limit_memory(client_id, endpoint, rate_limit)

    async def _check_rate_limit_redis(
        self, client_id: str, endpoint: str, rate_limit: Dict[str, int]
    ) -> tuple[bool, int, int]:
        """Redis-based rate limiting with sliding window."""
        from app.core.redis import redis_manager

        current_time = int(time.time())
        window = rate_limit["window"]
        limit = rate_limit["requests"]

        # Use sliding window approach
        key = f"rate_limit:{client_id}:{endpoint}"

        async with redis_manager.get_client() as client:
            # Remove expired entries
            await client.zremrangebyscore(key, 0, current_time - window)

            # Count current requests
            current_requests = await client.zcard(key)

            if current_requests >= limit:
                # Get reset time (oldest request + window)
                oldest = await client.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1]) + window if oldest else current_time + window

                return False, 0, reset_time

            # Add current request
            await client.zadd(key, {str(current_time): current_time})
            await client.expire(key, window)

            remaining = limit - current_requests - 1
            reset_time = current_time + window

            return True, remaining, reset_time

    def _check_rate_limit_memory(
        self, client_id: str, endpoint: str, rate_limit: Dict[str, int]
    ) -> tuple[bool, int, int]:
        """Memory-based rate limiting (fallback)."""
        current_time = time.time()
        window = rate_limit["window"]
        limit = rate_limit["requests"]

        key = f"{client_id}:{endpoint}"

        # Clean up old entries
        if key in self._memory_store:
            self._memory_store[key] = [
                req_time for req_time in self._memory_store[key]
                if current_time - req_time < window
            ]
        else:
            self._memory_store[key] = []

        # Check limit
        current_requests = len(self._memory_store[key])

        if current_requests >= limit:
            reset_time = int(self._memory_store[key][0] + window)
            return False, 0, reset_time

        # Add current request
        self._memory_store[key].append(current_time)

        remaining = limit - current_requests - 1
        reset_time = int(current_time + window)

        return True, remaining, reset_time


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for state-changing operations.

    Implements double-submit cookie pattern for CSRF protection.
    """

    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.safe_methods = ["GET", "HEAD", "OPTIONS", "TRACE"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply CSRF protection."""
        # Skip CSRF protection for safe methods and exempt paths
        if (request.method in self.safe_methods or
            any(request.url.path.startswith(path) for path in self.exempt_paths)):
            return await call_next(request)

        # Skip CSRF for API endpoints with valid API key
        if request.url.path.startswith("/api/") and request.headers.get("X-API-Key"):
            return await call_next(request)

        # Check CSRF token for state-changing operations
        csrf_token_header = request.headers.get("X-CSRF-Token")
        csrf_token_cookie = request.cookies.get("csrf_token")

        if not csrf_token_header or not csrf_token_cookie:
            security_logger.log_suspicious_activity(
                "csrf_token_missing",
                {"endpoint": request.url.path, "method": request.method},
                self._get_client_ip(request)
            )

            return Response(
                content='{"detail": "CSRF token missing"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json"
            )

        # Validate CSRF token
        if not self._validate_csrf_token(csrf_token_header, csrf_token_cookie):
            security_logger.log_suspicious_activity(
                "csrf_token_invalid",
                {"endpoint": request.url.path, "method": request.method},
                self._get_client_ip(request)
            )

            return Response(
                content='{"detail": "CSRF token invalid"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json"
            )

        # Process request
        response = await call_next(request)

        # Set new CSRF token if needed
        if not csrf_token_cookie:
            new_csrf_token = self._generate_csrf_token()
            response.set_cookie(
                "csrf_token",
                new_csrf_token,
                secure=settings.is_production,
                httponly=True,
                samesite="strict"
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        if request.client:
            return request.client.host
        return "unknown"

    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(32)

    def _validate_csrf_token(self, header_token: str, cookie_token: str) -> bool:
        """Validate CSRF token using double-submit pattern."""
        # Simple comparison for double-submit pattern
        return hmac.compare_digest(header_token, cookie_token)


class CORSConfig:
    """CORS configuration management."""

    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """Get CORS configuration based on environment."""
        if not settings.CORS_ENABLED:
            return {}

        config = {
            "allow_origins": settings.get_cors_origins(),
            "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
            "allow_methods": [method.strip() for method in settings.CORS_ALLOW_METHODS.split(",")],
            "allow_headers": [header.strip() for header in settings.CORS_ALLOW_HEADERS.split(",")],
            "expose_headers": [
                "X-Request-ID",
                "X-API-Version",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ]
        }

        # Development-specific CORS settings
        if settings.is_development:
            config["allow_origins"] = ["*"]
            config["allow_methods"] = ["*"]
            config["allow_headers"] = ["*"]

        # Production-specific CORS settings
        elif settings.is_production:
            # More restrictive settings for production
            if "*" in config["allow_origins"]:
                logger.warning(
                    "Wildcard CORS origins in production - this may be insecure"
                )

        return config


class SecurityUtils:
    """Utility functions for security operations."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"tas_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks."""
        return hmac.compare_digest(a, b)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        import os
        import re

        # Remove path separators
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\-_\. ]', '', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext

        return filename

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


class SecurityAuditLogger:
    """Security audit logging for compliance and monitoring."""

    def __init__(self):
        self.logger = get_logger("app.security.audit")

    def log_authentication_success(
        self, user_id: str, ip_address: str, user_agent: str
    ):
        """Log successful authentication."""
        self.logger.info(
            "Authentication successful",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            security_event="auth_success"
        )

    def log_authentication_failure(
        self, user_id: str, ip_address: str, reason: str
    ):
        """Log failed authentication."""
        self.logger.warning(
            "Authentication failed",
            user_id=user_id,
            ip_address=ip_address,
            reason=reason,
            security_event="auth_failure"
        )

    def log_authorization_failure(
        self, user_id: str, resource: str, action: str, ip_address: str
    ):
        """Log authorization failure."""
        self.logger.warning(
            "Authorization denied",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            security_event="authz_failure"
        )

    def log_data_access(
        self, user_id: str, resource: str, action: str, ip_address: str
    ):
        """Log data access for audit trail."""
        self.logger.info(
            "Data access",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            security_event="data_access"
        )

    def log_privilege_escalation(
        self, user_id: str, old_role: str, new_role: str, admin_user: str
    ):
        """Log privilege changes."""
        self.logger.warning(
            "Privilege escalation",
            user_id=user_id,
            old_role=old_role,
            new_role=new_role,
            admin_user=admin_user,
            security_event="privilege_change"
        )


# Global security instances
security_audit_logger = SecurityAuditLogger()
security_utils = SecurityUtils()

# Export middleware classes for use in main app
__all__ = [
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "CSRFProtectionMiddleware",
    "CORSConfig",
    "SecurityUtils",
    "SecurityAuditLogger",
    "security_audit_logger",
    "security_utils"
]