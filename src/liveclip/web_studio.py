"""Private localhost control panel for existing LiveClip recording and VOD engines.

Run via START_WEB_STUDIO.vbs on Windows without a console. No public bind,
browser uploads, cloud services, external CDNs or remote authentication.
A random per-process token and exact Host+Origin controls protect mutations.
The existing Recorder, HighlightPipeline and CLI remain the single engines.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import subprocess
import sys
from threading import RLock, Thread
import time
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .capture import CaptureConfig, Recorder
from .moments import LENGTH_OPTIONS
from .pipeline import HighlightPipeline, SmartConfig
from .studio import demo_ffmpeg_args, make_vod_args

HOST = "127.0.0.1"
MAX_JSON_BYTES = 16384
MAX_EVENTS = 80
VIDEO_NAME = re.compile(r"^(?:highlight|clip)_[0-9A-Za-z_.-]+\.mp4$")
DEFAULT_ROOT = Path.home() / "Downloads" / "LiveClipZeroStudio"

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LiveClip Zero Studio — Local Web</title>
<style>
:root{color-scheme:dark;font-family:Inter,"Segoe UI",system-ui,sans-serif;
 --bg:#090d15;--panel:#141d2c;--border:#2b384c;--fg:#ecf3fc;--muted:#94a9be;--accent:#d7f86b}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);margin:0}
header{max-width:1200px;margin:auto;padding:24px 24px 10px;display:flex;justify-content:space-between;align-items:center;gap:18px}
.brand{font-weight:850;letter-spacing:-.04em;font-size:clamp(22px,3vw,34px)}.brand i{font-style:normal;color:var(--accent)}
.subtitle,small{color:var(--muted)}.pill{font-size:12px;border:1px solid #3b5b45;border-radius:30px;color:#a6e6b6;padding:8px 12px}
main{max-width:1200px;margin:auto;padding:16px 24px 40px}.layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(285px,.7fr);gap:18px}
section{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:22px;margin-bottom:18px}
h1,h2,h3,p{margin:0 0 12px}h2{font-size:19px;letter-spacing:-.02em}p{line-height:1.5;font-size:13px;color:var(--muted)}
label{font-size:12px;font-weight:650;display:block;margin:13px 0 5px}input,select{
width:100%;background:#0a1220;border:1px solid #33465c;border-radius:9px;color:var(--fg);
padding:11px 12px;font:inherit;font-size:13px;min-width:0}
input:focus,select:focus{outline:2px solid #91a958}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}
button{border:0;background:var(--accent);border-radius:9px;padding:12px 18px;font:inherit;
font-size:13px;font-weight:850;color:#0b1206;cursor:pointer}
button.secondary{background:#26344a;color:var(--fg)}button:disabled{opacity:.35;cursor:default}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:17px}
.switch{display:flex;gap:9px;align-items:center;font-size:13px;color:#c5d6e8;margin-top:14px}
.switch input{width:auto}.notice{border-left:3px solid var(--accent);padding:7px 12px;margin-top:12px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.tabs button{background:#253246;color:#d1dded}
.tabs button.active{background:var(--accent);color:#111}.tab{display:none}.tab.active{display:block}
#state{font-size:14px;font-weight:750;color:var(--accent)}#events{max-height:250px;overflow:auto;white-space:pre-wrap;
background:#0a111d;color:#c0d1e1;padding:12px;font-family:Consolas,monospace;font-size:11px;border-radius:8px}
.asset{border-bottom:1px solid var(--border);padding:8px 0;font-size:12px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.asset button{padding:6px 10px}video{width:100%;max-height:290px;margin-top:10px;border-radius:8px}
a{color:var(--accent);text-decoration:none}#error{color:#ffa49d;font-size:12px;white-space:pre-wrap}
footer{color:var(--muted);font-size:11px;margin-top:10px}
@media(max-width:860px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr 1fr}}
@media(max-width:540px){.grid,.grid.two{grid-template-columns:1fr}header{align-items:flex-start;flex-direction:column}}
</style></head><body>
<header><div><div class="brand">LIVECLIP <i>ZERO</i> STUDIO</div>
<small>Local Web Workspace / No paid AI / Your files stay on your laptop</small></div>
<span class="pill">● Private · 127.0.0.1 only</span></header>
<main><div class="layout"><div>
<div class="tabs"><button id="tab-live" class="active" onclick="tab('live')">LIVE CAPTURE</button>
<button id="tab-vod" onclick="tab('vod')">LOCAL SHORTS</button></div>
<section id="panel-live" class="tab active"><h2>Record an authorized live stream</h2>
<p>A URL must be genuinely live and Streamlink-supported. Recording only starts when you press START.</p>
<label for="stream">Live stream URL</label><input id="stream" placeholder="https://www.youtube.com/live/...">
<div class="grid"><div><label>Source segments</label><select id="segment"><option>30</option><option>60</option></select></div>
<div><label>Quality</label><select id="quality"><option>best</option><option>720p</option><option>480p</option><option>worst</option></select></div>
<div><label>Maximum highlight</label><select id="live-length"></select></div></div>
<div class="grid two"><div><label>Detection profile</label><select id="live-profile">
<option>Gaming</option><option>Sports</option><option>Reaction</option>
<option>Podcast</option><option>Balanced</option></select></div>
<div><label>Threshold (activity)</label><select id="threshold">
<option value="35">Strict — 35</option><option value="22" selected>Balanced — 22</option>
<option value="12">Sensitive — 12</option></select></div></div>
<label>Output root (local folder)</label><input id="out-live" value="__DEFAULT_ROOT__">
<label class="switch"><input type="checkbox" id="live-precision" checked>Precision mode: skip weak moments instead of cutting anywhere</label>
<label class="switch"><input type="checkbox" id="rights-live">I own or have permission to record this stream</label>
<div class="actions"><button id="start-live" onclick="startLive()">▶ START LIVE + SMART</button>
<button class="secondary" id="stop-live" onclick="stopLive()">■ STOP + FINISH</button></div>
<div class="notice"><p>Five minutes is an <strong>upper limit</strong>, not forced filler. Longer moments need sustained evidence.</p></div>
</section>
<section id="panel-vod" class="tab"><h2>Make meaningful Shorts from a local file</h2>
<p>In File Explorer: Shift + right-click video → Copy as path → paste below. No browser upload or cloud transfer.</p>
<label>Local video file (MP4 / MKV / MOV / WebM)</label><input id="file" placeholder="C:\Videos\my-gameplay.mp4">
<label>Output root</label><input id="out-vod" value="__DEFAULT_ROOT__">
<div class="grid"><div><label>Maximum duration</label><select id="vod-length"></select></div>
<div><label>Maximum picks</label><select id="count"><option>1</option><option selected>3</option><option>5</option></select></div>
<div><label>Focus</label><select id="focus"><option value="action">Action</option>
<option value="balanced">Balanced</option><option value="dialogue">Dialogue</option></select></div></div>
<div class="grid two"><div><label>Portrait crop</label><select id="layout">
<option value="blur">Full context + blurred margins</option><option value="fill">Fill 9:16 (may crop edges)</option></select></div></div>
<label class="switch"><input type="checkbox" id="vod-precision" checked>Precision mode: do not force weak/random moments</label>
<label class="switch"><input type="checkbox" id="rights-vod">I own or have rights to use this video</label>
<div class="actions"><button id="start-vod" onclick="startVod()">✦ FIND & EXPORT MOMENTS</button>
<button class="secondary" onclick="demo()">Generate synthetic test video</button></div>
<div class="notice"><p>Action/race scores show activity, not verified gameplay semantics. Preview the actual start, finish and ending.</p></div>
</section></div>
<div>
<section><h2>Job status</h2><div id="state">Ready</div><p id="detail">No job running.</p>
<p id="error"></p><h3>Latest event</h3><div id="events">Awaiting your first action.</div></section>
<section><h2>Recent results</h2><div id="assets">No output yet.</div>
<video id="preview" controls preload="metadata" playsinline></video>
<small>Preview uses local HTTP range streaming. Output files remain on disk; no automatic deletion.</small></section>
</div></div><footer>Local machine only. No remote listening, no account login, no automatic publishing.
Heuristic moments are review candidates, not a guarantee of races, wins or viral content.</footer></main>
<script>
const TOKEN="__TOKEN__";
const lengths=[15,30,45,60,90,120,180,300];
for(const name of ['live-length','vod-length']){const el=document.getElementById(name);
 lengths.forEach(v=>{const opt=document.createElement('option');opt.value=v;opt.textContent=v+' seconds';el.append(opt)});
 el.value='60';}
function tab(which){for(const t of ['live','vod']){document.getElementById('panel-'+t).classList.toggle('active',t===which);
 document.getElementById('tab-'+t).classList.toggle('active',t===which);}}
async function api(path,data){const response=await fetch(path,{method:'POST',credentials:'same-origin',
 headers:{'Content-Type':'application/json','X-LiveClip-Token':TOKEN},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}
function get(id){return document.getElementById(id)}
async function run(action){try{get('error').textContent='';await action();await refresh();}
 catch(err){get('error').textContent=String(err.message||err)}}
function startLive(){run(()=>api('/api/start-live',{url:get('stream').value,
 seconds:Number(get('segment').value),quality:get('quality').value,
 length:Number(get('live-length').value),profile:get('live-profile').value,
 threshold:Number(get('threshold').value),root:get('out-live').value,
 precision:get('live-precision').checked,rights:get('rights-live').checked}))}
function stopLive(){run(()=>api('/api/stop-live',{}))}
function startVod(){run(()=>api('/api/start-vod',{source:get('file').value,root:get('out-vod').value,
 length:Number(get('vod-length').value),count:Number(get('count').value),
 profile:get('focus').value,layout:get('layout').value,precision:get('vod-precision').checked,
 rights:get('rights-vod').checked}))}
function demo(){run(async()=>{await api('/api/demo',{root:get('out-vod').value});tab('vod')})}
function play(kind,name){get('preview').src='/media?kind='+encodeURIComponent(kind)+'&name='+encodeURIComponent(name);
 get('preview').play().catch(()=>{})}
let lastResults='';
async function refresh(){try{const response=await fetch('/api/state',{headers:{'X-LiveClip-Token':TOKEN}});
if(!response.ok)throw Error('Status unavailable');const v=await response.json();
get('state').textContent=v.status;get('detail').textContent=v.detail||'';
get('error').textContent=v.error||'';
get('events').textContent=(v.events||[]).slice(-25).join('\n')||'No events yet';
get('start-live').disabled=!!v.busy;get('start-vod').disabled=!!v.busy;
get('stop-live').disabled=!v.recording;
if(v.demo_file)get('file').value=v.demo_file;
const fresh=JSON.stringify(v.assets||[]);if(fresh!==lastResults){lastResults=fresh;const target=get('assets');
target.replaceChildren();for(const row of v.assets||[]){const div=document.createElement('div');div.className='asset';
const title=document.createElement('span');title.textContent=row.name;
const button=document.createElement('button');button.textContent='Preview';button.className='secondary';
button.onclick=()=>play(row.kind,row.name);div.append(title,button);target.append(div)}
if(!(v.assets||[]).length)target.textContent='No output yet.'}
}catch(err){get('error').textContent=String(err.message||err)}}
refresh();setInterval(refresh,1400);
</script></body></html>"""


