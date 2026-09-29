from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.v2_store import InvalidStoreIdError, V2Store, validate_v2_store_id


class V2StoreIdSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = V2Store(self.root / "v2")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_valid_existing_id_shapes_are_accepted(self) -> None:
        for value in ("v2prj_1234abcd", "v2preset_1234abcd", "prj_xxx", "preset_xxx", "project-1"):
            with self.subTest(value=value):
                self.assertEqual(validate_v2_store_id(value), value)

    def test_path_like_and_reserved_ids_are_rejected(self) -> None:
        invalid = (
            "", ".", "..", "../escape", "..\\escape", "nested/name", "nested\\name",
            "/absolute", "C:\\absolute", "name.txt", "with space", "CON", "nul", "LPT1",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(InvalidStoreIdError):
                    validate_v2_store_id(value)

    def test_save_project_rejects_invalid_id_before_filesystem_mutation(self) -> None:
        outside = self.root / "escape"
        payload = {"project": {"name": "x"}, "speakers": []}
        with self.assertRaises(InvalidStoreIdError):
            self.store.save_project(payload, "../escape")
        self.assertFalse(outside.exists())

    def test_project_get_rejects_invalid_id(self) -> None:
        with self.assertRaises(InvalidStoreIdError):
            self.store.get_project("../escape")

    def test_preset_save_get_delete_share_the_same_id_contract(self) -> None:
        payload = {
            "name": "preset",
            "subtitle_rule": {},
            "base_layer": 1,
            "template_exo": {},
        }
        for operation in (
            lambda: self.store.save_preset(payload, "../escape"),
            lambda: self.store.get_preset("../escape"),
            lambda: self.store.delete_preset("../escape"),
        ):
            with self.assertRaises(InvalidStoreIdError):
                operation()
    def test_list_ignores_stray_invalid_named_entries(self) -> None:
        self.store.save_project(
            {"project": {"name": "ok"}, "speakers": []},
            "project1",
        )
        (self.store.projects_dir / ".DS_Store").write_text("stray", encoding="utf-8")
        invalid_project_dir = self.store.projects_dir / "bad.id"
        invalid_project_dir.mkdir()
        (invalid_project_dir / "project.json").write_text("{}", encoding="utf-8")

        self.store.save_preset(
            {"name": "preset", "subtitle_rule": {}, "base_layer": 1, "template_exo": {}},
            "preset1",
        )
        (self.store.presets_dir / "desktop.ini").write_text("stray", encoding="utf-8")
        invalid_preset_dir = self.store.presets_dir / "bad.id"
        invalid_preset_dir.mkdir()
        (invalid_preset_dir / "preset.json").write_text("{}", encoding="utf-8")

        self.assertEqual(
            [item["project_id"] for item in self.store.list_projects()],
            ["project1"],
        )
        self.assertEqual(
            [item["preset_id"] for item in self.store.list_presets()],
            ["preset1"],
        )

    def test_generated_ids_remain_within_the_valid_contract(self) -> None:
        project = self.store.save_project({"project": {"name": "ok"}, "speakers": []})
        preset = self.store.save_preset({"name": "p", "subtitle_rule": {}, "base_layer": 1, "template_exo": {}})
        self.assertEqual(validate_v2_store_id(project["project_id"]), project["project_id"])
        self.assertEqual(validate_v2_store_id(preset["preset_id"]), preset["preset_id"])

    def test_valid_project_and_preset_ids_remain_usable(self) -> None:
        project = self.store.save_project({"project": {"name": "ok"}, "speakers": []}, "v2prj_abcd1234")
        self.assertEqual(self.store.get_project("v2prj_abcd1234")["project_id"], project["project_id"])

        preset_payload = {
            "name": "preset",
            "subtitle_rule": {},
            "base_layer": 1,
            "template_exo": {},
        }
        preset = self.store.save_preset(preset_payload, "v2preset_abcd1234")
        self.assertEqual(self.store.get_preset("v2preset_abcd1234")["preset_id"], preset["preset_id"])
        self.store.delete_preset("v2preset_abcd1234")
        with self.assertRaises(FileNotFoundError):
            self.store.get_preset("v2preset_abcd1234")


if __name__ == "__main__":
    unittest.main()
