from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.schemas.common import ApiResponse
from app.services.storage_service import storage_service
from app.services.video_generation import video_generation_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure storage paths are initialized
    storage_service.init_storage()
    logger.info(f"Initialized storage at: {settings.STORAGE_DIR}")
    await video_generation_service.recover_pending_jobs()
    yield
    # Shutdown logic if needed in later phases


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Real Estate Image-to-Video Walkthrough Generation",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under prefix (e.g. /api)
app.include_router(api_router, prefix=settings.API_PREFIX)


# ==========================================
# Exception Handlers for Unified ApiResponse
# ==========================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Handles custom application exceptions with specific status codes.
    """
    response_body = ApiResponse.error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response_body.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic input validation failures.
    """
    errors = exc.errors()
    msg = "Request validation failed."
    clean_errors = []
    
    for err in errors:
        loc = ".".join(str(l) for l in err.get("loc", []))
        clean_errors.append({
            "field": loc,
            "message": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        })
        
    if clean_errors:
        msg = f"Invalid field '{clean_errors[0]['field']}': {clean_errors[0]['message']}"

    response_body = ApiResponse.error_response(
        code="VALIDATION_ERROR",
        message=msg,
        details={"errors": clean_errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_body.model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles standard FastAPI HTTPExceptions.
    """
    code_map = {
        404: "NOT_FOUND",
        400: "BAD_REQUEST",
        403: "FORBIDDEN",
        401: "UNAUTHORIZED",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    response_body = ApiResponse.error_response(
        code=code,
        message=str(exc.detail),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response_body.model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected server errors. Avoids leaking raw tracebacks to clients.
    """
    logger.exception(f"Unhandled server error: {exc}")
    response_body = ApiResponse.error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_body.model_dump(),
    )
