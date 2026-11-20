"""Precision moment and private localhost control acceptance tests."""
from __future__ import annotations

from http.client import HTTPConnection
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread
import unittest

from liveclip.moments import LENGTH_OPTIONS, candidate_window, propose_moments
from liveclip.pipeline import SmartConfig, SessionDB, render_highlight, rebuild_manifest
from liveclip.studio import make_vod_args
from liveclip.web_studio import HOST, make_server


class PrecisionMoments(unittest.TestCase):
    def test_options_are_explicit_not_unlimited(self):
        self.assertEqual(LENGTH_OPTIONS[-1], 300)
        SmartConfig(highlight_seconds=300, precision=True).validate()
        with self.assertRaises(ValueError):
            SmartConfig(highlight_seconds=301).validate()

    def test_moments_reject_random_cut_single_flash_or_silence(self):
        zeros = [0] * 100
        cuts = list(zeros);cuts[50] = 1
        self.assertEqual(propose_moments(zeros, zeros, zeros, cuts, maximum_seconds=300), [])
        audio = list(zeros);audio[50] = 1
        self.assertEqual(propose_moments(zeros, audio, zeros, zeros, maximum_seconds=60), [])

    def test_correlated_activity_has_context_and_not_60s_of_filler(self):
        n = 150
        motion, loud, shout, cuts = ([0.] * n for _ in range(4))
        for i in range(60, 71):
            motion[i] = .86
            loud[i] = .73
            shout[i] = .74
        found = propose_moments(motion, loud, shout, cuts, maximum_seconds=300)
        self.assertEqual(len(found), 1)
        item = found[0]
        self.assertLess(item.start, 60)
        self.assertGreater(item.end, 70)
        self.assertLess(item.end - item.start, 60)
        self.assertIn("visual_motion", item.evidence)
        self.assertIn("audio_surge", item.evidence)
        self.assertEqual(item.confidence, "activity-evidence-only")

    def test_long_racing_like_activity_can_span_over_four_minutes(self):
        n = 400
        motion, loud = [0.] * n, [0.] * n
        for i in range(50, 310):
            motion[i], loud[i] = .82, .64
        found = propose_moments(motion, loud, [0.] * n, [0.] * n,
                                maximum_seconds=300)
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0].end - found[0].start, 250)
        self.assertLessEqual(found[0].end - found[0].start, 300)

    def test_live_long_clip_refuses_single_random_peak(self):
        self.assertIsNone(candidate_window(120, [120], limit=300,
                                           epoch_start=0,epoch_end=300))
        window = candidate_window(120, [70,110,120,155,186], limit=300,
                                  epoch_start=0,epoch_end=300)
        self.assertIsNotNone(window)
        self.assertGreater(window[1] - window[0], 100)

    def test_no_reconnect_epoch_crossing(self):
        interval = candidate_window(40, [21,33,46], limit=90,
                                    epoch_start=20,epoch_end=50)
        self.assertIsNotNone(interval)
        self.assertGreaterEqual(interval[0], 20)
        self.assertLessEqual(interval[1], 50)

    def test_persisted_windows_reject_duplicate_long_live_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = SessionDB(root)
            try:
                db.mark(12345, "exported", "highlights/not-found.mp4",
                        window=(10., 170.))  # unknown candidate IDs are no-op
                from liveclip.signals import Peak
                peak = Peak(50, 70., ["audio_surge", "rapid_motion"],
                            {"audio_surge":.8,"motion":.9}, [])
                self.assertEqual(db.insert_candidate(0,1,50,peak,10),"new")
                row = db.pending()[0]
                db.mark(row["id"],"exported","highlights/clip.mp4",window=(20.,150.))
                self.assertTrue(db.overlapping_export(0,80.,190.))
                self.assertFalse(db.overlapping_export(0,180.,245.))
                rebuild_manifest(root,db)
                info = json.loads((root / "highlights.jsonl").read_text().splitlines()[0])
                self.assertEqual(info["window_start"],20)
                self.assertEqual(info["window_end"],150)
            finally:
                db.close()

    def test_vod_validates_precision_and_300s_without_new_engine(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "test.mp4"
            source.write_bytes(b"local")
            args = make_vod_args(source, root / "output",
                                 count=3, seconds=300,precision=True)
            self.assertIn("--precision", args)
            self.assertIn("300", args)


class WebLocalSecurity(unittest.TestCase):
    def test_host_token_origin_and_browser_controls(self):
        server = make_server()
        thread = Thread(target=server.serve_forever,daemon=True)
        thread.start()
        host = f"{HOST}:{server.server_port}"
        try:
            conn = HTTPConnection(HOST,server.server_port,timeout=10)
            conn.request("GET","/",headers={"Host":host})
            resp = conn.getresponse()
            page = resp.read().decode()
            self.assertEqual(resp.status,200)
            self.assertIn("PRIVATE",page.upper())
            self.assertIn("▶ START LIVE + SMART",page)
            self.assertIn(server.token,page)
            conn.request("GET","/api/state",headers={"Host":host})
            resp=conn.getresponse();resp.read()
            self.assertEqual(resp.status,403)
            conn.request("GET","/api/state",headers={"Host":host,"X-LiveClip-Token":server.token})
            resp=conn.getresponse();data=json.loads(resp.read())
            self.assertEqual(resp.status,200)
            self.assertEqual(data["status"],"Ready")
            conn.request("POST","/api/start-live",body="{}",
                         headers={"Host":host,"Content-Type":"application/json",
                                  "X-LiveClip-Token":server.token,
                                  "Origin":"https://evil.test"})
            resp=conn.getresponse();resp.read()
            self.assertEqual(resp.status,403)
            conn.request("POST","/api/start-live",body="{}",
                         headers={"Host":host,"Content-Type":"application/json",
                                  "X-LiveClip-Token":server.token,
                                  "Origin":f"http://{host}"})
            resp=conn.getresponse();text=json.loads(resp.read())
            self.assertEqual(resp.status,400)
            self.assertTrue(any(term in text["error"].lower()
                                for term in ("permission", "rights", "own", "record")))
            conn.request("GET","/",headers={"Host":"foreign-domain.example"})
            resp=conn.getresponse();resp.read()
            self.assertEqual(resp.status,403)
            conn.close()
        finally:
            server.shutdown();server.server_close()
            thread.join(timeout=5)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
class LongRenderer(unittest.TestCase):
    def test_300_second_highlight_crosses_five_small_finalized_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            proc=subprocess.run([
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","testsrc2=size=96x64:rate=2:duration=300",
                "-c:v","mpeg4","-q:v","8","-g","120",
                "-f","segment","-segment_time","60","-reset_timestamps","1",
                str(root/"clip_%06d.mp4"),
            ],capture_output=True,timeout=100)
            self.assertEqual(proc.returncode,0,proc.stderr[-1000:])
            segments=[]
            t=0.
            for index,path in enumerate(sorted(root.glob("clip_*.mp4"))):
                data=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                     "-of","default=noprint_wrappers=1:nokey=1",str(path)],
                                    check=True,capture_output=True,text=True,timeout=15)
                duration=float(data.stdout.strip())
                segments.append({"epoch":0,"timeline_start":t,"duration":duration,"filename":path.name})
                t+=duration
            self.assertGreaterEqual(len(segments),5)
            self.assertGreaterEqual(t,299.)
            row={"id":2,"score":76.,"peak_time":150.,"epoch":0}
            file,seconds=render_highlight(root,row,segments,
                            SmartConfig(highlight_seconds=300),window=(0.,300.))
            self.assertTrue(file.exists())
            self.assertGreater(file.stat().st_size,1500)
            self.assertGreater(seconds,299.)
            probe=subprocess.run(["ffprobe","-v","error","-show_entries",
                                  "format=duration","-of","default=noprint_wrappers=1:nokey=1",
                                  str(file)],capture_output=True,text=True,check=True)
            self.assertGreater(float(probe.stdout.strip()),298.)
            self.assertLessEqual(float(probe.stdout.strip()),301.)

if __name__ == "__main__":
    unittest.main()
