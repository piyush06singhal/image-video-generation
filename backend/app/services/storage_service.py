import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.errors import StorageError
from app.core.logging import logger


class StorageService:
    """
    Manages local filesystem storage for projects, uploaded original images,
    and derived/processed artifacts.
    """

    def __init__(self, base_storage_dir: Optional[Path] = None):
        self.storage_dir = base_storage_dir or settings.STORAGE_DIR
        self.projects_dir = self.storage_dir / "projects"
        self.init_storage()

    def init_storage(self) -> None:
        """Ensures the root storage directories exist."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.projects_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to initialize storage directories: {e}")
            raise StorageError(f"Unable to initialize storage at {self.storage_dir}")

    def get_project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def get_project_uploads_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "uploads"

    def get_project_processed_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "processed"

    def get_project_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "project.json"

    def get_plan_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "plan.json"

    def save_plan_json(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves walkthrough generation plan into plan.json.
        """
        json_path = self.get_plan_json_path(project_id)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                dir=str(json_path.parent),
                delete=False,
                encoding="utf-8",
            ) as tf:
                json.dump(data, tf, indent=2, ensure_ascii=False)
                temp_name = tf.name

            os.replace(temp_name, str(json_path))
        except Exception as e:
            logger.error(f"Failed to save plan.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist plan for project {project_id}")

    def load_plan_json(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads walkthrough generation plan from plan.json. Returns None if not yet planned.
        """
        json_path = self.get_plan_json_path(project_id)
        if not json_path.is_file():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read plan.json for {project_id}: {e}")
            raise StorageError(f"Corrupted plan data for project {project_id}")


    def create_project_storage(self, project_id: str) -> Tuple[Path, Path]:
        """
        Creates isolated project storage with uploads/ and processed/ subdirectories.
        """
        try:
            project_dir = self.get_project_dir(project_id)
            uploads_dir = self.get_project_uploads_dir(project_id)
            processed_dir = self.get_project_processed_dir(project_id)

            project_dir.mkdir(parents=True, exist_ok=True)
            uploads_dir.mkdir(parents=True, exist_ok=True)
            processed_dir.mkdir(parents=True, exist_ok=True)

            return uploads_dir, processed_dir
        except Exception as e:
            logger.error(f"Failed to create project storage for {project_id}: {e}")
            raise StorageError(f"Could not create storage directories for project {project_id}")

    def save_project_json(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves project metadata into project.json.
        """
        json_path = self.get_project_json_path(project_id)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Atomic write via temporary file
            with tempfile.NamedTemporaryFile(
                "w",
                dir=str(json_path.parent),
                delete=False,
                encoding="utf-8",
            ) as tf:
                json.dump(data, tf, indent=2, ensure_ascii=False)
                temp_name = tf.name

            os.replace(temp_name, str(json_path))
        except Exception as e:
            logger.error(f"Failed to save project.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist metadata for project {project_id}")

    def load_project_json(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads project metadata from project.json. Returns None if project does not exist.
        """
        json_path = self.get_project_json_path(project_id)
        if not json_path.is_file():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read project.json for {project_id}: {e}")
            raise StorageError(f"Corrupted project data for project {project_id}")

    def save_original_image(
        self, project_id: str, filename: str, content: bytes
    ) -> Path:
        """
        Saves original uploaded image bytes to storage/projects/{project_id}/uploads/{filename}.
        """
        uploads_dir = self.get_project_uploads_dir(project_id)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        destination = uploads_dir / filename
        try:
            with open(destination, "wb") as f:
                f.write(content)
            return destination
        except Exception as e:
            logger.error(f"Failed to save uploaded file {filename}: {e}")
            raise StorageError(f"Failed to write image {filename} to disk.")

    def delete_image_files(
        self, project_id: str, original_filename: str, image_id: str
    ) -> None:
        """
        Removes both the original uploaded image and any derived thumbnail.
        """
        uploads_dir = self.get_project_uploads_dir(project_id)
        processed_dir = self.get_project_processed_dir(project_id)

        # Remove original
        orig_path = uploads_dir / original_filename
        if orig_path.exists():
            try:
                orig_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete original file {orig_path}: {e}")

        # Remove thumbnail
        thumb_path = processed_dir / f"thumb_{image_id}.jpg"
        if thumb_path.exists():
            try:
                thumb_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete thumbnail {thumb_path}: {e}")

    def list_all_projects(self) -> List[Dict[str, Any]]:
        """
        Returns all projects found in storage.
        """
        projects = []
        if not self.projects_dir.exists():
            return projects

        for item in self.projects_dir.iterdir():
            if item.is_dir():
                data = self.load_project_json(item.name)
                if data:
                    projects.append(data)
        
        # Sort by created_at desc
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return projects


storage_service = StorageService()
