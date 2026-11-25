from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from backend.exo_writer import assign_frames, build_srt


FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "exo-rounding.json").read_text(encoding="utf-8"))


class ExoRoundingParityTests(unittest.TestCase):
    def test_frame_cases(self):
        for fixture in FIXTURES["frameCases"]:
            with self.subTest(name=fixture["name"]):
                result = assign_frames(copy.deepcopy(fixture["segments"]), fixture["fps"], {"a": 1, "b": 2})
                self.assertEqual([[s["start_frame"], s["end_frame"]] for s in result], fixture["expected"])

    def test_srt_cases(self):
        for fixture in FIXTURES["srtCases"]:
            with self.subTest(expected=fixture["expected"]):
                self.assertEqual(build_srt(fixture["segments"]), fixture["expected"])


if __name__ == "__main__":
    unittest.main()
