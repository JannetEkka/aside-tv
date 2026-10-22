"""Aside backend: the companion API, phone pairing, and the TV + phone web apps.

    GEMINI_API_KEY=... uvicorn app:app --app-dir server --port 8000
"""
import asyncio
import io
import os
import random
import time
import wave
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import companion
from knowledge import DATA, load_films

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
MEDIA = Path(os.environ.get("ASIDE_MEDIA_DIR", ROOT / "media"))   # the demo films, streamed with range requests

app = FastAPI(title="Aside")
FILMS = load_films()
CACHE: dict = {}
ROOMS: dict = {}


class AskIn(BaseModel):
    film: str
    t: float
    mode: str = "question"
    question: str = ""
    since: float | None = None
    # Evaluation only (eval/spoilers.py), honoured when ASIDE_EVAL=1: switch the safeguards off
    # to measure what each one does. The demo films are public, so this exposes nothing private.
    guard: bool = True
    context: str = "seen"


EVAL = os.environ.get("ASIDE_EVAL") == "1"


@app.get("/api/health")
def health():
    return {"ok": True, "films": list(FILMS), "commit": os.environ.get("RENDER_GIT_COMMIT", "")[:7]}


@app.get("/api/films")
def films():
    out = []
    for f in FILMS.values():
        if not f.public:
            continue
        pub = dict(f.public)
        if os.environ.get("ASIDE_TEST_WEBM"):   # headless test browsers ship without H.264
            pub["video"] = "/media/" + pub["video_file"].replace(".mp4", "-test.webm")
        out.append(pub)
    return out


