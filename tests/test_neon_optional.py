"""Optional NumPy/OpenCV smoke tests for MIT-derived VOD scoring."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

if importlib.util.find_spec("numpy") is not None and importlib.util.find_spec("cv2") is not None:
    from liveclip.neon_adopt.highlights import rank
    from liveclip.neon_adopt import smart
else:
    rank = smart = None


@unittest.skipUnless(rank is not None and shutil.which("ffmpeg"), "Install optional neon extras + FFmpeg")
class NeonOptionalTests(unittest.TestCase):
    def test_streamed_audio_rank(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "activity.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=12:duration=8",
                            "-f", "lavfi", "-i", "sine=frequency=500:duration=8",
                            "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(video)],
                           check=True, timeout=45, capture_output=True)
            candidates = rank(str(video), 8.0, count=2, length=3, motion_on=False)
            self.assertGreaterEqual(len(candidates), 1)
            self.assertLessEqual(len(candidates), 2)
            self.assertIn("features", candidates[0])

    def test_imported_semantic_core_without_ollama(self):
        self.assertTrue(callable(smart.snap))
        self.assertTrue(callable(smart.find))
        result = {"start": 2.0, "end": 15.0}
        words = [{"start": 0.0, "end": .3, "text": "This"},
                 {"start": .4, "end": .8, "text": "works."}]
        smart.snap(result, words, min_len=2.0, max_len=15.0)
        self.assertGreater(result["end"], result["start"])


if __name__ == "__main__":
    unittest.main()
