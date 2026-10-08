from contextlib import asynccontextmanager
import hmac
import asyncio
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.schemas.common import ApiResponse
from app.services.video_generation import video_generation_service
from app.services.storage_service import storage_service


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

# ==========================================
# Optional API access key
# ==========================================
#
# NOTE ON ORDER: Starlette builds the middleware stack so that the most recently
# added middleware is the OUTERMOST one. CORS is registered *after* this guard (at
# the bottom of this block) so that CORS wraps the guard's responses. When the
# guard sat outside CORS, its 401 came back without an Access-Control-Allow-Origin
# header, and the browser reported an opaque "Failed to fetch" instead of the real
# "a valid API key is required" message — which made a misconfigured key look like
# a dead server.

# Route suffixes the browser fetches without being able to send headers.
# Keep this list in step with the media routes in app/api/v1/projects.py.
MEDIA_PATH_SEGMENTS = frozenset(
    {
        "health",          # readiness probe, used before any credentials exist
        "file",            # image / clip / final-video streaming
        "download",        # <a download> for the final video and scene clips
        "thumbnail",       # <img> grid thumbnails
        "analysis-file",   # <img> scene-analysis preview
    }
)

@app.middleware("http")
async def api_access_key_guard(request: Request, call_next):
    """
    Gate the API behind a shared secret when API_ACCESS_KEY is configured.

    Deliberately exempt are the *media* routes and the readiness probe, because
    the browser loads them from places that cannot attach a header — an
    ``<img src>``, a ``<video src>`` and a plain ``<a download>``. They are
    addressed by unguessable server-generated ids, so an anonymous GET cannot
    enumerate anything. For a hardened deployment, replace this with signed,
    expiring URLs.

    The exemption is matched on the FINAL path segment against an explicit
    allow-list rather than with ``str.endswith``. ``endswith("/file")`` was the
    original check and it silently missed ``/download``, ``/thumbnail`` and
    ``/analysis-file``, so with a key configured the studio's thumbnails, the
    immersive scene player and both download buttons all broke with a 401 while
    every JSON call kept working.

    When API_ACCESS_KEY is unset the guard is a no-op, so local development is
    unchanged.
    """
    expected = settings.API_ACCESS_KEY
    if not expected:
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)


    path = request.url.path.rstrip("/")
    if path.rsplit("/", 1)[-1] in MEDIA_PATH_SEGMENTS:
        return await call_next(request)

    provided = request.headers.get("X-API-Key") or request.query_params.get("key") or ""
    if not hmac.compare_digest(provided, expected):
        logger.warning(f"Rejected unauthenticated {request.method} {request.url.path}")
        body = ApiResponse.error_response(
            code="UNAUTHORIZED",
            message=(
                "A valid API key is required. Send it in the X-API-Key header "
                "(or as a `key` query parameter)."
            ),
        )
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=body.model_dump())

    return await call_next(request)


@app.middleware("http")
async def persist_project_mutations(request: Request, call_next):
    """Snapshot successful project mutations to durable storage when enabled."""
    response = await call_next(request)
    if response.status_code < 400 and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        parts = request.url.path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            try:
                await asyncio.to_thread(storage_service.sync_project, project_id)
            except Exception as exc:
                logger.error("Durable persistence failed for %s: %s", project_id, exc)
                raise
    return response


# Configure CORS for frontend access. Registered last so it is the outermost
# middleware and therefore decorates every response, including the guard's 401s.
app.add_middleware(
    CORSMiddleware,
    # Never fall back to a wildcard: allow_credentials=True with "*" is rejected by
    # browsers and, where accepted, would let any origin drive the API.
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [],
    # Catches origins that have no stable hostname — every Vercel preview build
    # gets a fresh URL. Empty string is normalised to None so an unset variable
    # cannot accidentally match everything.
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
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
