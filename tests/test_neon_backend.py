"""Regression tests for optional NeonClipping-derived backend (no network access)."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from liveclip.neon_adopt import aiparts, curation, layouts, subtitles, translit
from liveclip.neon_adopt.chat_hype import is_spike, analyze_bucket, hype_percent
from liveclip.neon_adopt.cli import verticalize, main
from liveclip.neon_adopt.source_download import validate_vod_url, download_public_vod


class NeonBackendLogic(unittest.TestCase):
    def test_all_eleven_layouts_have_bounded_geometry(self):
        self.assertEqual(len(layouts.CATALOG), 11)
        for name, *_ in layouts.CATALOG:
            geometry = layouts.geometry(name, .32, 720, 1280)
            self.assertEqual((geometry["width"], geometry["height"]), (720, 1280))
            for layer in geometry["layers"]:
                self.assertGreater(layer["w"], 0)
                self.assertGreater(layer["h"], 0)
                self.assertGreaterEqual(layer["x"], 0)
                self.assertGreaterEqual(layer["y"], 0)
                self.assertLessEqual(layer["x"] + layer["w"], 720)
                self.assertLessEqual(layer["y"] + layer["h"], 1280)

    def test_vod_url_allowlist_and_rights_gate(self):
        good = "https://www.youtube.com/watch?v=abcdefghijk"
        self.assertEqual(validate_vod_url(good), good)
        for bad in ("http://youtube.com/watch?v=abcdefghijk",
                    "https://youtube.com.evil.example/watch",
                    "https://127.0.0.1/video",
                    "https://user:pass@youtube.com/watch?v=abcdefghijk",
                    "https://kick.com:8080/private"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_vod_url(bad)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                download_public_vod(good, Path(tmp), authorized=False)
            self.assertEqual(main(["vod-url", good, str(Path(tmp)), "--count", "2"]), 2)

    def test_subtitle_round_trip(self):
        srt = "1\n00:00:01,000 --> 00:00:02,200\nHello दुनिया\n"
        cues = subtitles.parse_track(srt)
        output = subtitles.write_track(cues, "vtt")
        self.assertTrue(output.startswith("WEBVTT"))
        self.assertEqual(subtitles.parse_track(output), cues)

    def test_chat_spike_rule_needs_history(self):
        self.assertFalse(is_spike(80, [0] * 30))
        self.assertTrue(is_spike(50, [2] * 12))
        r = analyze_bucket(50, [2] * 12, 80)
        self.assertTrue(r.is_spike)
        self.assertTrue(r.sufficient_history)
        self.assertGreater(r.score, 25)
        with self.assertRaises(ValueError):
            analyze_bucket(-1, [2] * 12)

    def test_transcript_parts_and_hinglish(self):
        words = [{"start": i * 30, "end": i * 30 + .3, "text": "Hello"} for i in range(30)]
        prompts = aiparts.split("Authorized example", words, 900, parts=3)
        self.assertEqual(len(prompts), 3)
        self.assertIn("TRANSCRIPT:", prompts[0]["prompt"])
        self.assertIsInstance(translit.to_hinglish("नमस्ते"), str)

    def test_curate_near_duplicate(self):
        clips = [{"start": 0, "end": 20, "rank": .9, "transcript": "hello"},
                 {"start": 5, "end": 22, "rank": .8, "transcript": "hello"},
                 {"start": 60, "end": 80, "rank": .7, "transcript": "different"}]
        chosen = curation.select(clips, 3)
        self.assertEqual(len(chosen), 2)
        self.assertEqual([x["start"] for x in chosen], [0, 60])

    def test_invalid_layout(self):
        with self.assertRaises(ValueError):
            layouts.geometry("not-a-real-layout")

    def test_caption_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "source.srt"
            out = Path(tmp) / "output.vtt"
            inp.write_text("1\n00:00:00,000 --> 00:00:01,500\nCaption\n", encoding="utf-8")
            self.assertEqual(main(["captions-convert", str(inp), str(out), "--format", "vtt"]), 0)
            self.assertTrue(out.read_text().startswith("WEBVTT"))

    def test_curate_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "candidates.json"
            out = Path(tmp) / "selected.json"
            inp.write_text(json.dumps([{"start": 1, "end": 20, "rank": 1.0}]))
            self.assertEqual(main(["curate-json", str(inp), str(out)]), 0)
            self.assertEqual(len(json.loads(out.read_text())), 1)

    def test_transcript_parts_cli_accepts_asr_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "transcript.words.json"
            dest = Path(tmp) / "parts.json"
            source.write_text(json.dumps({"words": [{"start": .5, "end": .8, "text": "Hello"},
                                                    {"start": 20.5, "end": 20.8, "text": "world."}]}), encoding="utf-8")
            self.assertEqual(main(["transcript-parts", str(source), str(dest),
                                   "--duration", "60", "--parts", "1"]), 0)
            self.assertEqual(len(json.loads(dest.read_text())["parts"]), 1)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe required")
class NeonBackendMedia(unittest.TestCase):
    def synthetic(self, path):
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=12:duration=2",
               "-f", "lavfi", "-i", "sine=frequency=750:sample_rate=16000:duration=2",
               "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=45)

    def test_vertical_blur_export_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.mp4"
            out = Path(tmp) / "highlights" / "vertical.mp4"
            self.synthetic(source)
            original = source.stat().st_size
            result = verticalize(source, out, duration=1.5)
            self.assertTrue(out.is_file())
            self.assertEqual((result["width"], result["height"]), (720, 1280))
            self.assertGreater(out.stat().st_size, 1000)
            self.assertEqual(source.stat().st_size, original)
            self.assertTrue(result["source_preserved"])
            with self.assertRaises(FileExistsError):
                verticalize(source, out, duration=1)

    def test_requires_explicit_face_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.mp4"
            self.synthetic(source)
            with self.assertRaisesRegex(ValueError, "--cam-box"):
                verticalize(source, Path(tmp) / "out.mp4", layout="stack", duration=1)

    def test_sidecar_subtitle_without_libass(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.mp4"
            track = Path(tmp) / "words.srt"
            output = Path(tmp) / "short.mp4"
            self.synthetic(source)
            track.write_text("1\n00:00:00,000 --> 00:00:01,500\nHello world\n", encoding="utf-8")
            response = verticalize(source, output, duration=1.5, captions_file=track)
            self.assertEqual(response["captions_burned"], False)
            self.assertTrue(output.with_suffix(".srt").exists())


if __name__ == "__main__":
    unittest.main()
