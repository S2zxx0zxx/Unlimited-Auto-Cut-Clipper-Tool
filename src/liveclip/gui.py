"""Cross-platform desktop control for capture + offline heuristic highlight ranking."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .capture import Recorder, CaptureConfig
from .pipeline import HighlightPipeline, SmartConfig, SessionDB, rebuild_manifest
from .signals import PROFILES
from .studio import LocalShortsStudio

APP_TITLE = 'LiveClip Zero Studio — Local Highlights'
SETTINGS = Path.home() / '.liveclip_zero_smart_settings.json'
BG = '#111722'
FG = '#f4f7ff'
MUTED = '#aab7c8'


def open_path(path: Path):
    if not path.exists():
        return
    if sys.platform == 'win32':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(path)])
    else:
        subprocess.Popen(['xdg-open', str(path)])


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry('980x790')
        self.root.minsize(800, 690)
        self.events: queue.Queue = queue.Queue()
        self.recorder = Recorder(self.events)
        self.pipeline: HighlightPipeline | None = None
        self.folder: Path | None = None
        try:
            saved = json.loads(SETTINGS.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            saved = {}
        self.url = tk.StringVar(value='')
        self.duration = tk.StringVar(value=str(saved.get('seconds', 30)))
        self.quality = tk.StringVar(value=saved.get('quality', 'best'))
        self.output = tk.StringVar(value=saved.get('output', str(Path.home() / 'Videos' / 'LiveClipZero')))
        self.profile = tk.StringVar(value=saved.get('profile', 'Gaming'))
        self.sensitivity = tk.StringVar(value=saved.get('sensitivity', 'Balanced (22)'))
        self.highlight_duration = tk.StringVar(value=str(saved.get('highlight_duration', 30)))
        self.cooldown = tk.StringVar(value=str(saved.get('cooldown', 25)))
        self.ocr = tk.BooleanVar(value=bool(saved.get('ocr', False)))
        self.status = tk.StringVar(value='Ready — authorized stream URL or existing clip folder')
        self.smart_status = tk.StringVar(value='Smart detector idle')
        self.counter = tk.StringVar(value='Segments: 0   •   Highlights: 0')
        self._closing = False
        self._last_review_folder = None
        self._review_tick = 0
        self._create_ui()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.after(350, self.poll_events)

    def _create_ui(self):
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=FG, font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'), foreground='#ffffff')
        style.configure('Hint.TLabel', foreground=MUTED, font=('Segoe UI', 9))
        style.configure('TButton', padding=(13, 8), font=('Segoe UI', 10, 'bold'))
        style.configure('TEntry', padding=5)
        style.configure('TCombobox', padding=5)
        style.configure('TCheckbutton', background=BG, foreground=FG)
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='LIVECLIP ZERO STUDIO', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Private by default  •  Zero paid APIs  •  Auto-record + highlight candidates  •  Manual review recommended',
                  style='Hint.TLabel').pack(anchor='w', pady=(3, 12))
        tabs = ttk.Notebook(outer)
        tabs.pack(fill='x')
        live_tab = ttk.Frame(tabs, padding=13)
        replay_tab = ttk.Frame(tabs, padding=13)
        review_tab = ttk.Frame(tabs, padding=13)
        tabs.add(live_tab, text='Live + Smart')
        tabs.add(replay_tab, text='Analyze existing folder')
        tabs.add(review_tab, text='Review highlights')
        self.studio = LocalShortsStudio(
            tabs, self.root,
            lambda: not self.recorder.active and not bool(self.pipeline and self.pipeline.active),
            self.note,
        )
        tabs.select(self.studio.frame)
        ttk.Label(live_tab, text='Livestream URL (Streamlink-supported, authorized sources)').pack(anchor='w')
        ttk.Entry(live_tab, textvariable=self.url).pack(fill='x', pady=(6, 12))
        live_opts = ttk.Frame(live_tab)
        live_opts.pack(fill='x')
        for index, (title, var, choices) in enumerate((
            ('Segment every', self.duration, ['30', '60']),
            ('Stream quality', self.quality, ['best', '720p', '480p', 'worst']),
        )):
            ttk.Label(live_opts, text=title).grid(row=0, column=index, sticky='w', padx=(0, 16))
            ttk.Combobox(live_opts, textvariable=var, values=choices, state='readonly', width=13).grid(
                row=1, column=index, sticky='w', padx=(0, 16), pady=(5, 12))
        ttk.Label(live_tab, text='Output folder (source segments are preserved)').pack(anchor='w')
        output_row = ttk.Frame(live_tab)
        output_row.pack(fill='x', pady=(5, 8))
        ttk.Entry(output_row, textvariable=self.output).pack(side='left', fill='x', expand=True)
        ttk.Button(output_row, text='Browse', command=self.browse).pack(side='left', padx=(8, 0))

        ttk.Label(replay_tab, text='Already recorded? Analyze any folder containing clip_000001.mp4, clip_000002.mp4, etc.').pack(anchor='w', pady=(4, 9))
        ttk.Label(replay_tab, text='Re-running the same folder resumes safely: it does not re-score segments already indexed.',
                  style='Hint.TLabel').pack(anchor='w', pady=(0, 9))
        self.folder_btn = ttk.Button(replay_tab, text='CHOOSE & ANALYZE CLIPS FOLDER', command=self.analyze_folder)
        self.folder_btn.pack(anchor='w', pady=(4, 6))
        ttk.Label(review_tab, text='Open a highlight, then mark Keep or Reject. Rejected files stay on disk.',
                  style='Hint.TLabel').pack(anchor='w', pady=(0, 8))
        self.review_table = ttk.Treeview(review_tab, columns=('id','score','peak','decision','file'),
                                         show='headings', height=6, selectmode='browse')
        for name, label, width in (
            ('id', '#', 44), ('score', 'Score', 65), ('peak', 'Time (s)', 70),
            ('decision', 'Review', 96), ('file', 'Highlight file', 390)
        ):
            self.review_table.heading(name, text=label)
            self.review_table.column(name, width=width, minwidth=38, stretch=name == 'file')
        self.review_table.pack(fill='x')
        review_actions = ttk.Frame(review_tab)
        review_actions.pack(fill='x', pady=(9, 3))
        ttk.Button(review_actions, text='Open selected clip', command=self.open_selected).pack(side='left')
        ttk.Button(review_actions, text='✓ Keep', command=lambda: self.mark_selected('keep')).pack(side='left', padx=7)
        ttk.Button(review_actions, text='✕ Reject', command=lambda: self.mark_selected('reject')).pack(side='left')
        ttk.Button(review_actions, text='Refresh list', command=self.refresh_review).pack(side='left', padx=7)

        detection = ttk.LabelFrame(outer, text='SMART HIGHLIGHT DETECTION', padding=12)
        detection.pack(fill='x', pady=(12, 12))
        options = ttk.Frame(detection)
        options.pack(fill='x')
        settings = (
            ('Profile', self.profile, list(PROFILES)),
            ('Sensitivity', self.sensitivity, ['More picks (12)', 'Balanced (22)', 'Strict (35)']),
            ('Highlight length', self.highlight_duration, ['15', '30', '45', '60']),
            ('Duplicate cooldown (s)', self.cooldown, ['10', '15', '25', '30', '45', '60']),
        )
        for i, (title, var, choices) in enumerate(settings):
            ttk.Label(options, text=title).grid(row=0, column=i, sticky='w', padx=(0, 12))
            ttk.Combobox(options, textvariable=var, state='readonly', values=choices, width=16).grid(
                row=1, column=i, sticky='w', padx=(0, 12), pady=(5, 9))
        ttk.Checkbutton(detection, text='Optional on-screen text detection (requires local Tesseract OCR installation)',
                        variable=self.ocr).pack(anchor='w')
        ttk.Label(detection, text='Scores indicate promising activity, not proven viral / funny / winning moments.',
                  style='Hint.TLabel').pack(anchor='w', pady=(6, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill='x', pady=(0, 12))
        self.start_btn = ttk.Button(actions, text='▶ START LIVE + SMART', command=self.start)
        self.start_btn.pack(side='left')
        self.stop_btn = ttk.Button(actions, text='■ STOP + FINISH', command=self.stop, state='disabled')
        self.stop_btn.pack(side='left', padx=8)
        ttk.Button(actions, text='Open output folder', command=self.open_folder).pack(side='left', padx=8)
        ttk.Label(outer, textvariable=self.status).pack(anchor='w', pady=(0, 5))
        ttk.Label(outer, textvariable=self.smart_status, style='Hint.TLabel').pack(anchor='w', pady=(0, 4))
        ttk.Label(outer, textvariable=self.counter, style='Hint.TLabel').pack(anchor='w', pady=(0, 9))
        ttk.Label(outer, text='Live activity / highlight decisions').pack(anchor='w')
        logs = ttk.Frame(outer)
        logs.pack(fill='both', expand=True, pady=(5, 8))
        self.log = tk.Text(logs, font=('Consolas', 9), bg='#0b1019', fg='#d3dde9', wrap='word', relief='flat', state='disabled')
        self.log.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(logs, command=self.log.yview)
        scroll.pack(side='right', fill='y')
        self.log.config(yscrollcommand=scroll.set)
        ttk.Label(outer, text='Local files only. Use media you own or are authorized to capture. Requires Python, FFmpeg and Streamlink.',
                  style='Hint.TLabel').pack(anchor='w')

    def _smart_cfg(self) -> SmartConfig:
        threshold = float(self.sensitivity.get().split('(')[-1].strip(')'))
        return SmartConfig(profile=self.profile.get(), threshold=threshold,
                           highlight_seconds=int(self.highlight_duration.get()),
                           cooldown_seconds=int(self.cooldown.get()), ocr=self.ocr.get())

    def _save_settings(self):
        data = {'seconds': int(self.duration.get()), 'quality': self.quality.get(),
                'output': self.output.get(), 'profile': self.profile.get(),
                'sensitivity': self.sensitivity.get(), 'highlight_duration': int(self.highlight_duration.get()),
                'cooldown': int(self.cooldown.get()), 'ocr': self.ocr.get()}
        try:
            SETTINGS.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except OSError:
            pass

    def note(self, line: str):
        self.log.configure(state='normal')
        self.log.insert('end', line + '\n')
        # Avoid unbounded GUI memory growth on multi-day sessions.
        if int(self.log.index('end-1c').split('.')[0]) > 2200:
            self.log.delete('1.0', '600.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def browse(self):
        folder = filedialog.askdirectory(title='Choose output folder')
        if folder:
            self.output.set(folder)

    def _assert_idle(self):
        if self.recorder.active or (self.pipeline and self.pipeline.active) or self.studio.is_busy():
            raise RuntimeError('A recording, analysis or Studio task is active. Finish it first.')

    def start(self):
        try:
            self._assert_idle()
            cfg = CaptureConfig(url=self.url.get(), seconds=int(self.duration.get()),
                                quality=self.quality.get(), output_root=Path(self.output.get()))
            smart = self._smart_cfg()
            smart.validate()
            self.recorder.start(cfg)
            assert self.recorder.session_folder
            self.folder = self.recorder.session_folder
            # Explicit queue adapter prevents event-type confusion with tkinter callback APIs.
            self.pipeline = HighlightPipeline(self.folder, smart, lambda typ, msg: self.events.put((typ, msg)))
            self.pipeline.start()
            self._save_settings()
            self._update_buttons()
            self.note('Recording and smart analysis started; final clips appear in highlights/.')
        except Exception as exc:
            if self.recorder.active:
                self.recorder.stop()
            messagebox.showerror('Cannot start', str(exc))

    def analyze_folder(self):
        folder = filedialog.askdirectory(title='Choose an existing LiveClip session folder')
        if not folder:
            return
        try:
            self._assert_idle()
            self.folder = Path(folder)
            if not any(self.folder.glob('clip_*.mp4')):
                raise ValueError('The folder does not contain any clip_000001.mp4-style files.')
            self.pipeline = HighlightPipeline(self.folder, self._smart_cfg(),
                                              lambda typ, msg: self.events.put((typ, msg)))
            self.pipeline.start(already_finished=True)
            self._save_settings()
            self._update_buttons()
            self.note(f'Analyzing saved session {folder}')
        except Exception as exc:
            messagebox.showerror('Cannot analyze', str(exc))

    def stop(self):
        if self.recorder.active:
            self.recorder.stop()
            self.note('Finishing capture; then all remaining segments will be analyzed.')
        elif self.pipeline and self.pipeline.active:
            self.pipeline.cancel()
            self.note('Analysis cancellation requested (completed highlights preserved).')
        self._update_buttons()

    def open_folder(self):
        open_path(self.folder or Path(self.output.get()).expanduser())

    def refresh_review(self):
        if not self.folder or not (self.folder / 'smart_index.sqlite3').exists():
            return
        try:
            conn = sqlite3.connect(str(self.folder / 'smart_index.sqlite3'), timeout=2)
            conn.row_factory = sqlite3.Row
            try:
                data = conn.execute("""SELECT id, score, peak_time, review_status, output_name
                    FROM candidates WHERE status='exported' ORDER BY id DESC LIMIT 500""").fetchall()
            finally:
                conn.close()
            selected = self.review_table.selection()
            old_selected = selected[0] if selected else None
            new_ids = set()
            for item in data:
                iid = str(item['id'])
                new_ids.add(iid)
                values = (iid, f"{item['score']:.1f}", f"{item['peak_time']:.1f}",
                          item['review_status'], item['output_name'])
                if self.review_table.exists(iid):
                    if self.review_table.item(iid, 'values') != values:
                        self.review_table.item(iid, values=values)
                else:
                    self.review_table.insert('', 'end', iid=iid, values=values)
            for iid in self.review_table.get_children():
                if iid not in new_ids:
                    self.review_table.delete(iid)
            if old_selected and self.review_table.exists(old_selected):
                self.review_table.selection_set(old_selected)
        except (OSError, sqlite3.Error) as exc:
            self.note(f'Cannot refresh reviews: {exc}')

    def _selected_review_id(self) -> int | None:
        selected = self.review_table.selection()
        return int(selected[0]) if selected else None

    def open_selected(self):
        key = self._selected_review_id()
        if key is None or not self.folder:
            messagebox.showinfo('Choose a highlight', 'Select a highlight in the Review tab first.')
            return
        with sqlite3.connect(str(self.folder / 'smart_index.sqlite3')) as db:
            row = db.execute('SELECT output_name FROM candidates WHERE id=?', (key,)).fetchone()
        if row and row[0]:
            open_path(self.folder / row[0])

    def mark_selected(self, decision: str):
        key = self._selected_review_id()
        if key is None or not self.folder:
            messagebox.showinfo('Choose a highlight', 'Select a highlight in the Review tab first.')
            return
        if decision not in ('keep', 'reject'):
            return
        try:
            db = SessionDB(self.folder)
            try:
                with db.connection:
                    db.connection.execute("UPDATE candidates SET review_status=? WHERE id=? AND status='exported'",
                                          (decision, key))
                rebuild_manifest(self.folder, db)
            finally:
                db.close()
            self.note(f'Highlight #{key} marked {decision}. Video file was not deleted.')
            self.refresh_review()
        except (sqlite3.Error, OSError) as exc:
            messagebox.showerror('Review could not save', str(exc))

    def _update_buttons(self):
        busy = self.recorder.active or bool(self.pipeline and self.pipeline.active) or self.studio.is_busy()
        self.start_btn.config(state='disabled' if busy else 'normal')
        self.folder_btn.config(state='disabled' if busy else 'normal')
        self.stop_btn.config(state='normal' if busy else 'disabled')

    def poll_events(self):
        for _ in range(120):
            try:
                kind, msg = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'folder':
                self.folder = Path(msg)
                self.note(f'Session folder: {msg}')
            elif kind in ('status', 'error'):
                self.status.set(msg)
                self.note(msg)
            elif kind == 'smart_status':
                self.smart_status.set(msg)
                self.note(msg)
            elif kind in ('log', 'candidate', 'highlight'):
                self.note(msg)
            elif kind == 'finished':
                if self.pipeline:
                    self.pipeline.finish_capture()
                self.note('Capture finalized. Smart analyzer draining remaining segments.')
            elif kind == 'smart_finished':
                self.note('Smart detection worker has stopped.')
        if self.folder and self.folder.is_dir():
            source = len(list(self.folder.glob('clip_*.mp4')))
            exported = len(list((self.folder / 'highlights').glob('highlight_*.mp4')))
            self.counter.set(f'Segments: {source}   •   Highlights: {exported}   •   Source clips preserved')
        self._update_buttons()
        self._review_tick += 1
        if self._review_tick % 4 == 0 and self.folder is not None and (self.folder / 'smart_index.sqlite3').exists():
            self.refresh_review()
        if self._closing:
            if not self.recorder.active and not (self.pipeline and self.pipeline.active):
                self.root.destroy()
                return
        self.root.after(650, self.poll_events)

    def on_close(self):
        if self.studio.is_busy():
            messagebox.showinfo('Studio is exporting', 'Finish the current local export before closing to preserve its output.')
            return
        if self.recorder.active or (self.pipeline and self.pipeline.active):
            if not messagebox.askyesno('Stop and finish?', 'Stop capture and finish smart processing before closing?'):
                return
            self._closing = True
            if self.recorder.active:
                self.recorder.stop()
            elif self.pipeline:
                self.pipeline.finish_capture()
            self.root.withdraw()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == '__main__':
    main()
