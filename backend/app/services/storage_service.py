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

    def get_project_clips_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "clips"

    def get_project_final_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "final"

    def get_final_video_path(self, project_id: str) -> Path:
        return self.get_project_final_dir(project_id) / "walkthrough.mp4"

    def get_final_metadata_path(self, project_id: str) -> Path:
        return self.get_project_final_dir(project_id) / "metadata.json"

    def get_assembly_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "assembly.json"

    def get_generation_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "generation.json"

    def get_clip_path(self, project_id: str, scene_id: str) -> Path:
        clean_sid = scene_id.replace("scene_", "")
        return self.get_project_clips_dir(project_id) / f"clip_{clean_sid}.mp4"

    def get_render_options_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "render_options.json"

    def save_render_options(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically persists the per-project cinematic render options.
        """
        json_path = self.get_render_options_path(project_id)
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
            logger.error(f"Failed to save render_options.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist render options for project {project_id}")

    def load_render_options(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads per-project render options. Returns None when the user has not customised
        anything yet, so callers can fall back to the default house style.
        """
        json_path = self.get_render_options_path(project_id)
        if not json_path.is_file():
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read render_options.json for {project_id}: {e}")
            return None

    def save_assembly_json(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves assembly overview and job metadata into assembly.json.
        """
        json_path = self.get_assembly_json_path(project_id)
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
            logger.error(f"Failed to save assembly.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist assembly metadata for project {project_id}")

    def load_assembly_json(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads assembly job metadata from assembly.json. Returns None if not yet assembled.
        """
        json_path = self.get_assembly_json_path(project_id)
        if not json_path.is_file():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read assembly.json for {project_id}: {e}")
            raise StorageError(f"Corrupted assembly data for project {project_id}")

    def save_final_metadata_json(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves final walkthrough video metadata into final/metadata.json.
        """
        json_path = self.get_final_metadata_path(project_id)
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
            logger.error(f"Failed to save final metadata.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist final video metadata for project {project_id}")

    def load_final_metadata_json(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads final walkthrough video metadata from final/metadata.json.
        """
        json_path = self.get_final_metadata_path(project_id)
        if not json_path.is_file():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read final metadata.json for {project_id}: {e}")
            raise StorageError(f"Corrupted final video metadata for project {project_id}")

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

    def save_generation_json(self, project_id: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves video generation overview and job metadata into generation.json.
        """
        json_path = self.get_generation_json_path(project_id)
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
            logger.error(f"Failed to save generation.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist generation metadata for project {project_id}")

    def load_generation_json(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads video generation overview and job metadata from generation.json. Returns None if not started.
        """
        json_path = self.get_generation_json_path(project_id)
        if not json_path.is_file():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read generation.json for {project_id}: {e}")
            raise StorageError(f"Corrupted generation data for project {project_id}")

    def delete_clip_file(self, project_id: str, scene_id: str) -> None:
        """
        Removes stored generated video clip for a scene if it exists.
        """
        clip_path = self.get_clip_path(project_id, scene_id)
        if clip_path.exists():
            try:
                clip_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete clip file {clip_path}: {e}")


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

    def get_evaluations_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "evaluations.json"

    def save_evaluations_json(self, project_id: str, data: List[Dict[str, Any]]) -> None:
        """
        Atomically saves list of human evaluations into evaluations.json.
        """
        json_path = self.get_evaluations_json_path(project_id)
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
            logger.error(f"Failed to save evaluations.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist evaluations for project {project_id}")

    def load_evaluations_json(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Loads list of human evaluations from evaluations.json.
        """
        json_path = self.get_evaluations_json_path(project_id)
        if not json_path.is_file():
            return []

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to read evaluations.json for {project_id}: {e}")
            raise StorageError(f"Corrupted evaluations data for project {project_id}")

    def get_scene_reviews_json_path(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "scene_reviews.json"

    def save_scene_reviews_json(self, project_id: str, data: List[Dict[str, Any]]) -> None:
        """
        Atomically saves scene review records into scene_reviews.json.
        """
        json_path = self.get_scene_reviews_json_path(project_id)
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
            logger.error(f"Failed to save scene_reviews.json for {project_id}: {e}")
            raise StorageError(f"Failed to persist scene reviews for project {project_id}")

    def load_scene_reviews_json(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Loads scene review records from scene_reviews.json.
        """
        json_path = self.get_scene_reviews_json_path(project_id)
        if not json_path.is_file():
            return []

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to read scene_reviews.json for {project_id}: {e}")
            raise StorageError(f"Corrupted scene reviews data for project {project_id}")

    def delete_project(self, project_id: str) -> bool:
        """
        Safely deletes all files, directories, and data for a project.
        """
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists() and project_dir.is_dir():
            try:
                shutil.rmtree(project_dir)
                logger.info(f"Cleaned up all storage files for project {project_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete project directory {project_dir}: {e}")
                raise StorageError(f"Failed to delete project storage for {project_id}")
        return False

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