def _safe_root(raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 700:
        raise ValueError("Choose a valid local output folder")
    root = Path(raw.strip().strip('"')).expanduser().resolve()
    if root == Path(root.anchor) or root.exists() and not root.is_dir():
        raise ValueError("Choose a writable subfolder, not a drive root or a file")
    return root


def _safe_file(raw: str) -> Path:
    if not isinstance(raw, str):
        raise ValueError("Choose a local video file")
    p = Path(raw.strip().strip('"')).expanduser().resolve()
    if p.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"} or not p.is_file():
        raise ValueError("Local video not found. Copy its full path from File Explorer.")
    return p


class WebState:
    def __init__(self):
        self.lock = RLock()
        self.events = queue.Queue()
        self.recorder = Recorder(self.events)
        self.pipeline: HighlightPipeline | None = None
        self.job = False
        self.status = "Ready"
        self.detail = "Choose Live Capture or Local Shorts."
        self.error = ""
        self.activity = deque(maxlen=MAX_EVENTS)
        self.session: Path | None = None
        self.latest_output: Path | None = None
        self.demo_file = ""
        Thread(target=self._event_worker, daemon=True).start()

    def _add(self, value):
        with self.lock:
            self.activity.append(str(value)[-500:])

    def busy(self) -> bool:
        return self.job or self.recorder.active or bool(self.pipeline and self.pipeline.active)

    def snapshot(self):
        with self.lock:
            assets = []
            # Only output folders generated by this process are served.
            roots = []
            if self.session:
                roots.append((self.session, "source"))
                roots.append((self.session / "highlights", "highlight"))
            if self.latest_output:
                roots.append((self.latest_output, "vod"))
            for folder, kind in roots:
                if folder.is_dir():
                    files = sorted(folder.glob("*.mp4"), key=lambda p:p.stat().st_mtime, reverse=True)
                    # Do not offer a file that FFmpeg may still be writing.
                    current_source = files[0] if kind == "source" and self.recorder.active and files else None
                    for p in files[:15]:
                        if p != current_source and VIDEO_NAME.fullmatch(p.name) and p.stat().st_size > 500:
                            assets.append({"kind":kind, "name":p.name})
            return {"status":self.status, "detail":self.detail, "error":self.error,
                    "busy":self.busy(), "recording":self.recorder.active,
                    "events":list(self.activity), "assets":assets[:30],
                    "demo_file":self.demo_file}

    def _event_worker(self):
        while True:
            kind, message = self.events.get()
            with self.lock:
                if kind == "finished" and self.pipeline:
                    self.pipeline.finish_capture()
                if kind == "smart_finished":
                    self.status = "Ready"
                    self.detail = "Recording and highlight analysis finalized."
                elif kind == "folder":
                    self.session = Path(message)
                elif kind == "error":
                    self.error = str(message)[-400:]
                    self._add("Issue: " + self.error)
                elif kind == "status":
                    self.detail = str(message)[-350:]
                else:
                    self._add(message)

    def start_live(self, body):
        if body.get("rights") is not True:
            raise PermissionError("Confirm that you own or can record this stream")
        length = body.get("length", 60)
        if type(length) is not int or length not in LENGTH_OPTIONS:
            raise ValueError("Choose a maximum clip length up to 300 seconds")
        root = _safe_root(body.get("root") or str(DEFAULT_ROOT))
        cfg = CaptureConfig(url=str(body.get("url") or ""), seconds=body.get("seconds"),
                            quality=body.get("quality"), output_root=root)
        cfg.validate()
        smart = SmartConfig(profile=body.get("profile") or "Gaming",
                            threshold=body.get("threshold", 22), highlight_seconds=length,
                            cooldown_seconds=25, precision=body.get("precision") is True)
        smart.validate()
        with self.lock:
            if self.busy():
                raise RuntimeError("Finish the current job before starting another")
            self.error = ""
            self.session = None
            self.latest_output = None
            self.demo_file = ""
            self.recorder.start(cfg)
            assert self.recorder.session_folder
            self.session = self.recorder.session_folder
            self.pipeline = HighlightPipeline(self.session, smart, lambda k,v:self.events.put((k,v)))
            self.pipeline.start()
            self.status = "Recording"
            self.detail = "Recording started. You can stop from this browser page."
            self._add("Live capture: " + str(self.session))

    def stop_live(self):
        with self.lock:
            if not self.recorder.active:
                return
            self.recorder.stop()
            self.status = "Finalizing"
            self.detail = "Finish source recording, then index finalized clips. Do not close the browser backend."

    def _run_vod(self, args, folder, source, is_demo=False):
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.run([sys.executable, "-m", "liveclip.neon_adopt.cli", *args],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=5400, creationflags=flags)
            if proc.returncode:
                details = proc.stderr.decode("utf-8", "replace")[-650:]
                raise RuntimeError("Local video processing failed: " + details)
            manifest = folder / "candidates.json"
            data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
            num = len(data.get("outputs", []))
            with self.lock:
                self.latest_output = folder
                self.status = "Ready"
                self.detail = (f"{num} candidate(s) exported to {folder}" if num else
                               "No strong evidence found: no arbitrary highlight was generated.")
                self._add(self.detail)
        except Exception as exc:
            with self.lock:
                self.error = str(exc)[-650:]
                self.status = "Ready"
                self.detail = "Local video job failed."
        finally:
            with self.lock:
                self.job = False

    def start_vod(self, body):
        if body.get("rights") is not True:
            raise PermissionError("Confirm you own or are allowed to edit this video")
        source = _safe_file(body.get("source"))
        root = _safe_root(body.get("root") or str(DEFAULT_ROOT))
        count, length = body.get("count"), body.get("length")
        if type(count) is not int or type(length) is not int:
            raise ValueError("Choose valid integer count and length")
        folder = root / (datetime.now().strftime("Shorts_%Y%m%d_%H%M%S_") + secrets.token_hex(3))
        args = make_vod_args(source, folder, count=count, seconds=length,
                             profile=body.get("profile", "action"),layout=body.get("layout", "blur"),
                             precision=body.get("precision") is True)
        with self.lock:
            if self.busy():
                raise RuntimeError("Finish the previous job first")
            self.job = True
            self.status = "Finding moments"
            self.error = ""
            self.demo_file = ""
            self.detail = "Analyzing local video. Long videos can take time; no cloud upload."
            Thread(target=self._run_vod, args=(args,folder,source), daemon=True).start()

    def demo(self, body):
        root = _safe_root(body.get("root") or str(DEFAULT_ROOT))
        folder = root / ("Demo_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(3))
        source = folder / "demo_gameplay.mp4"
        command = demo_ffmpeg_args(source)
        with self.lock:
            if self.busy():
                raise RuntimeError("Finish the previous job first")
            self.job = True
            self.status = "Generating sample"
            self.detail = "Creating a synthetic local video; no streaming provider involved."
            self.error = ""
            self.demo_file = ""
        def work():
            try:
                folder.mkdir(parents=True, exist_ok=False)
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                proc = subprocess.run(command, capture_output=True, timeout=140, creationflags=flags)
                if proc.returncode or not source.is_file():
                    raise RuntimeError("Synthetic video generation failed")
                with self.lock:
                    self.demo_file = str(source)
                    self.latest_output = folder
                    self.detail = "Demo created: local file field filled. Try 15 seconds with precision OFF (demo is not real gameplay)."
                    self._add(self.detail)
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)[-400:]
            finally:
                with self.lock:
                    self.job = False
                    self.status = "Ready"
        Thread(target=work, daemon=True).start()

    def media(self, kind: str, name: str) -> Path | None:
        if not VIDEO_NAME.fullmatch(name):
            return None
        with self.lock:
            folder = (self.session if kind == "source" else
                      self.session / "highlights" if kind == "highlight" and self.session else
                      self.latest_output if kind == "vod" else None)
            if folder is None or not folder.is_dir():
                return None
            target = (folder / name).resolve()
            if target.parent != folder.resolve() or not target.is_file():
                return None
            return target


class Handler(BaseHTTPRequestHandler):
    server_version = "LiveClipLocal/1"
    def log_message(self, *args):
        pass  # Avoid request logging / accidental capture URL leakage

    def _headers(self, status=200, content_type="application/json", length=None, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host == f"{HOST}:{self.server.server_port}"  # DNS rebinding protection

    def _auth_ok(self):
        if not self._host_ok() or self.headers.get("X-LiveClip-Token") != self.server.token:
            return False
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{HOST}:{self.server.server_port}":
            return False
        if self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return False
        return True

    def _json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._headers(status, length=len(payload))
        self.wfile.write(payload)

    def do_GET(self):
        if not self._host_ok():
            self._json({"error":"Invalid local Host"}, 403)
            return
        uri = urlsplit(self.path)
        if uri.path == "/":
            page = PAGE.replace("__TOKEN__", self.server.token).replace(
                "__DEFAULT_ROOT__", str(DEFAULT_ROOT).replace("&","&amp;").replace("<","&lt;").replace('"',"&quot;"))
            payload = page.encode("utf-8")
            self._headers(200, "text/html; charset=utf-8",len(payload))
            self.wfile.write(payload)
            return
        if uri.path == "/api/state":
            if not self._auth_ok():
                self._json({"error":"Unauthorized"}, 403)
                return
            self._json(self.server.state.snapshot())
            return
        if uri.path == "/media":
            args = parse_qs(uri.query)
            name = args.get("name", [""])[0]
            kind = args.get("kind", [""])[0]
            target = self.server.state.media(kind,name)
            if not target:
                self._json({"error":"File unavailable"},404)
                return
            self._media(target)
            return
        self._json({"error":"Not found"}, 404)

    def _media(self, file: Path):
        size = file.stat().st_size
        if size <= 0:
            self._json({"error":"Empty video"}, 404)
            return
        start, end, status = 0, size - 1, HTTPStatus.OK
        range_value = self.headers.get("Range")
        if range_value:
            match = re.fullmatch(r"bytes=(\d+)-(\d*)",range_value.strip())
            if match:
                start = int(match.group(1))
                end = min(int(match.group(2)),size-1) if match.group(2) else size-1
                if start >= size or start > end:
                    self._headers(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
                                  "text/plain",0,{"Content-Range":f"bytes */{size}"})
                    return
                status = HTTPStatus.PARTIAL_CONTENT
            else:
                self._headers(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
                              "text/plain",0,{"Content-Range":f"bytes */{size}"})
                return
        extra = {"Accept-Ranges":"bytes"}
        if status == HTTPStatus.PARTIAL_CONTENT:
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        self._headers(status,"video/mp4",end-start+1,extra)
        try:
            with file.open("rb") as stream:
                stream.seek(start)
                remaining = end-start+1
                while remaining:
                    data = stream.read(min(1024 * 256, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self._auth_ok() or self.headers.get("Content-Type","").split(";")[0] != "application/json":
            self._json({"error":"Unauthorized local request"},403)
            return
        try:
            length = int(self.headers.get("Content-Length","-1"))
            if not 2 <= length <= MAX_JSON_BYTES:
                raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body,dict):
                raise ValueError("Expected a JSON object")
            path = urlsplit(self.path).path
            if path == "/api/start-live":
                self.server.state.start_live(body)
            elif path == "/api/stop-live":
                self.server.state.stop_live()
            elif path == "/api/start-vod":
                self.server.state.start_vod(body)
            elif path == "/api/demo":
                self.server.state.demo(body)
            else:
                self._json({"error":"Not found"},404)
                return
            self._json({"ok":True})
        except (ValueError, TypeError, PermissionError, OSError, RuntimeError) as exc:
            self._json({"error":str(exc)[:550]}, 400)


def make_server():
    server = ThreadingHTTPServer((HOST, 0), Handler)
    server.daemon_threads = True
    server.token = secrets.token_urlsafe(32)
    server.state = WebState()
    return server


def main():
    server = make_server()
    url = f"http://{HOST}:{server.server_port}/"
    try:
        webbrowser.open(url)
        server.serve_forever(poll_interval=.4)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
