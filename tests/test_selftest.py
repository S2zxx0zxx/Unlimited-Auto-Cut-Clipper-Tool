"""Offline smoke test of the FFmpeg segmenter using a synthetic, silent test video."""
from pathlib import Path
import subprocess
import tempfile
from liveclip.capture import command_for_segments, ffmpeg_executable, next_clip_number, validate_url


def run():
    assert validate_url("https://www.youtube.com/watch?v=example")
    for invalid in ("javascript:alert(1)", "file:///x", "https://user:secret@example.com/x", "http://localhost/watch"):
        try:
            validate_url(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted invalid URL {invalid}")
    ffmpeg = ffmpeg_executable()
    with tempfile.TemporaryDirectory(prefix="liveclip_smoketest_") as tmp:
        folder = Path(tmp)
        source = folder / "synthetic.ts"
        gen = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10", "-t", "4.1", "-c:v", "libx264", "-g", "10", "-f", "mpegts", str(source)]
        subprocess.run(gen, check=True, stdout=subprocess.DEVNULL)
        with source.open("rb") as stream:
            output = subprocess.run(command_for_segments(ffmpeg, 1, 1, folder), stdin=stream, capture_output=True, text=True)
        assert output.returncode == 0, output.stderr
        clips = list(folder.glob("clip_*.mp4"))
        assert len(clips) >= 3, f"Expected >=3 clips, got {len(clips)}"
        assert next_clip_number(folder) == len(clips) + 1
        for clip in clips:
            assert clip.stat().st_size > 100, f"Empty clip: {clip}"
        print(f"PASS: FFmpeg generated {len(clips)} local synthetic clips; URL + numbering checks passed")


if __name__ == "__main__":
    run()
