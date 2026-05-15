from __future__ import annotations


class AppException(Exception):
    """
    Base exception for all application-level errors.

    All subclasses map to a specific HTTP status code and carry a
    machine-readable ``error_code`` for client-side handling.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, message: str = "Authentication required.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to perform this action.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Request validation failed.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class TenantNotFoundError(NotFoundError):
    error_code = "TENANT_NOT_FOUND"

    def __init__(self, message: str = "Tenant not found.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class TenantSuspendedError(ForbiddenError):
    error_code = "TENANT_SUSPENDED"

    def __init__(self, message: str = "This tenant account has been suspended.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class RateLimitError(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Too many requests. Please try again later.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)


class ServiceUnavailableError(AppException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(self, message: str = "Service temporarily unavailable.", **kwargs) -> None:
        super().__init__(message=message, **kwargs)
