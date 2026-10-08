import asyncio
from typing import List, Optional, Tuple
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.core.config import settings
from app.core.errors import (
    AppException,
    DuplicateImageError,
    ImageTooLargeError,
    ProjectNotFoundError,
)
from app.schemas.assembly import (
    AssemblyJob,
    AssemblyRequest,
    FinalVideoMetadata,
)
from app.schemas.common import ApiResponse
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationRecord,
    EvaluationSummary,
    PanoramaUpdatePayload,
    SceneReviewCreate,
    SceneReviewRecord,
    TechnicalReport,
)
from app.schemas.generation import (
    GenerateRequest,
    GenerationJob,
    ProjectGenerationOverview,
    RegenerateSceneRequest,
)
from app.schemas.image import ImageBatchUploadResult, ImageMetadata, RejectedImage
from app.schemas.plan import GenerationPlan, PlanUpdateRequest
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.render_options import RenderOptions, RenderPresetInfo, RenderOptionsUpdate
from app.schemas.scene import ProjectAnalysisRequest, SceneCorrectionPayload
from app.services.evaluation_service import evaluation_service
from app.services.project_service import project_service
from app.services.render_options_service import render_options_service
from app.services.scene_service import scene_service
from app.services.video_assembler import video_assembler_service
from app.services.video_generation import video_generation_service
from app.services.walkthrough_planner import walkthrough_planner
from app.services.local_slideshow_service import local_slideshow_service


router = APIRouter(prefix="/projects", tags=["Projects"])



@router.post("", response_model=ApiResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(project_in: ProjectCreate):
    """
    Create a new real estate project session.
    """
    project = project_service.create_project(project_in)
    await asyncio.to_thread(project_service.storage.sync_project, project.id)
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

    # Read each upload with a hard cap at MAX_IMAGE_SIZE_BYTES. The limit used to be
    # enforced only after the whole body had been read into memory, so a client could
    # declare a small image and stream gigabytes into RAM before being refused.
    max_bytes = settings.MAX_IMAGE_SIZE_BYTES
    files_data: List[Tuple[str, bytes]] = []
    oversize_rejections: List[RejectedImage] = []
    for file in files:
        filename = file.filename or "image.jpg"
        buffer = bytearray()
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                break
        if len(buffer) > max_bytes:
            oversize = ImageTooLargeError(len(buffer), max_bytes)
            if len(files) == 1:
                # Keep the single-file contract: a direct 413 rather than a batch report.
                raise oversize
            oversize_rejections.append(
                RejectedImage(
                    filename=filename,
                    code="IMAGE_TOO_LARGE",
                    message=oversize.message,
                )
            )
            continue
        files_data.append((filename, bytes(buffer)))

    if not files_data and oversize_rejections:
        # Every file in the batch was over the limit: report it the same way the
        # batch pipeline reports an all-rejected upload.
        first = oversize_rejections[0]
        raise AppException(
            code=first.code,
            message=first.message,
            status_code=413,
            details={"rejected": [r.model_dump() for r in oversize_rejections]},
        )

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

    # Fold files rejected for size (caught before the batch pipeline saw them) back
    # into the batch report so it stays complete and honest about what arrived.
    if oversize_rejections:
        result.rejected.extend(oversize_rejections)
        result.total_rejected += len(oversize_rejections)
        result.total_received = len(files)

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


# ==========================================
# Phase 3: Walkthrough Planning Endpoints
# ==========================================

@router.get("/{project_id}/plan", response_model=ApiResponse[GenerationPlan])
async def get_project_plan(project_id: str):
    """
    Retrieve current walkthrough generation plan for a project.
    Generates a baseline AI plan if none currently exists.
    """
    plan = walkthrough_planner.get_or_create_plan(project_id)
    return ApiResponse.success_response(plan)


@router.post("/{project_id}/plan/rebuild", response_model=ApiResponse[GenerationPlan])
async def rebuild_project_plan(project_id: str):
    """
    Re-generates a new baseline walkthrough plan from the current scene analysis.
    Preserves user-confirmed scene classifications while recalculating route and camera motions.
    """
    plan = walkthrough_planner.generate_baseline_plan(project_id, force_rebuild=True)
    return ApiResponse.success_response(plan)


@router.put("/{project_id}/plan", response_model=ApiResponse[GenerationPlan])
async def update_project_plan(
    project_id: str,
    update_request: PlanUpdateRequest,
):
    """
    Saves a user-modified walkthrough plan (reordering, exclusions, customized camera motions/prompts).
    Increments plan version and sets source to 'user'.
    """
    plan = walkthrough_planner.update_user_plan(project_id, update_request)
    return ApiResponse.success_response(plan)


# ==========================================
# Phase 4: Video Generation Endpoints
# ==========================================

@router.post("/{project_id}/generate", response_model=ApiResponse[ProjectGenerationOverview])
async def generate_project_clips(
    project_id: str,
    request: Optional[GenerateRequest] = None,
):
    """
    Triggers asynchronous image-to-video clip generation for all eligible scenes in the plan.
    Reuses previously generated clips unless force_regenerate is True.
    """
    overview = await video_generation_service.generate_clips(project_id, request)
    return ApiResponse.success_response(overview)


# ==========================================
# Render options (cinematic style controls)
# ==========================================

@router.get("/render-options/presets", response_model=ApiResponse[List[RenderPresetInfo]])
async def list_render_presets():
    """
    Lists the available cinematic style presets for the studio UI.
    """
    return ApiResponse.success_response(render_options_service.list_presets())


@router.get("/{project_id}/render-options", response_model=ApiResponse[RenderOptions])
async def get_project_render_options(project_id: str):
    """
    Returns the cinematic render options this project will be generated and assembled with.
    """
    # Options default rather than error, so the service cannot distinguish "no
    # options saved yet" from "no such project" — check the project here.
    if not project_service.storage.load_project_json(project_id):
        raise ProjectNotFoundError(project_id)
    return ApiResponse.success_response(render_options_service.get(project_id))


@router.patch("/{project_id}/render-options", response_model=ApiResponse[RenderOptions])
async def update_project_render_options(project_id: str, payload: RenderOptionsUpdate):
    """
    Applies a preset and/or partial option overrides to a project.

    Any already-rendered clips and the final walkthrough become stale when the
    changed options affect them; the generation overview and final-video metadata
    report that so the UI can prompt for a regenerate/reassemble.
    """
    options = render_options_service.update(
        project_id,
        preset=payload.preset,
        overrides=payload.options,
        replace=payload.replace,
    )
    return ApiResponse.success_response(options)


@router.get("/{project_id}/generation", response_model=ApiResponse[ProjectGenerationOverview])
async def get_project_generation_overview(project_id: str):
    """
    Retrieves full video generation state and status breakdown for all scenes in the walkthrough plan.
    """
    overview = video_generation_service.get_or_create_overview(project_id)
    return ApiResponse.success_response(overview)


@router.get("/{project_id}/generation/jobs/{job_id}", response_model=ApiResponse[GenerationJob])
async def get_generation_job(project_id: str, job_id: str):
    """
    Retrieves execution state and result metadata for a specific generation job.
    """
    job = video_generation_service.get_job_status(project_id, job_id)
    return ApiResponse.success_response(job)


@router.post("/{project_id}/generation/jobs/{job_id}/retry", response_model=ApiResponse[GenerationJob])
async def retry_generation_job(project_id: str, job_id: str):
    """
    Retries a failed or quota-paused generation job without re-executing other scenes.
    """
    job = await video_generation_service.retry_job(project_id, job_id)
    return ApiResponse.success_response(job)


@router.post("/{project_id}/scenes/{scene_id}/regenerate", response_model=ApiResponse[GenerationJob])
async def regenerate_scene_clip(
    project_id: str,
    scene_id: str,
    request: Optional[RegenerateSceneRequest] = None,
):
    """
    Forces regeneration of an individual scene clip, with optional camera motion or prompt overrides.
    """
    job = await video_generation_service.regenerate_scene(project_id, scene_id, request)
    return ApiResponse.success_response(job)


@router.get("/{project_id}/clips/{scene_id}/file")
async def get_scene_clip_file(project_id: str, scene_id: str):
    """
    Streams the generated MP4 video clip for in-browser playback.
    """
    clip_path = video_generation_service.get_clip_file_path(project_id, scene_id)
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=clip_path.name,
    )


