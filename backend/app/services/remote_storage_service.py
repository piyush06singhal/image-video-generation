"""Durable Supabase Storage snapshots for Render's ephemeral filesystem."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.errors import StorageError
from app.core.logging import logger


class RemoteStorageService:
    """Stores one private archive per project in Supabase Storage.

    The local filesystem remains the working directory required by FFmpeg. A
    project archive is the durable source of truth and is restored lazily when
    Render starts with an empty filesystem.
    """

    def __init__(self) -> None:
        self.enabled = bool(
            settings.REMOTE_STORAGE_ENABLED
            and settings.SUPABASE_URL
            and settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def _headers(self) -> dict[str, str]:
        key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not key:
            raise StorageError("Supabase service role key is not configured.")
        return {
            "Authorization": f"Bearer {key}",
            "apikey": key,
        }

    def _object_url(self, project_id: str) -> str:
        base = (settings.SUPABASE_URL or "").rstrip("/")
        bucket = settings.SUPABASE_STORAGE_BUCKET.strip("/")
        return f"{base}/storage/v1/object/{bucket}/projects/{project_id}.zip"

    @staticmethod
    def _archive(project_dir: Path) -> Path:
        fd, archive_name = tempfile.mkstemp(suffix=".zip", dir=str(project_dir.parent))
        Path(archive_name).unlink(missing_ok=True)
        archive_path = Path(archive_name)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in project_dir.rglob("*"):
                relative_path = path.relative_to(project_dir)
                if (
                    path.is_file()
                    and not path.name.startswith(".")
                    and not (
                        len(relative_path.parts) >= 2
                        and relative_path.parts[0] == "final"
                        and relative_path.parts[1].startswith("temp_")
                    )
                ):
                    archive.write(path, relative_path)
        return archive_path

    def sync_project(self, project_id: str, project_dir: Path) -> None:
        if not self.enabled:
            return
        if not project_dir.is_dir():
            raise StorageError(f"Cannot persist missing project directory: {project_id}")

        archive_path = self._archive(project_dir)
        try:
            archive_bytes = archive_path.stat().st_size
            with archive_path.open("rb") as archive_file:
                response = httpx.post(
                    self._object_url(project_id),
                    content=archive_file,
                    headers={
                        **self._headers(),
                        "Content-Type": "application/zip",
                        "Content-Length": str(archive_bytes),
                        "x-upsert": "true",
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
            index_response = httpx.post(
                f"{(settings.SUPABASE_URL or '').rstrip('/')}/rest/v1/project_snapshots",
                json={
                    "project_id": project_id,
                    "archive_path": f"projects/{project_id}.zip",
                    "archive_bytes": archive_bytes,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                timeout=30.0,
            )
            index_response.raise_for_status()
        except (httpx.HTTPError, StorageError) as exc:
            logger.error("Failed to persist project %s to Supabase: %s", project_id, exc)
            raise StorageError(f"Failed to persist project {project_id} to remote storage") from exc
        finally:
            archive_path.unlink(missing_ok=True)
        logger.info(
            "Persisted project %s to durable storage (%d bytes, %s)",
            project_id,
            archive_bytes,
            datetime.now(timezone.utc).isoformat(),
        )

    def restore_project(self, project_id: str, project_dir: Path) -> bool:
        if not self.enabled:
            return False
        try:
            response = httpx.stream(
                self._object_url(project_id),
                headers=self._headers(),
                timeout=60.0,
            )
            with response as stream:
                if stream.status_code == 404:
                    return False
                stream.raise_for_status()
                fd, archive_name = tempfile.mkstemp(suffix=".zip", dir=str(project_dir.parent))
                archive_path = Path(archive_name)
                with archive_path.open("wb") as archive_file:
                    for chunk in stream.iter_bytes():
                        archive_file.write(chunk)
        except (httpx.HTTPError, StorageError) as exc:
            logger.error("Failed to restore project %s from Supabase: %s", project_id, exc)
            raise StorageError(f"Failed to restore project {project_id} from remote storage") from exc

        with tempfile.TemporaryDirectory(dir=str(project_dir.parent)) as temp_dir:
            extracted = Path(temp_dir) / project_id
            extracted.mkdir()
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    for member in archive.infolist():
                        target = (extracted / member.filename).resolve()
                        if extracted.resolve() not in target.parents:
                            raise StorageError("Remote project archive contains an unsafe path.")
                    archive.extractall(extracted)
            except (OSError, zipfile.BadZipFile) as exc:
                raise StorageError(f"Remote project {project_id} archive is invalid") from exc

            if project_dir.exists():
                shutil.rmtree(project_dir)
            shutil.move(str(extracted), str(project_dir))
        archive_path.unlink(missing_ok=True)
        logger.info("Restored project %s from durable storage", project_id)
        return True

    def list_project_ids(self) -> list[str]:
        if not self.enabled:
            return []
        try:
            response = httpx.get(
                f"{(settings.SUPABASE_URL or '').rstrip('/')}/rest/v1/project_snapshots",
                params={"select": "project_id"},
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            rows = response.json()
            return [row["project_id"] for row in rows if isinstance(row, dict) and row.get("project_id")]
        except (httpx.HTTPError, StorageError, ValueError) as exc:
            logger.error("Failed to list durable projects: %s", exc)
            raise StorageError("Failed to list projects from remote storage") from exc

    def delete_project(self, project_id: str) -> None:
        if not self.enabled:
            return
        try:
            response = httpx.delete(
                self._object_url(project_id),
                headers=self._headers(),
                timeout=30.0,
            )
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()
            index_response = httpx.delete(
                f"{(settings.SUPABASE_URL or '').rstrip('/')}/rest/v1/project_snapshots",
                params={"project_id": f"eq.{project_id}"},
                headers=self._headers(),
                timeout=30.0,
            )
            index_response.raise_for_status()
        except (httpx.HTTPError, StorageError) as exc:
            logger.error("Failed to delete durable project %s: %s", project_id, exc)
            raise StorageError(f"Failed to delete remote project {project_id}") from exc


remote_storage_service = RemoteStorageService()
