"""Fault isolation / state management / filename edge cases."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from liveclip.pipeline import (HighlightPipeline, SessionDB, SmartConfig,
                                rebuild_manifest, render_highlight)
from liveclip.signals import Peak, ocr_keywords, probe_video, analyze_segment
from test_smart import synthesize


class DbStateTests(unittest.TestCase):
    def test_recovery_dedupe_review_and_atomic_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            db = SessionDB(folder)
            try:
                peak = Peak(8, 35.2, ['audio_surge'], {'audio_surge': 1}, [])
                self.assertEqual(db.insert_candidate(0, 1, 8., peak, 20), 'new')
                self.assertEqual(db.insert_candidate(0, 1, 9., peak, 20), 'duplicate')
                improved = Peak(10, 55.5, ['screen_text'], {}, ['VICTORY'])
                self.assertEqual(db.insert_candidate(0, 1, 10., improved, 20), 'upgraded')
                self.assertEqual(len(db.pending()), 1)
                self.assertAlmostEqual(db.pending()[0]['peak_time'], 10)
                db.mark(1, 'rendering')
                db.repair_interrupted()
                self.assertEqual(db.pending()[0]['status'], 'pending')
                db.mark(1, 'exported', 'highlights/highlight_00001_056.mp4')
                with db.connection:
                    db.connection.execute('UPDATE candidates SET review_status=? WHERE id=1', ('keep',))
                rebuild_manifest(folder, db)
                data = json.loads((folder / 'highlights.jsonl').read_text().strip())
                self.assertEqual(data['review_status'], 'keep')
                self.assertEqual(data['ocr_matches'], ['VICTORY'])
                self.assertEqual(db.insert_candidate(0, 1, 11., improved, 20), 'duplicate')
                # Rebuilding is not an append; report remains exactly one row.
                rebuild_manifest(folder, db)
                self.assertEqual(len((folder/'highlights.jsonl').read_text().splitlines()), 1)
                self.assertEqual(len((folder/'highlights_review.csv').read_text().splitlines()), 2)
            finally:
                db.close()

    def test_bad_config_rejected(self):
        for threshold in (-5, 101):
            with self.assertRaises(ValueError):
                SmartConfig(threshold=threshold).validate()
        with self.assertRaises(ValueError):
            SmartConfig(highlight_seconds=0).validate()


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class MediaEdgeTests(unittest.TestCase):
    def test_quoted_unicode_path_and_missing_audio(self):
        with tempfile.TemporaryDirectory(prefix="it's✨live-") as tmp:
            folder = Path(tmp)
            subprocess.run([shutil.which('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-y',
                            '-f', 'lavfi', '-i', 'testsrc2=s=160x90:r=5', '-t', '5', '-an',
                            '-c:v', 'libx264', '-g', '5', str(folder/'clip_000001.mp4')],
                           capture_output=True, check=True, timeout=30)
            db = SessionDB(folder)
            try:
                file = folder/'clip_000001.mp4'
                self.assertFalse(probe_video(file).audio)
                db.add_segment(1, file, 0, 0., 5.)
                db.insert_candidate(0,1,2.,Peak(2.,55.,['motion'],{'motion':1},[]),5)
                dest, sec = render_highlight(folder, db.pending()[0], db.segments(),
                                             SmartConfig(highlight_seconds=15))
                self.assertTrue(dest.exists())
                self.assertGreater(probe_video(dest).seconds, 2)
            finally:
                db.close()

    def test_gap_marker_epoch_separation(self):
        with tempfile.TemporaryDirectory(prefix='liveclip_gap_') as tmp:
            folder = Path(tmp)
            synthesize(folder, 26)
            # Clip_000002 should form a new continuity epoch.
            (folder / 'gap_before_000002.marker').touch()
            worker = HighlightPipeline(folder, SmartConfig(profile='Gaming', threshold=10,
                                               highlight_seconds=15, cooldown_seconds=7))
            worker.start(already_finished=True)
            worker.join(timeout=60)
            self.assertFalse(worker.active)
            db = SessionDB(folder)
            try:
                epochs = [r['epoch'] for r in db.segments()]
                self.assertEqual(epochs[0], 0)
                self.assertEqual(epochs[-1], 1)
            finally:
                db.close()

    @unittest.skipUnless(shutil.which('tesseract'), 'Tesseract local OCR not installed')
    def test_optional_ocr_static_banner(self):
        with tempfile.TemporaryDirectory(prefix='liveclip_ocr_') as tmp:
            folder = Path(tmp)
            target = folder/'clip_000001.mp4'
            font = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
            if not Path(font).exists():
                self.skipTest('Synthetic OCR fixture font unavailable')
            subprocess.run([shutil.which('ffmpeg'), '-hide_banner','-loglevel','error','-y',
                            '-f','lavfi','-i','color=c=black:s=640x360:r=5',
                            '-vf',f'drawtext=fontfile={font}:text=VICTORY:fontsize=96:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2',
                            '-t','5','-c:v','libx264','-pix_fmt','yuv420p',str(target)],
                           capture_output=True, check=True, timeout=30)
            matches = ocr_keywords(target, 2.5)
            self.assertIn('VICTORY', matches)
            info, peaks = analyze_segment(target, 'Gaming', ocr=True)
            self.assertTrue(any('screen_text' in p.reasons for p in peaks))
            self.assertGreater(max(p.score for p in peaks), 35)


if __name__ == '__main__':
    unittest.main(verbosity=2)
