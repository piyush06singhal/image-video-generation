from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import settings
from app.core.errors import (
    AppException,
    DuplicateImageError,
    ImageNotFoundError,
    ProjectNotFoundError,
)
from app.core.logging import logger
from app.schemas.image import (
    ImageBatchUploadResult,
    ImageMetadata,
    ImageStatus,
    RejectedImage,
)
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStatus
from app.services.image_preprocessor import image_preprocessor
from app.services.storage_service import storage_service
from app.utils.file_utils import (
    generate_image_id,
    generate_project_id,
    sanitize_filename,
)


class ProjectService:
    """
    Core business logic service for real estate project lifecycle and image management.
    """

    def __init__(self):
        self.storage = storage_service
        self.preprocessor = image_preprocessor

    def create_project(self, project_in: ProjectCreate) -> ProjectResponse:
        """
        Creates a new project session with local directory structure.
        """
        active_projects = len(self.storage.list_all_projects())
        if active_projects >= settings.MAX_ACTIVE_PROJECTS:
            raise AppException(
                code="ACTIVE_PROJECT_LIMIT",
                message=(
                    f"This installation allows up to {settings.MAX_ACTIVE_PROJECTS} "
                    "active projects. Delete an existing project before creating another."
                ),
                status_code=429,
            )
        project_id = generate_project_id()
        now = datetime.now(timezone.utc).isoformat()

        self.storage.create_project_storage(project_id)

        project_data = {
            "id": project_id,
            "name": project_in.name,
            "status": ProjectStatus.CREATED.value,
            "created_at": now,
            "updated_at": now,
            "images": [],
            "image_count": 0,
        }

        self.storage.save_project_json(project_id, project_data)
        logger.info(f"Created project: {project_id} ('{project_in.name}')")

        return ProjectResponse(**project_data)

    def get_project(self, project_id: str) -> ProjectResponse:
        """
        Retrieves project metadata by ID.
        """
        data = self.storage.load_project_json(project_id)
        if not data:
            raise ProjectNotFoundError(project_id)

        return ProjectResponse(**data)

    def list_projects(self) -> List[ProjectResponse]:
        """
        Lists all available projects.
        """
        raw_list = self.storage.list_all_projects()
        return [ProjectResponse(**p) for p in raw_list]

    def add_images(
        self, project_id: str, files_data: List[Tuple[str, bytes]]
    ) -> ImageBatchUploadResult:
        """
        Processes and validates multiple uploaded images for a project.
        Extracts metadata, performs exact duplicate detection, saves original and derived files.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        existing_images = project_data.get("images", [])
        remaining_capacity = settings.MAX_IMAGES_PER_PROJECT - len(existing_images)
        if remaining_capacity <= 0:
            raise AppException(
                code="PROJECT_IMAGE_LIMIT",
                message=f"A project can contain at most {settings.MAX_IMAGES_PER_PROJECT} images.",
                status_code=413,
            )
        if len(files_data) > remaining_capacity:
            raise AppException(
                code="PROJECT_IMAGE_LIMIT",
                message=(
                    f"This upload contains {len(files_data)} files, but the project "
                    f"has room for only {remaining_capacity} more image(s)."
                ),
                status_code=413,
            )
        # Set of existing hashes in this project for fast duplicate checking
        existing_hashes = {img["sha256"]: img["id"] for img in existing_images}

        # Track hashes added within the current batch to prevent duplicates in single multi-file upload
        batch_hashes = set()

        accepted_images: List[ImageMetadata] = []
        rejected_images: List[RejectedImage] = []

        uploads_dir = self.storage.get_project_uploads_dir(project_id)
        processed_dir = self.storage.get_project_processed_dir(project_id)

        for original_filename, file_bytes in files_data:
            safe_original_name = sanitize_filename(original_filename)

            try:
                # 1. Image validation and metadata extraction
                metadata_dict = self.preprocessor.validate_and_extract_metadata(
                    file_bytes=file_bytes,
                    original_filename=safe_original_name,
                )

                file_sha256 = metadata_dict["sha256"]

                # 2. Duplicate detection
                if file_sha256 in existing_hashes or file_sha256 in batch_hashes:
                    existing_id = existing_hashes.get(file_sha256)
                    raise DuplicateImageError(
                        filename=safe_original_name,
                        existing_image_id=existing_id,
                    )

                # 3. Generate IDs and paths
                image_id = generate_image_id()
                stored_filename = f"{image_id}_{safe_original_name}"

                # 4. Save original file to uploads/
                self.storage.save_original_image(
                    project_id=project_id,
                    filename=stored_filename,
                    content=file_bytes,
                )

                # 5. Generate safe thumbnail to processed/
                thumb_path = processed_dir / f"thumb_{image_id}.jpg"
                self.preprocessor.generate_thumbnail(
                    file_bytes=file_bytes,
                    output_path=thumb_path,
                )

                # 6. Build ImageMetadata
                api_prefix = settings.API_PREFIX
                file_url = f"{api_prefix}/projects/{project_id}/images/{image_id}/file"
                thumb_url = f"{api_prefix}/projects/{project_id}/images/{image_id}/thumbnail"

                img_meta = ImageMetadata(
                    id=image_id,
                    filename=stored_filename,
                    original_filename=safe_original_name,
                    width=metadata_dict["width"],
                    height=metadata_dict["height"],
                    format=metadata_dict["format"],
                    file_size=metadata_dict["file_size"],
                    aspect_ratio=metadata_dict["aspect_ratio"],
                    sha256=file_sha256,
                    status=ImageStatus.VALIDATED,
                    file_url=file_url,
                    thumbnail_url=thumb_url,
                    is_panoramic=metadata_dict.get("is_panoramic", False),
                    is_panoramic_detected=metadata_dict.get("is_panoramic_detected", False),
                    panoramic_type=metadata_dict.get("panoramic_type", "perspective"),
                )

                accepted_images.append(img_meta)
                batch_hashes.add(file_sha256)
                existing_hashes[file_sha256] = image_id

            except AppException as app_err:
                logger.warning(
                    f"Image validation failed for {safe_original_name}: {app_err.message} ({app_err.code})"
                )
                rejected_images.append(
                    RejectedImage(
                        filename=safe_original_name,
                        code=app_err.code,
                        message=app_err.message,
                    )
                )
            except Exception as e:
                logger.error(f"Unexpected error validating {safe_original_name}: {e}")
                rejected_images.append(
                    RejectedImage(
                        filename=safe_original_name,
                        code="INTERNAL_ERROR",
                        message="An unexpected error occurred while processing the image.",
                    )
                )

        # 7. Update and persist project state if new images were accepted
        if accepted_images:
            for img in accepted_images:
                existing_images.append(img.model_dump())

            project_data["images"] = existing_images
            project_data["image_count"] = len(existing_images)
            project_data["status"] = ProjectStatus.VALIDATED.value
            project_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            self.storage.save_project_json(project_id, project_data)
            logger.info(
                f"Project {project_id}: Added {len(accepted_images)} images, total is now {len(existing_images)}"
            )

        # Return comprehensive batch result
        return ImageBatchUploadResult(
            project_id=project_id,
            total_received=len(files_data),
            total_accepted=len(accepted_images),
            total_rejected=len(rejected_images),
            uploaded=accepted_images,
            rejected=rejected_images,
        )

    def get_images(self, project_id: str) -> List[ImageMetadata]:
        """
        Retrieves all images associated with a project.
        """
        project = self.get_project(project_id)
        return project.images

    def delete_image(self, project_id: str, image_id: str) -> bool:
        """
        Deletes a single image from a project, removes original and derived files.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        existing_images = project_data.get("images", [])
        target_img = None
        remaining_images = []

        for img in existing_images:
            if img["id"] == image_id:
                target_img = img
            else:
                remaining_images.append(img)

        if not target_img:
            raise ImageNotFoundError(image_id, project_id)

        # Delete physical files
        self.storage.delete_image_files(
            project_id=project_id,
            original_filename=target_img["filename"],
            image_id=image_id,
        )

        # Update project data
        project_data["images"] = remaining_images
        project_data["image_count"] = len(remaining_images)
        if len(remaining_images) == 0:
            project_data["status"] = ProjectStatus.CREATED.value
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        self.storage.save_project_json(project_id, project_data)
        logger.info(f"Project {project_id}: Deleted image {image_id}")
        return True

    def get_image_file_path(self, project_id: str, image_id: str) -> Path:
        """
        Locates the original uploaded image file path on disk.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        for img in project_data.get("images", []):
            if img["id"] == image_id:
                path = self.storage.get_project_uploads_dir(project_id) / img["filename"]
                if path.exists():
                    return path
                raise ImageNotFoundError(image_id, project_id)

        raise ImageNotFoundError(image_id, project_id)

    def get_image_thumbnail_path(self, project_id: str, image_id: str) -> Path:
        """
        Locates the thumbnail image file path on disk.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        for img in project_data.get("images", []):
            if img["id"] == image_id:
                path = self.storage.get_project_processed_dir(project_id) / f"thumb_{image_id}.jpg"
                if path.exists():
                    return path
                # Fallback to original if thumbnail missing
                orig_path = self.storage.get_project_uploads_dir(project_id) / img["filename"]
                if orig_path.exists():
                    return orig_path
                raise ImageNotFoundError(image_id, project_id)

        raise ImageNotFoundError(image_id, project_id)

    def delete_project(self, project_id: str) -> bool:
        """
        Safely deletes all files, directories, and database records for a project.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)
        return self.storage.delete_project(project_id)


project_service = ProjectService()
