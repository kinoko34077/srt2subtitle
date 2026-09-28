from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}

class InvalidStoreIdError(ValueError):
    pass

class StoreCorruptionError(RuntimeError):
    """Raised when an existing local store file cannot be decoded safely."""

def validate_v2_store_id(value: object) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise InvalidStoreIdError("project_id/preset_id must use only ASCII letters, digits, '_' or '-' (1-128 chars).")
    if value.upper() in _WINDOWS_RESERVED_NAMES:
        raise InvalidStoreIdError("project_id/preset_id uses a reserved filesystem name.")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

class V2Store:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.projects_dir = self.root_dir / "projects"
        self.presets_dir = self.root_dir / "presets"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _entity_dir(store_root: Path, logical_id: object) -> Path:
        normalized_id = validate_v2_store_id(logical_id)
        root = store_root.resolve()
        expected = root / normalized_id
        resolved = expected.resolve(strict=False)
        if resolved != expected:
            raise InvalidStoreIdError("project_id/preset_id does not resolve to its own store directory.")
        if resolved.parent != root:
            raise InvalidStoreIdError("project_id/preset_id escapes the configured store root.")
        return resolved

    @classmethod
    def _entity_file(cls, store_root: Path, logical_id: object, filename: str) -> Path:
        entity_dir = cls._entity_dir(store_root, logical_id)
        path = (entity_dir / filename).resolve(strict=False)
        if path.parent != entity_dir:
            raise InvalidStoreIdError("store file escapes the validated entity directory.")
        return path

    def list_projects(self) -> list[dict]:
        items: list[dict] = []
        for entry in sorted(self.projects_dir.iterdir()):
            entity_dir = self._entity_dir(self.projects_dir, entry.name)
            if not entity_dir.is_dir():
                continue
            path = self._entity_file(self.projects_dir, entry.name, "project.json")
            if not path.exists():
                continue
            data = self._read_json(path)
            items.append(
                {
                    "project_id": data["project_id"],
                    "name": data["project"]["name"],
                    "speaker_count": len(data.get("speakers", [])),
                    "updated_at": data.get("updated_at", ""),
                }
            )
        return items

    def get_project(self, project_id: str) -> dict:
        return self._read_json(self._entity_file(self.projects_dir, project_id, "project.json"))

    def save_project(self, payload: dict, project_id: str | None = None) -> dict:
        candidate_id = project_id if project_id is not None else payload.get("project_id")
        normalized_id = validate_v2_store_id(candidate_id if candidate_id is not None else f"v2prj_{uuid.uuid4().hex[:8]}")
        project_dir = self._entity_dir(self.projects_dir, normalized_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        project_json = self._entity_file(self.projects_dir, normalized_id, "project.json")
        current = self._read_json(project_json) if project_json.exists() else {}
        data = {
            "schema_version": "0.2-local-project",
            "project_id": normalized_id,
            "project": payload["project"],
            "speakers": payload.get("speakers", []),
            "created_at": current.get("created_at") or _utc_now(),
            "updated_at": _utc_now(),
        }
        self._write_json(project_json, data)
        return data

    def list_presets(self) -> list[dict]:
        items: list[dict] = []
        for entry in sorted(self.presets_dir.iterdir()):
            entity_dir = self._entity_dir(self.presets_dir, entry.name)
            if not entity_dir.is_dir():
                continue
            path = self._entity_file(self.presets_dir, entry.name, "preset.json")
            if not path.exists():
                continue
            data = self._read_json(path)
            if data.get("deleted_at"):
                continue
            items.append(data)
        return items

    def get_preset(self, preset_id: str) -> dict:
        data = self._read_json(self._entity_file(self.presets_dir, preset_id, "preset.json"))
        if data.get("deleted_at"):
            raise FileNotFoundError(preset_id)
        return data

    def save_preset(self, payload: dict, preset_id: str | None = None) -> dict:
        candidate_id = preset_id if preset_id is not None else payload.get("preset_id")
        normalized_id = validate_v2_store_id(candidate_id if candidate_id is not None else f"v2preset_{uuid.uuid4().hex[:8]}")
        preset_dir = self._entity_dir(self.presets_dir, normalized_id)
        preset_dir.mkdir(parents=True, exist_ok=True)
        preset_json = self._entity_file(self.presets_dir, normalized_id, "preset.json")
        current = self._read_json(preset_json) if preset_json.exists() else {}
        data = {
            "schema_version": "0.2-local-preset",
            "preset_id": normalized_id,
            "name": payload["name"],
            "subtitle_rule": payload["subtitle_rule"],
            "base_layer": payload["base_layer"],
            "template_exo": payload["template_exo"],
            "template_preview_meta": payload.get("template_preview_meta", {}),
            "created_at": current.get("created_at") or _utc_now(),
            "updated_at": _utc_now(),
        }
        self._write_json(preset_json, data)
        return data

    def delete_preset(self, preset_id: str) -> None:
        preset_json = self._entity_file(self.presets_dir, preset_id, "preset.json")
        if not preset_json.exists():
            raise FileNotFoundError(preset_id)
        data = self._read_json(preset_json)
        data["deleted_at"] = _utc_now()
        data["updated_at"] = data["deleted_at"]
        self._write_json(preset_json, data)

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise StoreCorruptionError(
                f"Stored {path.name} is corrupted and was not modified. Restore or explicitly replace it."
            ) from exc

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            temp_path = None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
