from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.errors import (
    AppException,
    DuplicateImageError,
    ImageCorruptedError,
    ImageNotFoundError,
    ImageTooLargeError,
    ImageTooSmallError,
    InvalidImageFormatError,
    ProjectNotFoundError,
)
from app.schemas.common import ApiResponse
from app.schemas.image import ImageBatchUploadResult, ImageMetadata
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.scene import ProjectAnalysisRequest, SceneCorrectionPayload
from app.services.project_service import project_service
from app.services.scene_service import scene_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ApiResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(project_in: ProjectCreate):
    """
    Create a new real estate project session.
    """
    project = project_service.create_project(project_in)
    return ApiResponse.success_response(project)


@router.get("", response_model=ApiResponse[List[ProjectResponse]])
async def list_projects():
    """
    List all stored property projects.
    """
    projects = project_service.list_projects()
    return ApiResponse.success_response(projects)


@router.get("/{project_id}", response_model=ApiResponse[ProjectResponse])
async def get_project(project_id: str):
    """
    Retrieve project details and associated images by project ID.
    """
    project = project_service.get_project(project_id)
    return ApiResponse.success_response(project)


@router.post(
    "/{project_id}/images",
    response_model=ApiResponse[ImageBatchUploadResult],
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_images(
    project_id: str,
    files: List[UploadFile] = File(...),
):
    """
    Upload one or more property images for validation and storage in the project.
    Performs format checks, size limits, dimension validation, duplicate hash detection,
    and creates safe derived thumbnails.
    """
    if not files:
        raise AppException(
            code="EMPTY_UPLOAD",
            message="No image files were provided for upload.",
            status_code=400,
        )

    # Read bytes for all uploaded files
    files_data = []
    for file in files:
        content = await file.read()
        filename = file.filename or "image.jpg"
        files_data.append((filename, content))

    # If exactly one file was uploaded, we want direct error codes (413, 415, 400) on failure
    if len(files_data) == 1:
        filename, content = files_data[0]
        # Check project existence first
        project_data = project_service.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        # Validate directly to raise precise HTTP error codes
        # 1. Image validation & metadata extraction
        meta = project_service.preprocessor.validate_and_extract_metadata(
            file_bytes=content,
            original_filename=filename,
        )

        # 2. Check duplicate
        existing_images = project_data.get("images", [])
        for img in existing_images:
            if img["sha256"] == meta["sha256"]:
                raise DuplicateImageError(
                    filename=filename,
                    existing_image_id=img["id"],
                )

    # Run batch processing
    result = project_service.add_images(project_id=project_id, files_data=files_data)

    # If all files in a batch were rejected and total_received == 1, exception was already raised.
    # If all files in multi-batch failed, raise the first error for clarity
    if result.total_accepted == 0 and result.total_rejected > 0:
        first_rejection = result.rejected[0]
        # Map code to status
        status_map = {
            "INVALID_IMAGE_FORMAT": 415,
            "IMAGE_TOO_LARGE": 413,
            "IMAGE_TOO_SMALL": 400,
            "IMAGE_CORRUPTED": 400,
            "DUPLICATE_IMAGE": 400,
        }
        err_status = status_map.get(first_rejection.code, 400)
        raise AppException(
            code=first_rejection.code,
            message=first_rejection.message,
            status_code=err_status,
            details={"rejected": [r.model_dump() for r in result.rejected]},
        )

    return ApiResponse.success_response(result)


@router.get("/{project_id}/images", response_model=ApiResponse[List[ImageMetadata]])
async def get_project_images(project_id: str):
    """
    Get list of all validated images for a project.
    """
    images = project_service.get_images(project_id)
    return ApiResponse.success_response(images)


@router.delete("/{project_id}/images/{image_id}", response_model=ApiResponse[dict])
async def delete_project_image(project_id: str, image_id: str):
    """
    Delete a specific image from a project and clean up its files.
    """
    project_service.delete_image(project_id=project_id, image_id=image_id)
    return ApiResponse.success_response(
        {"deleted": True, "image_id": image_id, "project_id": project_id}
    )


@router.get("/{project_id}/images/{image_id}/file")
async def get_original_image_file(project_id: str, image_id: str):
    """
    Serve the original pristine image file.
    """
    file_path = project_service.get_image_file_path(project_id, image_id)
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=file_path.name,
    )


@router.get("/{project_id}/images/{image_id}/thumbnail")
async def get_image_thumbnail_file(project_id: str, image_id: str):
    """
    Serve the derived thumbnail file.
    """
    file_path = project_service.get_image_thumbnail_path(project_id, image_id)
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=file_path.name,
    )


@router.post("/{project_id}/analyze", response_model=ApiResponse[ProjectResponse])
async def analyze_project_scenes(
    project_id: str,
    request: Optional[ProjectAnalysisRequest] = None,
):
    """
    Execute real multimodal scene analysis and quality evaluation across project photographs.
    Avoids re-analyzing already completed images unless force_reanalyze is True.
    """
    force_reanalyze = request.force_reanalyze if request else False
    image_ids = request.image_ids if request else None

    updated_project = await scene_service.analyze_project(
        project_id=project_id,
        force_reanalyze=force_reanalyze,
        image_ids=image_ids,
    )
    return ApiResponse.success_response(updated_project)


@router.patch("/{project_id}/images/{image_id}/scene", response_model=ApiResponse[ImageMetadata])
async def update_image_scene(
    project_id: str,
    image_id: str,
    payload: SceneCorrectionPayload,
):
    """
    Manually correct or confirm the scene type/features for an image.
    Marks the image as user_corrected and prevents automatic overwrites.
    """
    updated_image = scene_service.update_image_scene(
        project_id=project_id,
        image_id=image_id,
        correction=payload,
    )
    return ApiResponse.success_response(updated_image)


@router.get("/{project_id}/images/{image_id}/analysis-file")
async def get_analysis_image_file(project_id: str, image_id: str):
    """
    Serve the normalized analysis-ready image file.
    """
    file_path = scene_service.get_analysis_image_path(project_id, image_id)
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=file_path.name,
    )