@app.post("/api/ask")
async def ask(body: AskIn):
    film = FILMS.get(body.film)
    if not film:
        raise HTTPException(404, "unknown film")
    if body.mode == "question" and not body.question.strip():
        raise HTTPException(400, "empty question")
    if not EVAL:
        body.guard, body.context = True, "seen"
    baseline = not body.guard or body.context != "seen"
    if body.mode != "question" and not baseline:
        hit = film.prepared_answer(body.mode, body.t, body.since)
        if hit:
            return {**hit, "prepared": True}
    # Answers depend only on what has been seen, so nearby positions can share one.
    key = (body.film, body.mode, int(body.t // 5), int((body.since or 0) // 30), body.question.strip().lower(),
           body.guard, body.context)
    if key in CACHE:
        return {**CACHE[key], "cached": True}
    try:
        result = await asyncio.to_thread(companion.ask, film, body.t, body.mode, body.question, body.since,
                                         body.guard, body.context)
    except Exception as e:
        return JSONResponse({"error": "The companion couldn't answer just now. Try again in a moment.",
                             "detail": str(e)[:200]}, status_code=503)
    if not EVAL:   # the rejected drafts are for tuning the check, not for viewers
        result = {k: v for k, v in result.items() if k not in ("first_answer", "second_answer", "check_reason", "check_reason_2")}
    CACHE[key] = result
    return result


class JudgeIn(BaseModel):
    film: str
    t: float
    question: str
    answer: str


@app.post("/api/eval/judge")
async def eval_judge(body: JudgeIn):
    """Grades one answer for spoilers and helpfulness (eval/spoilers.py). Only with ASIDE_EVAL=1."""
    film = FILMS.get(body.film)
    if not EVAL or not film:
        raise HTTPException(404)
    try:
        return await asyncio.to_thread(companion.judge, film, body.t, body.question, body.answer)
    except Exception as e:
        return JSONResponse({"error": str(e)[:200]}, status_code=503)


CLIENT_LOG = []   # (time, kind, detail, user agent) reported by TV apps, newest last


class ClientEvent(BaseModel):
    kind: str
    detail: str = ""


@app.post("/api/client-log")
def client_log(e: ClientEvent, request: Request):
    """The TV app reports media and script errors, so a failure on a real stick can be read from here."""
    CLIENT_LOG.append((time.strftime("%H:%M:%S"), e.kind[:40], e.detail[:400], request.headers.get("user-agent", "")[:100]))
    del CLIENT_LOG[:-100]
    return {"ok": True}


@app.get("/api/eval/client-log")
def eval_client_log():
    if not EVAL:
        raise HTTPException(404)
    return {"now": time.strftime("%H:%M:%S"), "events": CLIENT_LOG[-60:]}


@app.get("/api/eval/models")
def eval_models():
    """Which models the server will try, and which Groq offers this key. Only with ASIDE_EVAL=1."""
    if not EVAL:
        raise HTTPException(404)
    out = {"answer": companion.ANSWER_MODELS, "judge": companion.JUDGE_MODELS or companion.judge_models(),
           "recent_failures": companion.FAILURES[-20:]}
    if os.environ.get("GROQ_API_KEY"):
        import json as _json
        import urllib.request
        req = urllib.request.Request("https://api.groq.com/openai/v1/models",
                                     headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "User-Agent": "aside-tv"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                out["groq_available"] = sorted(m["id"] for m in _json.loads(r.read())["data"])
        except Exception as e:
            out["groq_available"] = f"error: {e}"
    return out


# ---- phone pairing ----------------------------------------------------------------------------
# The TV opens a room and shows its code as a QR. The phone sends questions into the room; the TV
# picks them up (it alone knows where the film is), answers, and posts the answer back.

LETTERS = "ACDEFGHJKMNPQRTUVWXY"


def _room(code):
    r = ROOMS.get(code.upper())
    if not r or time.time() - r["seen"] > 6 * 3600:
        raise HTTPException(404, "This code has expired. Open Ask from phone on the TV for a new one.")
    return r


@app.post("/api/rooms")
def new_room():
    for k in [k for k, r in ROOMS.items() if time.time() - r["seen"] > 6 * 3600]:
        del ROOMS[k]
    code = "".join(random.choice(LETTERS) for _ in range(4))
    while code in ROOMS:
        code = "".join(random.choice(LETTERS) for _ in range(4))
    ROOMS[code] = {"seen": time.time(), "inbox": [], "log": [], "state": {}, "phone_seen": 0}
    return {"code": code}


class Say(BaseModel):
    text: str = ""
    mode: str = "question"


@app.post("/api/rooms/{code}/say")
def say(code: str, body: Say):
    r = _room(code)
    if body.mode == "question" and not body.text.strip():
        raise HTTPException(400, "empty")
    r["inbox"].append({"id": int(time.time() * 1000), "text": body.text.strip()[:300], "mode": body.mode})
    r["phone_seen"] = time.time()
    return {"ok": True}


@app.get("/api/rooms/{code}/inbox")
def inbox(code: str):
    r = _room(code)
    r["seen"] = time.time()
    items, r["inbox"] = r["inbox"], []
    return {"items": items, "phone": time.time() - r["phone_seen"] < 30}


class State(BaseModel):
    film: str | None = None
    title: str | None = None
    t: float = 0
    playing: bool = False


@app.post("/api/rooms/{code}/state")
def put_state(code: str, body: State):
    r = _room(code)
    r["seen"] = time.time()
    r["state"] = body.model_dump()
    return {"ok": True}


class Answer(BaseModel):
    question: str
    answer: str
    t: float = 0


@app.post("/api/rooms/{code}/answer")
def put_answer(code: str, body: Answer):
    r = _room(code)
    r["log"].append({"n": len(r["log"]) + 1, **body.model_dump()})
    r["log"] = r["log"][-30:]
    return {"ok": True}


@app.get("/api/rooms/{code}/feed")
def feed(code: str, after: int = 0):
    r = _room(code)
    r["phone_seen"] = time.time()
    return {"state": r["state"], "log": [x for x in r["log"] if x["n"] > after]}


@app.get("/api/qr")
def qr(data: str):
    import qrcode
    img = qrcode.make(data, border=1, box_size=10)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


# ---- files ------------------------------------------------------------------------------------
# Only the playback files are public. timeline.json (the whole story) never leaves the server.

PUBLIC_FILES = {".jpg", ".png", ".webp", ".mp3", ".vtt"}


@app.get("/films/{film}/{path:path}")
def film_file(film: str, path: str):
    base = (DATA / film).resolve()
    p = (base / path).resolve()
    if base not in p.parents or p.suffix not in PUBLIC_FILES and p.name != "public.json" or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/media/{name}")
def media(name: str):
    p = (MEDIA / name).resolve()
    if p.parent != MEDIA.resolve() or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/vpkg")
@app.get("/vpkg/{arch}")
def vpkg(arch: str = "armv7"):
    """The Vega OS app (Fire TV Stick 4K Select and newer). armv7 for today's sticks."""
    p = ROOT / "dist" / f"aside_{arch}.vpkg"
    if arch not in ("armv7", "aarch64", "x86_64") or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="application/octet-stream", filename="aside.vpkg")


# ---- read-aloud for Vega -------------------------------------------------------------------------
# Vega's WebView has no speech API, so the server reads answers out with Groq's speech model.

SPEAK_DIR = Path(os.environ.get("ASIDE_SPEAK_DIR", "/tmp/aside-speak"))
SPEAK_MODEL = os.environ.get("ASIDE_SPEAK_MODEL", "canopylabs/orpheus-v1-english")
SPEAK_VOICES = [v for v in os.environ.get("ASIDE_SPEAK_VOICES", "diana,autumn,hannah,daniel,austin,troy").split(",") if v]


def _speak_chunk(text, voice):
    import json as _json
    import urllib.request
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/speech",
        data=_json.dumps({"model": SPEAK_MODEL, "voice": voice, "input": text, "response_format": "wav"}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": "application/json",
                 "User-Agent": "aside-tv"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def _sentences(text, limit=190):
    import re as _re
    out, cur = [], ""
    for part in _re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(part) + 1 > limit:
            out.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}".strip()
    return out + ([cur] if cur else [])


def _join_wavs(blobs):
    """One WAV from several. Groq streams WAVs with a 'size unknown' header, so the frame count
    is reset and the writer fills in the real size when it closes."""
    import wave
    if len(blobs) == 1:
        return blobs[0]
    frames, params = [], None
    for b in blobs:
        with wave.open(io.BytesIO(b)) as w:
            params = params or w.getparams()
            frames.append(w.readframes(w.getnframes()))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams(params._replace(nframes=0))
        for f in frames:
            w.writeframes(f)
    return buf.getvalue()


VOICE_DIR = ROOT / "data" / "voice"   # answers pre-recorded with Kokoro (pipeline/voice.py), keyed by text
GEMINI_TTS = [m for m in os.environ.get("ASIDE_GEMINI_TTS",
              "gemini-3.8-flash-tts,gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts").split(",") if m]


def _silence(seconds=0.4, rate=24000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def voice_key(text):
    import hashlib
    return hashlib.sha1(text.encode()).hexdigest()


def _gemini_tts(text):
    """Gemini's speech model, on the server's Gemini key: 24 kHz 16-bit mono PCM, wrapped as WAV."""
    import wave
    from google.genai import types
    last = None
    for m in GEMINI_TTS:
        try:
            r = companion.client().models.generate_content(
                model=m, contents=f"Say in a warm, clear voice: {text}",
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore"))),
                    http_options=types.HttpOptions(timeout=20000)))
            pcm = r.candidates[0].content.parts[0].inline_data.data
            if pcm[:4] == b"RIFF":   # some models already return a WAV file
                return pcm
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm)
            return buf.getvalue()
        except Exception as e:
            last = e
            companion.FAILURES.append((time.strftime("%H:%M:%S"), f"speak:{m}", str(e)[:200]))
    raise RuntimeError(f"no Gemini voice: {last}")


