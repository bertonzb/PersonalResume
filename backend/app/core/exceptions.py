from __future__ import annotations


class AppException(Exception):
    """业务异常基类。"""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
        )


class PermissionDeniedError(AppException):
    def __init__(self) -> None:
        super().__init__(message="Permission denied", code="PERMISSION_DENIED")
