import unittest

from backend.validators import (
    ValidationError,
    validate_project_payload,
    validate_subtitle_rule,
)


def project(**overrides):
    payload = {"name": "p", "fps": 30, "width": 1920, "height": 1080}
    payload.update(overrides)
    return payload


def rule(**overrides):
    payload = {
        "max_chars_per_line": 20,
        "max_lines": 2,
        "min_duration_sec": 1,
        "max_duration_sec": 5,
    }
    payload.update(overrides)
    return payload


class NonFiniteNumberTests(unittest.TestCase):
    def test_non_finite_values_are_validation_errors(self):
        for value in ("nan", "NaN", "inf", "-inf", float("nan"), float("inf"), "1e400"):
            with self.subTest(value=value):
                for field in ("fps", "width", "height", "audio_rate", "audio_ch"):
                    with self.assertRaises(ValidationError) as ctx:
                        validate_project_payload(project(**{field: value}))
                    self.assertEqual(ctx.exception.code, "ERR-NUMBER-001")
                for field in ("max_chars_per_line", "max_lines", "min_duration_sec", "max_duration_sec"):
                    with self.assertRaises(ValidationError) as ctx:
                        validate_subtitle_rule(rule(**{field: value}))
                    self.assertEqual(ctx.exception.code, "ERR-NUMBER-001")

    def test_ordinary_values_still_accepted(self):
        self.assertEqual(validate_project_payload(project(fps="29.97"))["fps"], 29.97)
        self.assertEqual(validate_subtitle_rule(rule(min_duration_sec="0.5"))["min_duration_sec"], 0.5)


if __name__ == "__main__":
    unittest.main()
