"""Shared helpers for the offline pipeline: time formats, subtitles, Gemini client."""
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILMS = ROOT / "data" / "films"

# Newest first. If a model is missing or out of free quota, the next one is tried.
VIDEO_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3-flash-preview"]


def parse_ts(s):
    """'MM:SS', 'H:MM:SS', 'MM:SS.s' or a number -> seconds (float)."""
    if isinstance(s, (int, float)):
        return float(s)
    s = s.strip().replace(",", ".")
    parts = [float(p) for p in s.split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def fmt_ts(sec):
    sec = max(0, int(round(sec)))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def read_srt(path):
    text = Path(path).read_text(encoding="utf-8-sig", errors="ignore")
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        for i, l in enumerate(lines):
            m = re.match(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)", l)
            if m:
                body = " ".join(x.strip() for x in lines[i + 1:])
                body = re.sub(r"<[^>]+>", "", body)
                out.append({"start": round(parse_ts(m.group(1)), 2), "end": round(parse_ts(m.group(2)), 2), "text": body})
                break
    return out


def read_cuts(path):
    return [float(x) for x in Path(path).read_text().split()] if path and Path(path).exists() else []


def snap(t, cuts, window=2.5):
    """Move t to the nearest shot cut within `window` seconds, so scene edges land on real edits."""
    best = min(cuts, key=lambda c: abs(c - t), default=None)
    return round(best, 2) if best is not None and abs(best - t) <= window else round(t, 2)


def client():
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def upload_video(c, path):
    f = c.files.upload(file=str(path))
    while f.state and f.state.name == "PROCESSING":
        time.sleep(3)
        f = c.files.get(name=f.name)
    if f.state and f.state.name != "ACTIVE":
        raise RuntimeError(f"upload failed: {f.state}")
    return f


def generate_json(c, contents, schema=None, models=VIDEO_MODELS, temperature=0.2, media_resolution=None,
                  patience=900):
    """Call the first model that answers; return (parsed JSON, model name).

    Free-tier models are often "experiencing high demand" (503). Cycle through the list with a
    growing pause until one answers or `patience` seconds have passed.
    """
    from google.genai import types
    cfg = dict(response_mime_type="application/json", temperature=temperature)
    if schema:
        cfg["response_schema"] = schema
    if media_resolution:
        cfg["media_resolution"] = media_resolution
    started, rnd, dead, last = time.time(), 0, set(), None
    while time.time() - started < patience:
        for m in models:
            if m in dead:
                continue
            try:
                r = c.models.generate_content(model=m, contents=contents, config=types.GenerateContentConfig(**cfg))
                return json.loads(r.text), m
            except Exception as e:  # quota, overload, missing model, bad JSON
                last = e
                msg = str(e)
                print(f"  {m} round {rnd + 1}: {msg[:140]}", flush=True)
                if "404" in msg or "NOT_FOUND" in msg or "limit: 0" in msg or "PerDay" in msg:
                    dead.add(m)  # missing, or no free quota left today
        if len(dead) == len(models):
            break
        rnd += 1
        time.sleep(min(60, 10 * rnd))
    raise RuntimeError(f"all models failed: {last}")


def edge_tts_tls():
    """edge-tts pins certifi's CA list. Behind a TLS-inspecting proxy, point it at that proxy's CA
    with ASIDE_CA_BUNDLE (not needed on a normal host such as Render)."""
    import os
    import ssl
    ca = os.environ.get("ASIDE_CA_BUNDLE")
    if ca:
        import edge_tts.communicate
        edge_tts.communicate._SSL_CTX = ssl.create_default_context(cafile=ca)
