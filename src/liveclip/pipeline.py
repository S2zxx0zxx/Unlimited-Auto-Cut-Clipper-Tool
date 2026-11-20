"""Recoverable, local media analysis and highlight rendering pipeline.

SQLite is an idempotent event journal. 'pending' candidates are exported only
when necessary later segments are complete. Files are never silently deleted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from typing import Callable

from .signals import analyze_segment, probe_video
from .moments import LENGTH_OPTIONS, candidate_window

SEGMENT_RE = re.compile(r'^clip_(\d{6})\.mp4$')


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass(frozen=True)
class SmartConfig:
    profile: str = 'Gaming'
    threshold: float = 18.0
    highlight_seconds: int = 30
    cooldown_seconds: int = 25
    ocr: bool = False
    poll_seconds: float = 1.0
    precision: bool = False  # Opt-in from desktop/web; preserves existing CLI/test sessions

    def validate(self):
        from .signals import PROFILES
        if self.profile not in PROFILES:
            raise ValueError('Invalid smart profile')
        if not 0 <= self.threshold <= 100:
            raise ValueError('Threshold must be 0 to 100')
        if self.highlight_seconds not in LENGTH_OPTIONS:
            raise ValueError('Highlight length must be 15–300 seconds')
        if not 0 <= self.cooldown_seconds <= 240:
            raise ValueError('Cooldown must be between 0 and 240 seconds')
        if not .2 <= self.poll_seconds <= 15:
            raise ValueError('Poll interval out of range')


class SessionDB:
    def __init__(self, folder: Path):
        self.folder = folder
        self.connection = sqlite3.connect(str(folder / 'smart_index.sqlite3'), timeout=20)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA busy_timeout=20000')
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY,
                number INTEGER UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                timeline_start REAL NOT NULL,
                duration REAL NOT NULL,
                analyzed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epoch INTEGER NOT NULL,
                segment_number INTEGER NOT NULL,
                peak_time REAL NOT NULL,
                score REAL NOT NULL,
                reasons_json TEXT NOT NULL,
                signals_json TEXT NOT NULL,
                ocr_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                output_name TEXT,
                error TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS candidates_by_epoch ON candidates(epoch,peak_time);
        ''')
        # Forward-compatible migration for sessions created by early smart builds.
        columns = {row[1] for row in self.connection.execute('PRAGMA table_info(candidates)')}
        if 'review_status' not in columns:
            self.connection.execute("ALTER TABLE candidates ADD COLUMN review_status TEXT NOT NULL DEFAULT 'unreviewed'")
        for column in ('window_start', 'window_end'):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE candidates ADD COLUMN {column} REAL")
        self.connection.commit()

    def segments(self) -> list[sqlite3.Row]:
        return list(self.connection.execute('SELECT * FROM segments ORDER BY number'))

    def last_segment(self) -> sqlite3.Row | None:
        return self.connection.execute('SELECT * FROM segments ORDER BY number DESC LIMIT 1').fetchone()

    def segment_numbers(self) -> set[int]:
        return {r['number'] for r in self.connection.execute('SELECT number FROM segments')}

    def add_segment(self, number: int, file: Path, epoch: int, start: float, duration: float):
        with self.connection:
            self.connection.execute('''INSERT OR IGNORE INTO segments
                (number,filename,epoch,timeline_start,duration,analyzed_at) VALUES(?,?,?,?,?,?)''',
                (number, file.name, epoch, start, duration, utc_now()))

    def insert_candidate(self, epoch: int, number: int, at: float, peak,
                         cooldown: int) -> str:
        # Prevent both overlapping pending exports and adjacent nearly-identical exports.
        existing = self.connection.execute('''SELECT * FROM candidates WHERE epoch=?
            AND ABS(peak_time-?)<=? AND status IN ('pending','rendering','exported')
            ORDER BY score DESC LIMIT 1''', (epoch, at, cooldown)).fetchone()
        if existing:
            if existing['status'] == 'pending' and peak.score > existing['score']:
                with self.connection:
                    self.connection.execute('''UPDATE candidates SET segment_number=?,peak_time=?,score=?,
                        reasons_json=?,signals_json=?,ocr_json=? WHERE id=?''',
                        (number, at, peak.score, json.dumps(peak.reasons),
                         json.dumps(peak.signals), json.dumps(peak.ocr_matches), existing['id']))
                return 'upgraded'
            return 'duplicate'
        with self.connection:
            self.connection.execute('''INSERT INTO candidates
                (epoch,segment_number,peak_time,score,reasons_json,signals_json,ocr_json,created_at)
                VALUES(?,?,?,?,?,?,?,?)''',
                (epoch, number, at, peak.score, json.dumps(peak.reasons),
                 json.dumps(peak.signals), json.dumps(peak.ocr_matches), utc_now()))
        return 'new'

    def pending(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM candidates WHERE status='pending' ORDER BY peak_time"))

    def exported(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM candidates WHERE status='exported' ORDER BY peak_time, id"))

    def mark(self, candidate_id: int, status: str, output_name: str | None = None,
             error: str | None = None, window: tuple[float, float] | None = None):
        with self.connection:
            self.connection.execute(
                """UPDATE candidates SET status=?,output_name=?,error=?,
                   window_start=COALESCE(?,window_start),
                   window_end=COALESCE(?,window_end) WHERE id=?""",
                (status, output_name, error, window[0] if window else None,
                 window[1] if window else None, candidate_id))

    def overlapping_export(self, epoch: int, start: float, end: float) -> bool:
        """Deny near-identical long outputs; one meaningful event, one clip."""
        for row in self.connection.execute(
                """SELECT window_start,window_end FROM candidates
                   WHERE epoch=? AND status='exported'
                   AND window_start IS NOT NULL AND window_end IS NOT NULL""", (epoch,)):
            overlap = max(0, min(end, row['window_end']) - max(start, row['window_start']))
            shorter = min(end-start, row['window_end']-row['window_start'])
            if shorter > 0 and overlap / shorter > .45:
                return True
        return False

    def repair_interrupted(self):
        with self.connection:
            self.connection.execute("UPDATE candidates SET status='pending' WHERE status='rendering'")

    def stats(self) -> dict:
        return {
            'segments': self.connection.execute('SELECT COUNT(*) FROM segments').fetchone()[0],
            'candidates': self.connection.execute('SELECT COUNT(*) FROM candidates').fetchone()[0],
            'exported': self.connection.execute("SELECT COUNT(*) FROM candidates WHERE status='exported'").fetchone()[0],
            'failed': self.connection.execute("SELECT COUNT(*) FROM candidates WHERE status='error'").fetchone()[0],
        }

    def close(self):
        self.connection.close()


def _concat_quote(path: Path) -> str:
    # ffconcat syntax single quotes and backslash-escaping; no shell involved.
    return "'" + str(path.resolve()).replace("'", "'\\''") + "'"


def render_highlight(folder: Path, row: sqlite3.Row, segments: list[sqlite3.Row],
                     config: SmartConfig, window: tuple[float, float] | None = None) -> tuple[Path, float]:
    same_epoch = [s for s in segments if s['epoch'] == row['epoch']]
    if not same_epoch:
        raise ValueError('Candidate epoch not found')
    timeline_start = same_epoch[0]['timeline_start']
    timeline_end = same_epoch[-1]['timeline_start'] + same_epoch[-1]['duration']
    if window is not None:
        wanted_start = max(timeline_start, window[0])
        wanted_end = min(timeline_end, window[1])
    else:
        preroll = config.highlight_seconds * .40
        wanted_start = max(timeline_start, row['peak_time'] - preroll)
        wanted_end = min(timeline_end, wanted_start + config.highlight_seconds)
        wanted_start = max(timeline_start, wanted_end - config.highlight_seconds)
    # No clips across unexpected gaps/reconnect boundaries.
    selected = [s for s in same_epoch
                if s['timeline_start'] + s['duration'] > wanted_start + 1e-3
                and s['timeline_start'] < wanted_end - 1e-3]
    if not selected:
        raise RuntimeError('No finalized segments cover highlight')
    for s in selected:
        if not (folder / s['filename']).is_file():
            raise FileNotFoundError(f"Source segment was removed: {s['filename']}")
    duration = wanted_end - wanted_start
    if duration < 1.0:
        raise RuntimeError('Insufficient source media to make highlight')
    outdir = folder / 'highlights'
    outdir.mkdir(exist_ok=True)
    destination = outdir / f"highlight_{row['id']:05d}_{round(row['score']):03d}.mp4"
    partial = outdir / f"highlight_{row['id']:05d}.partial.mp4"
    if destination.exists() and destination.stat().st_size > 500:
        return destination, duration
    concat_file = outdir / f'.concat_{row["id"]:05d}.txt'
    concat_file.write_text('ffconcat version 1.0\n' + ''.join(
        f"file {_concat_quote(folder / s['filename'])}\n" for s in selected), encoding='utf-8')
    try:
        cmd = [shutil.which('ffmpeg') or 'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
               '-y', '-safe', '0', '-f', 'concat', '-i', str(concat_file),
               '-ss', str(max(0.0, wanted_start - selected[0]['timeline_start'])),
               '-t', str(duration), '-map', '0:v:0', '-map', '0:a?',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(partial)]
        completed = subprocess.run(cmd, capture_output=True, timeout=max(90, config.highlight_seconds * 8))
        if completed.returncode != 0 or not partial.exists() or partial.stat().st_size < 500:
            raise RuntimeError(completed.stderr.decode('utf-8', 'replace')[-800:])
        os.replace(partial, destination)
        # Thumbnails help humans quickly review heuristic picks; noncritical.
        try:
            subprocess.run([shutil.which('ffmpeg') or 'ffmpeg', '-hide_banner', '-loglevel', 'error',
                            '-nostdin', '-y', '-ss', '1', '-i', str(destination), '-frames:v', '1',
                            '-vf', 'scale=480:-2', str(destination.with_suffix('.jpg'))],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return destination, duration
    finally:
        concat_file.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)


def rebuild_manifest(folder: Path, db: SessionDB | None = None):
    """Materialize portable JSONL+CSV from committed SQLite export state."""
    import csv
    own = db is None
    db = db or SessionDB(folder)
    try:
        rows = db.exported()
        journal = []
        csv_rows = []
        for row in rows:
            data = {
                'id': row['id'], 'created_at': row['created_at'],
                'file': row['output_name'], 'peak_session_seconds': round(row['peak_time'], 2),
                'score': round(row['score'], 1), 'reasons': json.loads(row['reasons_json']),
                'signals': json.loads(row['signals_json']),
                'ocr_matches': json.loads(row['ocr_json']),
                'review_status': row['review_status'],
                'window_start': round(row['window_start'], 2) if row['window_start'] is not None else None,
                'window_end': round(row['window_end'], 2) if row['window_end'] is not None else None,
                'note': 'Heuristic ranking; manually inspect before publishing.'
            }
            journal.append(json.dumps(data, ensure_ascii=False))
            csv_rows.append([data['id'], data['file'], data['score'], data['peak_session_seconds'],
                             '; '.join(data['reasons']), '; '.join(data['ocr_matches']),
                             data['review_status']])
        unique = f'.tmp.{os.getpid()}.{threading.get_ident()}'
        jsonpath = folder / 'highlights.jsonl'
        json_tmp = folder / ('highlights.jsonl' + unique)
        json_tmp.write_text(('\n'.join(journal) + '\n') if journal else '', encoding='utf-8')
        os.replace(json_tmp, jsonpath)
        csvpath = folder / 'highlights_review.csv'
        csv_tmp = folder / ('highlights_review.csv' + unique)
        with csv_tmp.open('w', encoding='utf-8', newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow(['id','file','score','peak_session_seconds','reasons','ocr_matches','review_status'])
            writer.writerows(csv_rows)
        os.replace(csv_tmp, csvpath)
    finally:
        if own:
            db.close()


class HighlightPipeline:
    """One background worker per session. No tkinter calls from this worker."""
    def __init__(self, folder: Path, config: SmartConfig,
                 emit: Callable[[str, str], None] | None = None):
        config.validate()
        self.folder = folder.expanduser().resolve()
        self.config = config
        self.emit = emit or (lambda kind, msg: None)
        self._finish = threading.Event()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self.active = False
        self._last_scan_stamp = None
        self._last_deep_scan = 0.0

    def start(self, already_finished: bool = False):
        if self.active:
            raise RuntimeError('Pipeline already running')
        self.folder.mkdir(parents=True, exist_ok=True)
        self._finish.clear()
        self._cancel.clear()
        if already_finished:
            self._finish.set()
        self.active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def finish_capture(self):
        self._finish.set()

    def cancel(self):
        self._cancel.set()
        self._finish.set()

    def join(self, timeout: float | None = None):
        if self._thread:
            self._thread.join(timeout)

    def _scannable(self, known: set[int]) -> list[tuple[int, Path]]:
        # Directory metadata avoids re-globbing thousands of segments every
        # second during long, idle sessions. Periodic full scan is a fallback
        # for filesystems with coarse directory timestamps.
        now = time.monotonic()
        stamp = self.folder.stat().st_mtime_ns
        if (not self._finish.is_set() and stamp == self._last_scan_stamp
                and now - self._last_deep_scan < 30):
            return []
        self._last_scan_stamp = stamp
        self._last_deep_scan = now
        files: list[tuple[int, Path]] = []
        for file in self.folder.glob('clip_*.mp4'):
            match = SEGMENT_RE.fullmatch(file.name)
            if match and file.stat().st_size > 100:
                files.append((int(match.group(1)), file))
        files.sort()
        # FFmpeg's last MP4 is still open while recording. Only a newer segment
        # proves the prior MP4 was closed by the muxer.
        if not self._finish.is_set() and files:
            files = files[:-1]
        return [(num, file) for num, file in files if num not in known]

    def _log_export(self, db: SessionDB):
        # Deterministic manifest reconstructed from SQLite instead of append-only:
        # if the process crashes between DB commit and export log, next run repairs it.
        rebuild_manifest(self.folder, db)

    def _export_ready(self, db: SessionDB):
        pending = db.pending()
        if not pending:
            return
        segments = db.segments()
        for row in pending:
            if self._cancel.is_set():
                return
            current_epoch = [s for s in segments if s['epoch'] == row['epoch']]
            if not current_epoch:
                continue
            end = current_epoch[-1]['timeline_start'] + current_epoch[-1]['duration']
            required_end = row['peak_time'] + min(self.config.highlight_seconds * .60, 180)
            # Wait for post-roll, unless recording has stopped / folder is complete.
            if not self._finish.is_set() and end < required_end:
                continue
            window = None
            if self.config.precision:
                # A peak alone never proves a race/match event. Conservative
                # mode rejects weak or single-source random scene flashes.
                reasons = set(json.loads(row['reasons_json']))
                signals = json.loads(row['signals_json'])
                audio = signals.get('audio_surge', 0) >= .35 or signals.get('audio_onset', 0) >= .35
                video = signals.get('motion', 0) >= .35 or signals.get('scene', 0) >= .45
                text = bool(json.loads(row['ocr_json']))
                if not ((audio and video) or (text and (audio or video))):
                    db.mark(row['id'], 'rejected_weak', error='No independent evidence corroboration')
                    self.emit('smart_status', f"Skipped weak event #{row['id']}; no arbitrary highlight generated")
                    continue
                neighbours = [r['peak_time'] for r in db.connection.execute(
                    """SELECT peak_time FROM candidates
                       WHERE epoch=? AND peak_time BETWEEN ? AND ? AND score>=?
                       AND status IN ('pending','exported','rendering')""",
                    (row['epoch'], max(current_epoch[0]['timeline_start'],
                                      row['peak_time'] - self.config.highlight_seconds * .62),
                     end, max(self.config.threshold, 25)))]
                window = candidate_window(
                    row['peak_time'], neighbours, limit=self.config.highlight_seconds,
                    epoch_start=current_epoch[0]['timeline_start'], epoch_end=end)
                if window is None:
                    if self._finish.is_set():
                        db.mark(row['id'], 'rejected_weak',
                                error='Insufficient sustained evidence for requested clip length')
                    continue
                if not self._finish.is_set() and end < window[1] + 2:
                    continue
                if db.overlapping_export(row['epoch'], *window):
                    db.mark(row['id'], 'rejected_overlap',
                            error='An equivalent event interval was already exported')
                    self.emit('smart_status', f"Skipped overlapping candidate #{row['id']}")
                    continue
            # The source recorder independently enforces a low-space guard;
            # exports must not bypass it.
            if shutil.disk_usage(self.folder).free < 512 * 1024 * 1024:
                self.emit('error', 'Low disk space (<512 MiB): highlight exports paused; free space first.')
                return
            db.mark(row['id'], 'rendering')
            try:
                result, actual_seconds = render_highlight(self.folder, row, segments, self.config,
                                                           window=window)
                db.mark(row['id'], 'exported', str(result.relative_to(self.folder)),
                        window=window)
                # SQLite is authoritative, and reports are deterministically
                # reconciled periodically, at stop, and on resume/review.
                if db.stats()['exported'] % 20 == 0:
                    self._log_export(db)
                self.emit('highlight', f"#{row['id']} score {row['score']:.1f}: {result.name}")
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                db.mark(row['id'], 'error', error=str(exc)[:700])
                self.emit('error', f"Highlight #{row['id']} export failed: {str(exc)[:180]}")

    def _run(self):
        db: SessionDB | None = None
        try:
            db = SessionDB(self.folder)
            db.repair_interrupted()
            rebuild_manifest(self.folder, db)
            self.emit('smart_status', f'Smart analysis started: {self.config.profile}')
            # Retry ffprobe failures only after a newer MP4 appears, or at finalization.
            failed_files: set[int] = set()
            known = db.segment_numbers()
            while not self._cancel.is_set():
                pending = self._scannable(known)   # finalized files only
                made_progress = False
                for number, path in pending:
                    if self._cancel.is_set():
                        break
                    if number in failed_files and not self._finish.is_set():
                        continue
                    try:
                        # Analyze *before* registering, so an interrupted scan may be retried.
                        info, peaks = analyze_segment(path, self.config.profile, self.config.ocr)
                        last = db.last_segment()
                        if last:
                            # `gap_before_<number>` is written on each Streamlink reconnect.
                            gaps = any((self.folder / f'gap_before_{i:06d}.marker').exists()
                                       for i in range(last['number'] + 1, number + 1))
                            epoch = last['epoch'] + (1 if gaps or number != last['number'] + 1 else 0)
                            timeline_start = last['timeline_start'] + last['duration']
                        else:
                            epoch = 0
                            timeline_start = 0.0
                        # Ensure a segment row and its candidates are journaled consistently.
                        db.add_segment(number, path, epoch, timeline_start, info.seconds)
                        known.add(number)
                        self.emit('smart_status', f"Analyzed segment {number}: {info.seconds:.1f}s")
                        for peak in peaks:
                            if peak.score < self.config.threshold:
                                continue
                            decision = db.insert_candidate(epoch, number, timeline_start + peak.at,
                                                           peak, self.config.cooldown_seconds)
                            if decision in ('new', 'upgraded'):
                                self.emit('candidate', f"Candidate {peak.score:.1f}/100 @ {timeline_start + peak.at:.1f}s ({decision})")
                        failed_files.discard(number)
                        made_progress = True
                    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                        failed_files.add(number)
                        self.emit('error', f"Segment {number} skipped until retry: {str(exc)[:200]}")
                self._export_ready(db)
                if self._finish.is_set():
                    # Finalized session: last closed MP4 has now been scanned.
                    if not self._scannable(known):
                        break
                    # Faulty source files must not stall the worker indefinitely.
                    if not made_progress:
                        break
                self._cancel.wait(self.config.poll_seconds)
            rebuild_manifest(self.folder, db)
            self.emit('smart_status', 'Smart analysis finished. ' + str(db.stats()))
        except Exception as exc:
            self.emit('error', f'Smart pipeline failed: {exc}')
        finally:
            if db:
                db.close()
            self.active = False
            self.emit('smart_finished', '')
