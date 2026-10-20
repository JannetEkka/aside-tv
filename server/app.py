"""Aside backend: the companion API, phone pairing, read-aloud audio, and the TV + phone web apps.

    GEMINI_API_KEY=... uvicorn app:app --app-dir server --port 8000
"""
import asyncio
import hashlib
import io
import os
import random
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import companion
from knowledge import DATA, load_films

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
MEDIA = Path(os.environ.get("ASIDE_MEDIA_DIR", ROOT / "media"))   # local video files, dev only
TTS_DIR = Path(os.environ.get("ASIDE_TTS_DIR", "/tmp/aside-tts"))
TTS_VOICE = os.environ.get("ASIDE_VOICE", "en-US-AvaMultilingualNeural")

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


@app.get("/api/health")
def health():
    return {"ok": True, "films": list(FILMS)}


@app.get("/api/films")
def films():
    out = []
    for f in FILMS.values():
        if not f.public:
            continue
        pub = dict(f.public)
        local = pub.get("video_file", "")
        if os.environ.get("ASIDE_TEST_WEBM"):   # headless test browsers ship without H.264
            local = local.replace("-720p.mp4", "-test.webm")
        if local and (MEDIA / local).is_file():   # local copy (development): skip the download
            pub["video"] = "/media/" + local
        out.append(pub)
    return out


@app.post("/api/ask")
async def ask(body: AskIn):
    film = FILMS.get(body.film)
    if not film:
        raise HTTPException(404, "unknown film")
    if body.mode == "question" and not body.question.strip():
        raise HTTPException(400, "empty question")
    # Answers depend only on what has been seen, so nearby positions can share one.
    key = (body.film, body.mode, int(body.t // 5), int((body.since or 0) // 30), body.question.strip().lower())
    if key in CACHE:
        return {**CACHE[key], "cached": True}
    try:
        result = await asyncio.to_thread(companion.ask, film, body.t, body.mode, body.question, body.since)
    except Exception as e:
        return JSONResponse({"error": "The companion couldn't answer just now. Try again in a moment.",
                             "detail": str(e)[:200]}, status_code=503)
    CACHE[key] = result
    return result


# ---- read-aloud -------------------------------------------------------------------------------

@app.get("/api/tts")
async def tts(text: str):
    text = text.strip()[:600]
    if not text:
        raise HTTPException(400, "empty")
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TTS_DIR / (hashlib.sha1(f"{TTS_VOICE}|{text}".encode()).hexdigest() + ".mp3")
    if not path.exists():
        import edge_tts
        ca = os.environ.get("ASIDE_CA_BUNDLE")   # only behind a TLS-inspecting proxy
        if ca:
            import ssl
            import edge_tts.communicate
            edge_tts.communicate._SSL_CTX = ssl.create_default_context(cafile=ca)
        try:
            await edge_tts.Communicate(text, TTS_VOICE, rate="+4%").save(str(path))
        except Exception as e:
            raise HTTPException(503, f"voice unavailable: {e}")
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


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
