from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ProjectNotFoundError(AppException):
    def __init__(self, project_id: str):
        super().__init__(
            code="PROJECT_NOT_FOUND",
            message=f"Project with ID '{project_id}' was not found.",
            status_code=404,
        )


class ImageNotFoundError(AppException):
    def __init__(self, image_id: str, project_id: Optional[str] = None):
        msg = f"Image with ID '{image_id}' was not found"
        if project_id:
            msg += f" in project '{project_id}'."
        else:
            msg += "."
        super().__init__(
            code="IMAGE_NOT_FOUND",
            message=msg,
            status_code=404,
        )


class InvalidImageFormatError(AppException):
    def __init__(self, detected_format: Optional[str] = None, allowed: Optional[list] = None):
        allowed_str = ", ".join(allowed) if allowed else "JPEG, PNG, WEBP"
        msg = f"Unsupported image format: '{detected_format}'. Allowed formats are: {allowed_str}."
        super().__init__(
            code="INVALID_IMAGE_FORMAT",
            message=msg,
            status_code=415,
        )


class ImageTooLargeError(AppException):
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            code="IMAGE_TOO_LARGE",
            message=f"Image size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed size ({max_size / (1024*1024):.2f} MB).",
            status_code=413,
        )


class ImageTooSmallError(AppException):
    def __init__(self, width: int, height: int, min_width: int, min_height: int):
        super().__init__(
            code="IMAGE_TOO_SMALL",
            message=f"Image dimensions ({width}x{height}) are smaller than minimum required ({min_width}x{min_height}).",
            status_code=400,
        )


class ImageCorruptedError(AppException):
    def __init__(self, reason: str = "Image file is corrupted or unreadable."):
        super().__init__(
            code="IMAGE_CORRUPTED",
            message=reason,
            status_code=400,
        )


class DuplicateImageError(AppException):
    def __init__(self, filename: str, existing_image_id: Optional[str] = None):
        super().__init__(
            code="DUPLICATE_IMAGE",
            message="This image has already been uploaded.",
            status_code=400,
            details={"filename": filename, "existing_image_id": existing_image_id} if existing_image_id else None,
        )


class InvalidProjectNameError(AppException):
    def __init__(self, reason: str = "Project name cannot be empty."):
        super().__init__(
            code="INVALID_PROJECT_NAME",
            message=reason,
            status_code=400,
        )


class StorageError(AppException):
    def __init__(self, message: str = "Storage operation failed."):
        super().__init__(
            code="STORAGE_ERROR",
            message=message,
            status_code=500,
        )