async def _groq_tts(text):
    import urllib.error
    voice, blobs = SPEAK_VOICES[0], []
    for chunk in _sentences(text):
        for attempt in range(3):
            try:
                blobs.append(await asyncio.to_thread(_speak_chunk, chunk, voice))
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")[:300]
                companion.FAILURES.append((time.strftime("%H:%M:%S"), f"speak:{voice}", f"{e} {body}"[:400]))
                if e.code == 429 and "per minute" in body and attempt < 2:
                    await asyncio.sleep(7)
                    continue
                raise   # daily cap (3,600 tokens on the free tier) or another error: next engine
    return _join_wavs(blobs)


@app.get("/api/speak")
async def speak(text: str):
    """Read an answer aloud, for Vega's WebView (it has no speech API). Pre-recorded Kokoro audio first,
    then Groq's Orpheus, then Gemini's speech model. Each free tier is small, so all three exist."""
    text = text.strip()[:700]
    if not text:
        raise HTTPException(404)
    canned = VOICE_DIR / f"{voice_key(text)}.mp3"
    if canned.is_file():
        return FileResponse(canned, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})
    SPEAK_DIR.mkdir(parents=True, exist_ok=True)
    path = SPEAK_DIR / f"{voice_key(text)}.wav"
    if not path.exists():
        audio = None
        if os.environ.get("GROQ_API_KEY"):
            try:
                audio = await _groq_tts(text)
            except Exception:
                audio = None
        if audio is None and os.environ.get("GEMINI_API_KEY"):
            try:
                audio = await asyncio.to_thread(_gemini_tts, text)
            except Exception:
                audio = None
        if audio is None:
            # The Vega shell blanks the whole app when a media request fails, so a voice that is
            # unavailable (free quotas used up) is a short silence; the answer is on screen anyway.
            return Response(_silence(), media_type="audio/wav", headers={"Cache-Control": "no-store", "X-Voice": "unavailable"})
        path.write_bytes(audio)
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/apk")
def apk():
    """The Fire TV app, for the Downloader app on the TV: type <server>/apk."""
    return FileResponse(ROOT / "dist" / "aside.apk", media_type="application/vnd.android.package-archive",
                        filename="aside.apk")


@app.get("/")
def root():
    return RedirectResponse("/tv/")


@app.get("/p/{code}")
def phone(code: str):
    return FileResponse(WEB / "phone" / "index.html")


@app.middleware("http")
async def no_stale_app(request: Request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith(("/tv", "/phone")):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


app.mount("/tv", StaticFiles(directory=WEB / "tv", html=True), name="tv")
app.mount("/phone", StaticFiles(directory=WEB / "phone", html=True), name="phone")
