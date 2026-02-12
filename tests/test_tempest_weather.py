import json
import pathlib
import tempfile
import unittest
from unittest import mock

# Import from scripts directory
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import get_tempest_weather as tw  # noqa: E402


class TestTempestWeather(unittest.TestCase):
    def test_unit_conversions(self):
        self.assertAlmostEqual(tw.c_to_f(0), 32.0, places=1)
        self.assertAlmostEqual(tw.ms_to_mph(1), 2.2369, places=3)
        self.assertAlmostEqual(tw.mb_to_inhg(1013.25), 29.921, places=3)
        self.assertAlmostEqual(tw.mm_to_in(25.4), 1.0, places=3)

    def test_build_observations_url_device_wins(self):
        url = tw.build_observations_url(
            token="abc123",
            station_id="58152",
            device_id="165840",
        )
        self.assertIn("/observations/device/165840", url)
        self.assertNotIn("/observations/station/58152", url)

    def test_parse_and_convert_with_mock_fixture(self):
        fixture_path = pathlib.Path(__file__).parent / "fixtures" / "obs_device.json"
        payload = json.loads(fixture_path.read_text())

        obs_list = tw.extract_obs_list(payload)
        parsed = tw.parse_obs(obs_list[0])
        converted = tw.convert_units(parsed, "us")

        self.assertEqual(converted["relative_humidity_pct"], 75)
        self.assertAlmostEqual(converted["air_temp_f"], 23.7, places=1)
        self.assertAlmostEqual(converted["wind_avg_mph"], 3.8, places=1)
        self.assertAlmostEqual(converted["station_pressure_inhg"], 28.771, places=3)

    def test_summary_handles_missing_fields(self):
        summary = tw.make_summary({"timestamp_epoch": None}, "us")
        self.assertIn("Tempest @", summary)

    # Version is sourced from SKILL.md frontmatter (no env override).

    def test_read_version_from_skill_md(self):
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            scripts_dir = base / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "get_tempest_weather.py").write_text("# placeholder", encoding="utf-8")
            (base / "SKILL.md").write_text(
                "---\nname: tempest-weather\nversion: 9.9.9\n---\n",
                encoding="utf-8",
            )

            fake_file = scripts_dir / "get_tempest_weather.py"
            with mock.patch.object(tw, "__file__", str(fake_file)):
                self.assertEqual(tw.read_version_from_skill_md(), "9.9.9")

    @mock.patch.dict(tw.os.environ, {}, clear=True)
    def test_build_user_agent_without_version_suffix(self):
        with mock.patch.object(tw, "read_version_from_skill_md", return_value=None):
            self.assertEqual(tw.detect_version(), None)
            self.assertEqual(tw.build_user_agent(), "openclaw-tempest-skill")


if __name__ == "__main__":
    unittest.main()
