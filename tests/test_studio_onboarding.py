"""User-onboarding and first-party local Shorts Studio regression tests.

No remote video, browser sessions, model downloads or service credentials.
"""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from liveclip import __version__
from liveclip.studio import make_vod_args, demo_ffmpeg_args


class StudioArguments(unittest.TestCase):
    def test_brand_version_and_default_studio_settings(self):
        self.assertEqual(__version__, "2.4.0")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "my gameplay.mp4"
            source.write_bytes(b"local-test-input")
            dst = Path(tmp) / "exports"
            args = make_vod_args(source, dst)
            self.assertEqual(args[0], "vod")
            self.assertEqual(args[args.index("--count") + 1], "3")
            self.assertEqual(args[args.index("--seconds") + 1], "30")
            self.assertEqual(args[args.index("--profile") + 1], "balanced")
            self.assertEqual(args[args.index("--layout") + 1], "blur")

    def test_reject_unsupported_or_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "dummy.mp4"
            source.write_bytes(b"x")
            out = Path(tmp) / "clips"
            with self.assertRaises(ValueError):
                make_vod_args(Path(tmp) / "missing.mp4", out)
            with self.assertRaises(ValueError):
                make_vod_args(source, out, count=999)
            with self.assertRaises(ValueError):
                make_vod_args(source, out, profile="not-a-real-profile")
            with self.assertRaises(ValueError):
                make_vod_args(source, out, layout="stack")
            source.with_suffix(".txt").write_text("x")
            with self.assertRaises(ValueError):
                make_vod_args(source.with_suffix(".txt"), out)

    def test_build_demo_is_local_and_does_not_fetch_media(self):
        with patch("liveclip.studio.shutil.which", return_value="/usr/bin/ffmpeg"):
            cmd = demo_ffmpeg_args(Path("/tmp/demo.mp4"))
        self.assertIn("lavfi", cmd)
        self.assertIn("-nostdin", cmd)
        self.assertIn("testsrc2=size=320x180:rate=12:duration=36", cmd)
        self.assertTrue(cmd[-1].endswith(".mp4"))

    def test_launcher_and_notices_preserved(self):
        root = Path(__file__).resolve().parents[1]
        win = (root / "START_WINDOWS.bat").read_text()
        self.assertIn(".[neon]", win)
        self.assertTrue((root / "CHECK_SETUP_WINDOWS.bat").is_file())
        self.assertTrue((root / "docs" / "QUICK_START.md").is_file())
        self.assertTrue((root / "THIRD_PARTY_LICENSES" / "NeonClipping-MIT.txt").is_file())
        self.assertTrue((root / "THIRD_PARTY_LICENSES" / "GTA-Auto-Clipper-MIT.txt").is_file())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe required")
class StudioSyntheticVideo(unittest.TestCase):
    def test_generate_demo_and_create_real_portrait_highlight(self):
        from liveclip.neon_adopt.cli import main, _media_info
        with tempfile.TemporaryDirectory(prefix="studio-e2e-") as tmp:
            source = Path(tmp) / "demo.mp4"
            results = Path(tmp) / "highlights"
            proc = subprocess.run(demo_ffmpeg_args(source), capture_output=True,
                                  timeout=90)
            if proc.returncode:
                self.fail("FFmpeg demo failed: " + proc.stderr.decode("utf-8", "replace")[-1000:])
            self.assertTrue(source.is_file())
            source_before = source.stat().st_size
            info = _media_info(source)
            self.assertGreater(info["duration"], 30)
            args = make_vod_args(source, results, count=1, seconds=15,
                                 profile="balanced", layout="blur")
            self.assertEqual(main(args), 0)
            selected = list(results.glob("highlight_*.mp4"))
            self.assertTrue(selected, "Studio should export at least one 15s demo highlight")
            rendered = _media_info(selected[0])
            self.assertEqual((rendered["width"], rendered["height"]), (720, 1280))
            self.assertGreater(rendered["duration"], 1.0)
            self.assertEqual(source.stat().st_size, source_before)
            manifest = json.loads((results / "candidates.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["outputs"])


if __name__ == "__main__":
    unittest.main()
