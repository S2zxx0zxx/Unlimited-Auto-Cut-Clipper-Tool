"""Optional local YOLOX-S person tracker for third-person gaming frames.

Adapted from player_track.py in AnIntellectualBeing/GTA-Auto-Clipper at
a9ac2ba8b95b5a887e8ab068b8237c86bcec59a2.
MIT Copyright (c) 2026 AnIntellectualBeing.
See THIRD_PARTY_LICENSES/GTA-Auto-Clipper-MIT.txt.

No automatic model download or network request. User supplies model bytes
and accepts their independent weights license. CPU-only path is bounded.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional
from .framing import pick_player, smooth_path


def track_player(source: Path, start: float, length: float, model_file: Path,
                 *, sample_rate: float = 1., max_samples: int = 120
                 ) -> Optional[list[tuple[float,float]]]:
    """Return clip-relative player centre keyframes, or None when unreliable.

    Requires optional local opencv, numpy and onnxruntime. If a model is absent
    this function raises rather than installing or silently fetching it.
    """
    import cv2
    import numpy as np
    import onnxruntime as ort

    if not model_file.is_file() or model_file.stat().st_size < 100_000:
        raise ValueError("Supply a valid locally downloaded YOLOX model file")
    if not source.is_file() or not 0 <= start or not 0 < length <= 600:
        raise ValueError("Invalid video or bounded selection")
    if not .05 <= sample_rate <= 2. or not 2 <= max_samples <= 300:
        raise ValueError("Invalid sampling budget")
    session=ort.InferenceSession(str(model_file),providers=["CPUExecutionProvider"])
    inputs=session.get_inputs()
    if not inputs:
        raise ValueError("ONNX model has no inputs")
    input_name=inputs[0].name
    grids=[]
    for stride in (8,16,32):
        n=640//stride
        yy,xx=np.meshgrid(np.arange(n),np.arange(n),indexing="ij")
        grids.append(np.stack([xx.ravel(),yy.ravel(),np.full(n*n,stride)],axis=1))
    grid=np.concatenate(grids).astype(np.float32)
    cap=cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError("Cannot open video for tracking")
    try:
        width,height=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0 or width/height < 1.2:
            return None
        rate=float(cap.get(cv2.CAP_PROP_FPS) or 30)
        if not math.isfinite(rate) or rate<=0:
            rate=30.
        step=max(1,int(rate/max(.05,min(sample_rate,max_samples/length))))
        nframes=min(int(length*rate)+1,max_samples*step)
        cap.set(cv2.CAP_PROP_POS_MSEC,start*1000)
        times=[]; positions=[];prev=None
        for i in range(nframes):
            if i%step:
                if not cap.grab():
                    break
                continue
            ret,frame=cap.read()
            if not ret or frame is None:
                break
            h,w=frame.shape[:2]
            scale=min(640/w,640/h)
            new_w,new_h=round(w*scale),round(h*scale)
            canvas=np.full((640,640,3),114,dtype=np.uint8)
            canvas[:new_h,:new_w]=cv2.resize(frame,(new_w,new_h))
            inp=canvas.transpose(2,0,1)[None].astype(np.float32)
            out=session.run(None,{input_name:inp})[0]
            out=out[0] if out.ndim==3 else out
            if out.shape[0]!=len(grid) or out.shape[1]<6:
                raise ValueError("Unexpected YOLOX output geometry")
            xy=(out[:,:2]+grid[:,:2])*grid[:,2:3]
            wh=np.exp(np.clip(out[:,2:4],-15,15))*grid[:,2:3]
            score=out[:,4]*out[:,5]
            valid=(score > .35) & np.isfinite(score)
            boxes=[]
            if valid.any():
                xy,wh,scores=xy[valid]/scale,wh[valid]/scale,score[valid]
                rects=[[float(x-bw/2),float(y-bh/2),float(bw),float(bh)]
                       for (x,y),(bw,bh) in zip(xy,wh)]
                picks=cv2.dnn.NMSBoxes(rects,scores.tolist(),.35,.45)
                for j in np.asarray(picks).reshape(-1):
                    boxes.append((*rects[int(j)],float(scores[int(j)])))
            position=pick_player(boxes,width,height,prev)
            if position is not None:
                prev=position
            times.append(i/rate);positions.append(position)
        if len(times)<2 or sum(x is not None for x in positions)<max(2,len(times)//5):
            return None
        return list(zip(times,smooth_path(times,positions)))
    finally:
        cap.release()