@router.post("/{project_id}/local-slideshow", response_model=ApiResponse[FinalVideoMetadata])
async def create_local_slideshow(project_id: str):
    """Create a local image slideshow fallback without calling a remote AI provider."""
    metadata = await asyncio.to_thread(local_slideshow_service.create, project_id)
    return ApiResponse.success_response(metadata)


# ==========================================
# Phase 5: Video Assembly & Final Walkthrough
# ==========================================

@router.post("/{project_id}/assemble", response_model=ApiResponse[AssemblyJob])
async def assemble_project_walkthrough(
    project_id: str,
    request: Optional[AssemblyRequest] = None,
):
    """
    Assembles individual scene video clips into a single property walkthrough MP4.
    Validates clips, normalizes resolution/framerate, applies approved transitions,
    and extracts final verified metadata.
    """
    # Assembly can exceed Render's request timeout. Queue it and let the client
    # poll GET /assembly while the worker thread performs the FFmpeg pipeline.
    job = await video_assembler_service.queue_assembly(project_id, request)
    return ApiResponse.success_response(job)


@router.get("/{project_id}/assembly", response_model=ApiResponse[Optional[AssemblyJob]])
async def get_project_assembly_status(project_id: str):
    """
    Retrieves current assembly job status or latest completed assembly.
    """
    job = video_assembler_service.get_assembly_job(project_id)
    return ApiResponse.success_response(job)


@router.get("/{project_id}/assembly/{job_id}", response_model=ApiResponse[Optional[AssemblyJob]])
async def get_assembly_job_by_id(project_id: str, job_id: str):
    """
    Retrieves execution state for a specific assembly job.
    """
    job = video_assembler_service.get_assembly_job(project_id, job_id)
    return ApiResponse.success_response(job)


