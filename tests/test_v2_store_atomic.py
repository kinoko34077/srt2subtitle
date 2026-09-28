import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.v2_store import V2Store

PROJECT_OLD = {"project": {"name": "old"}, "speakers": []}
PROJECT_NEW = {"project": {"name": "new"}, "speakers": []}
PRESET = {
    "name": "preset",
    "subtitle_rule": {"max_chars": 20},
    "base_layer": 1,
    "template_exo": {"name": "sample.exo", "content_b64": "AA=="},
}


class V2StoreAtomicWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = V2Store(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
    def test_project_replace_failure_preserves_previous_valid_file(self) -> None:
        saved = self.store.save_project(PROJECT_OLD, "v2prj_atomic")
        path = self.root / "projects" / saved["project_id"] / "project.json"
        before = path.read_bytes()
        with patch("backend.v2_store.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                self.store.save_project(PROJECT_NEW, saved["project_id"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["project"]["name"], "old")
        self.assertFalse(list(path.parent.glob(f".{path.name}.*.tmp")))

    def test_project_fsync_failure_preserves_previous_valid_file(self) -> None:
        saved = self.store.save_project(PROJECT_OLD, "v2prj_fsync")
        path = self.root / "projects" / saved["project_id"] / "project.json"
        before = path.read_bytes()
        with patch("backend.v2_store.os.fsync", side_effect=OSError("fsync failed")):
            with self.assertRaises(OSError):
                self.store.save_project(PROJECT_NEW, saved["project_id"])
        self.assertEqual(path.read_bytes(), before)
    def test_preset_update_replace_failure_preserves_previous_valid_file(self) -> None:
        saved = self.store.save_preset(PRESET, "v2preset_update")
        path = self.root / "presets" / saved["preset_id"] / "preset.json"
        before = path.read_bytes()
        changed = {**PRESET, "name": "changed"}
        with patch("backend.v2_store.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                self.store.save_preset(changed, saved["preset_id"])
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list(path.parent.glob(f".{path.name}.*.tmp")))
    def test_tombstone_replace_failure_preserves_live_preset(self) -> None:
        saved = self.store.save_preset(PRESET, "v2preset_atomic")
        path = self.root / "presets" / saved["preset_id"] / "preset.json"
        before = path.read_bytes()
        with patch("backend.v2_store.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                self.store.delete_preset(saved["preset_id"])
        self.assertEqual(path.read_bytes(), before)
    def test_successful_update_keeps_existing_json_shape(self) -> None:
        saved = self.store.save_project(PROJECT_OLD, "v2prj_compat")
        updated = self.store.save_project(PROJECT_NEW, saved["project_id"])
        self.assertEqual(updated["project_id"], saved["project_id"])
        self.assertEqual(updated["created_at"], saved["created_at"])
        self.assertEqual(updated["project"]["name"], "new")
        self.assertEqual(self.store.get_project(saved["project_id"]), updated)

    def test_corrupted_existing_file_raises_bounded_store_error_without_rewrite(self) -> None:
        path = self.root / "projects" / "v2prj_corrupt" / "project.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"project_id":', encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(Exception) as caught:
            self.store.save_project(PROJECT_NEW, "v2prj_corrupt")
        self.assertEqual(type(caught.exception).__name__, "StoreCorruptionError")
        self.assertIn("corrupted", str(caught.exception).lower())
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
