import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import twin_survey_compare as survey


class SurveyCompareTest(unittest.TestCase):
    def test_changed_audio_and_display_are_reported_as_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(survey, "CAPTURE_ROOT", root):
                for name, layer, focus in (("off", "CarPlay layer", "audio focus CarPlay"),
                                            ("on", "CarPlay layer; HondaHack layer", "audio focus CarPlay")):
                    folder = root / name / "twin-survey"
                    folder.mkdir(parents=True)
                    (folder / "dumpsys-SurfaceFlinger.txt").write_text(layer + "\n")
                    (folder / "dumpsys-audio.txt").write_text(focus + "\n")
                    commands = [{"file": file, "exitCode": 0} for file in
                                ("dumpsys-SurfaceFlinger.txt", "dumpsys-audio.txt")]
                    (folder / "manifest.json").write_text(json.dumps({"phase": "twin-survey", "commands": commands}))
                result = survey.compare(root / "off" / "twin-survey", root / "on" / "twin-survey")
            self.assertIn("dumpsys-SurfaceFlinger.txt", result["changedFiles"])
            self.assertNotIn("dumpsys-audio.txt", result["changedFiles"])
            self.assertIn("CarPlay layer; HondaHack layer",
                          result["changedFiles"]["dumpsys-SurfaceFlinger.txt"]["signalLinesOnOnly"])

    def test_rejects_manifest_path_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(survey, "CAPTURE_ROOT", root):
                folder = root / "off" / "twin-survey"
                folder.mkdir(parents=True)
                (folder / "manifest.json").write_text(json.dumps({"phase": "twin-survey", "commands":
                    [{"file": "../../original", "exitCode": 0}]}))
                with self.assertRaises(ValueError):
                    survey.compare(folder, folder)


if __name__ == "__main__":
    unittest.main()