@router.get("/{project_id}/final-video", response_model=ApiResponse[Optional[FinalVideoMetadata]])
async def get_final_walkthrough_metadata(project_id: str):
    """
    Retrieves metadata for the assembled final walkthrough video.
    Identifies whether the video is up-to-date or outdated relative to the plan.
    """
    metadata = video_assembler_service.get_final_metadata(project_id)
    return ApiResponse.success_response(metadata)


@router.get("/{project_id}/final-video/file")
async def get_final_video_file(project_id: str):
    """
    Streams the final assembled walkthrough MP4 for in-browser playback.
    """
    video_path = project_service.storage.get_final_video_path(project_id)
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Final walkthrough video not found for project {project_id}.",
        )
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename="walkthrough.mp4",
    )


@router.get("/{project_id}/final-video/download")
async def download_final_video(project_id: str):
    """
    Direct file download attachment for the final property walkthrough video.
    """
    video_path = project_service.storage.get_final_video_path(project_id)
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Final walkthrough video not found for project {project_id}.",
        )
    proj = project_service.storage.load_project_json(project_id)
    raw_name = (proj.get("name") if proj else "property") or "property"
    clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in raw_name)
    download_filename = f"{clean_name}_cinematic_walkthrough.mp4"

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )


@router.get("/{project_id}/clips/{scene_id}/download")
async def download_scene_clip(project_id: str, scene_id: str):
    """
    Direct file download attachment for an individual generated scene clip.
    """
    clip_path = video_generation_service.get_clip_file_path(project_id, scene_id)
    download_filename = f"{project_id}_{scene_id}.mp4"
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )


# ==========================================
# Phase 6: Panorama & Evaluation Endpoints
# ==========================================

@router.patch("/{project_id}/images/{image_id}/panorama", response_model=ApiResponse[ImageMetadata])
async def update_image_panorama_status(
    project_id: str,
    image_id: str,
    payload: PanoramaUpdatePayload,
):
    """
    Manually classifies or toggles whether an image is a 360-degree equirectangular panorama.
    """
    updated_image = scene_service.update_image_panorama(
        project_id=project_id,
        image_id=image_id,
        is_panoramic=payload.is_panoramic,
        panoramic_type=payload.panoramic_type,
    )
    return ApiResponse.success_response(updated_image)


@router.post("/{project_id}/evaluations", response_model=ApiResponse[EvaluationRecord], status_code=status.HTTP_201_CREATED)
async def submit_human_evaluation(
    project_id: str,
    payload: EvaluationCreate,
):
    """
    Submits a structured human walkthrough evaluation across the 6 core quality dimensions.
    """
    record = evaluation_service.submit_evaluation(project_id, payload)
    return ApiResponse.success_response(record)


@router.get("/{project_id}/evaluations", response_model=ApiResponse[EvaluationSummary])
async def get_project_evaluations(project_id: str):
    """
    Retrieves mathematical evaluation summary averages and list of submitted reviews.
    """
    summary = evaluation_service.get_evaluation_summary(project_id)
    return ApiResponse.success_response(summary)


@router.post("/{project_id}/scene-reviews", response_model=ApiResponse[SceneReviewRecord])
async def submit_scene_review_flag(
    project_id: str,
    payload: SceneReviewCreate,
):
    """
    Submits or updates a reviewer flag (acceptable, needs_review, failed) for an individual scene.
    """
    record = evaluation_service.submit_scene_review(project_id, payload)
    return ApiResponse.success_response(record)


@router.get("/{project_id}/scene-reviews", response_model=ApiResponse[List[SceneReviewRecord]])
async def get_project_scene_reviews(project_id: str):
    """
    Retrieves all per-scene review flags for a project.
    """
    reviews = evaluation_service.get_scene_reviews(project_id)
    return ApiResponse.success_response(reviews)


@router.get("/{project_id}/report", response_model=ApiResponse[TechnicalReport])
async def get_technical_report(project_id: str):
    """
    Generates a full technical walkthrough generation report with quantitative metrics and evaluation data.
    """
    report = evaluation_service.generate_technical_report(project_id)
    return ApiResponse.success_response(report)


@router.get("/{project_id}/report/text")
async def get_technical_report_text(project_id: str):
    """
    Returns standard formatted plain-text walkthrough generation and evaluation report.
    """
    report = evaluation_service.generate_technical_report(project_id)
    return PlainTextResponse(report.formatted_text_report)


@router.delete("/{project_id}", response_model=ApiResponse[dict])
async def delete_project(
    project_id: str,
    confirm: bool = Query(False, description="Must be True to confirm irreversible project deletion"),
):
    """
    Safely and irreversibly removes all stored uploads, clips, plans, and final video files for a project.
    Requires explicit confirm=true query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project deletion requires explicit confirmation (?confirm=true).",
        )
    deleted = project_service.delete_project(project_id)
    if not deleted:
        raise ProjectNotFoundError(project_id)
    return ApiResponse.success_response(
        {"deleted": True, "project_id": project_id, "message": "Project and all associated artifacts deleted safely."}
    )
