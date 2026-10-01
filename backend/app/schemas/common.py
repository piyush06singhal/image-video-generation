from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def success_response(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def error_response(cls, code: str, message: str, details: Optional[Any] = None) -> "ApiResponse[None]":
        return cls(
            success=False,
            data=None,
            error=ErrorDetail(code=code, message=message, details=details),
        )
