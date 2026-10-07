"""Loads, saves and resolves the per-project cinematic :class:`RenderOptions`.

Both Phase 4 (clip generation) and Phase 5 (assembly) read their creative
settings from here, so a project has exactly one source of truth for "how should
this walkthrough look". Persisted as ``render_options.json`` inside the project
directory; absent means "use the house style" rather than an error.
"""

from typing import Any, Dict, List, Optional

from app.core.errors import AppException, ProjectNotFoundError
from app.core.logging import logger
from app.schemas.render_options import (
    PRESET_DEFINITIONS,
    RenderOptions,
    RenderPresetInfo,
    build_render_options,
    default_render_options,
)
from app.services.storage_service import storage_service


class RenderOptionsService:
    def __init__(self, storage=None):
        self.storage = storage or storage_service

    def _assert_project(self, project_id: str) -> None:
        if not self.storage.load_project_json(project_id):
            raise ProjectNotFoundError(project_id)

    def get(self, project_id: str) -> RenderOptions:
        """Returns the project's effective options (persisted, else the house style)."""
        raw = self.storage.load_render_options(project_id)
        if not raw:
            return default_render_options()
        try:
            return RenderOptions(**raw)
        except Exception as exc:
            # A stale or hand-edited file must not break a render: fall back loudly.
            logger.warning(
                f"render_options.json for {project_id} was invalid ({exc}); using defaults."
            )
            return default_render_options()

    def save(self, project_id: str, options: RenderOptions) -> RenderOptions:
        self._assert_project(project_id)
        self.storage.save_render_options(project_id, options.model_dump(mode="json"))
        logger.info(f"Saved render options for {project_id}: preset={options.preset}")
        return options

    def update(
        self,
        project_id: str,
        preset: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        replace: bool = False,
    ) -> RenderOptions:
        """Applies a preset and/or partial overrides on top of the current options.

        ``replace=False`` (default) merges onto what is already saved so the UI can
        send only the control the user touched. Presets always fully re-base the
        option set, because choosing a preset is an explicit "make it look like
        this" action.
        """
        try:
            if preset:
                options = build_render_options(preset, overrides)
            elif replace or not self.storage.load_render_options(project_id):
                options = build_render_options("cinematic_luxury", overrides)
            else:
                current = self.get(project_id).model_dump(mode="json")
                payload = {k: v for k, v in (overrides or {}).items() if v is not None}
                options = RenderOptions(**{**current, **payload})
        except ValueError as exc:
            # A bad preset id or an out-of-range control is caller error, not a 500.
            raise AppException(
                code="INVALID_RENDER_OPTIONS",
                message=str(exc),
                status_code=400,
            ) from exc
        return self.save(project_id, options)

    @staticmethod
    def list_presets() -> List[RenderPresetInfo]:
        return [
            RenderPresetInfo(
                id=key,
                label=definition["label"],
                description=definition["description"],
                options={
                    k: (v.value if hasattr(v, "value") else v)
                    for k, v in definition["options"].items()
                },
                recommended=(key == "cinematic_luxury"),
            )
            for key, definition in PRESET_DEFINITIONS.items()
        ]


render_options_service = RenderOptionsService()
