"""Pass 3: everything the TV is allowed to download.

    python pipeline/publish.py sintel --video media/sintel-720p.mp4 --still 296

Writes data/films/<id>/public.json (title, playback info, captions, audio description cues),
descriptions.vtt and captions.vtt (WebVTT, for any player),
the backdrop and card images, and one narrated MP3 per audio description cue, spoken offline by
Kokoro (an open-weight voice model, Apache 2.0; voice "af_heart"). Every clip is loudness-levelled,
and sped up slightly if it would run past its silent gap. --piper uses Piper's LJSpeech voice instead,
--voice-server an Aside server's /api/speak.
The scene notes and facts stay in timeline.json, which only the server reads.
"""
import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

from common import FILMS

VOICE = os.environ.get("ASIDE_PIPER_VOICE", "media/piper/en_US-ljspeech-high.onnx")
KOKORO_DIR = os.environ.get("ASIDE_KOKORO_DIR", "media/kokoro")
KOKORO_VOICE = os.environ.get("ASIDE_KOKORO_VOICE", "af_heart")
_kokoro = None


def kokoro_wav(text, wav, speed=0.95):
    """Kokoro-82M through kokoro-onnx: about 2x faster than real time on a laptop CPU, no API."""
    global _kokoro
    import soundfile
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        _kokoro = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
    samples, rate = _kokoro.create(text, voice=KOKORO_VOICE, speed=speed, lang="en-us")
    soundfile.write(wav, samples, rate)


def frame(video, t, out, vf):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1",
                    "-vf", vf, "-q:v", "3", str(out)], check=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return round(float(r.stdout.strip()), 2)


def speak_wav(text, wav, server, engine="kokoro"):
    if engine == "kokoro":
        return kokoro_wav(text, wav)
    if engine == "piper":
        subprocess.run(["python3", "-m", "piper", "-m", VOICE, "--length-scale", "0.9", "-f", wav],
                       input=text, text=True, check=True, capture_output=True)
        return
    url = server.rstrip("/") + "/api/speak?text=" + urllib.parse.quote(text)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as r, open(wav, "wb") as f:
                f.write(r.read())
            return
        except Exception as e:
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"no voice for: {text[:40]}")


def narrate(cues, folder, server=None, engine="kokoro"):
    folder.mkdir(exist_ok=True)
    for c in cues:
        path = folder / f"{c['id']}.mp3"
        if not (path.exists() and path.stat().st_size > 1000):
            with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
                speak_wav(c["text"], wav.name, server, engine)
                gap = c["end"] - c["start"]
                tempo = min(1.25, max(1.0, duration(wav.name) / max(gap, 0.5)))   # fit the gap
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav.name, "-af",
                                f"atempo={tempo:.3f},loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "24000",
                                "-c:a", "libmp3lame", "-b:a", "64k", str(path)], check=True)
            if engine == "server":
                time.sleep(7)   # Groq's speech model: 10 requests a minute on the free tier
        c["audio_s"] = duration(path)


def vtt_time(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def write_vtt(path, cues):
    """WebVTT, so any player can use the track: kind="descriptions" for audio description."""
    lines = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}", c["text"], ""]
    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--video", required=True, help="the 720p MP4 that is published")
    ap.add_argument("--still", type=float, required=True, help="second to take the backdrop from")
    ap.add_argument("--voice-server", help="render through this Aside server's /api/speak instead")
    ap.add_argument("--piper", action="store_true", help="render offline with Piper instead")
    args = ap.parse_args()

    d = FILMS / args.film
    tl = json.loads((d / "timeline.json").read_text())
    frame(args.video, args.still, d / "backdrop.jpg", "scale=1920:-2")
    frame(args.video, args.still, d / "thumb.jpg", "crop=ih*16/9:ih,scale=640:360")

    cues = [dict(c) for c in tl.get("ad", [])]
    engine = "piper" if args.piper else "server" if args.voice_server else "kokoro"
    narrate(cues, d / "ad", args.voice_server, engine)
    long = [c["id"] for c in cues if c["audio_s"] > c["end"] - c["start"] + 0.5]
    if long:
        print("narration longer than its gap:", ", ".join(long))

    name = f"{args.film}.mp4"   # media/<id>.mp4, kept under GitHub's 100 MB limit and served by the Aside server
    pub = {k: tl.get(k) for k in ["id", "title", "year", "director", "genre", "credit", "license",
                                   "license_url", "source_url", "logline", "duration", "credits_start"]}
    pub.update({
        "video": "/media/" + name,
        "video_file": name,
        "backdrop": f"/films/{args.film}/backdrop.jpg",
        "thumb": f"/films/{args.film}/thumb.jpg",
        "subtitles": tl.get("subtitles", []),
        "ad": [{"start": c["start"], "end": c["end"], "text": c["text"], "audio": f"/films/{args.film}/ad/{c['id']}.mp3",
                "audio_s": c["audio_s"]} for c in cues],
    })
    (d / "public.json").write_text(json.dumps(pub, indent=1, ensure_ascii=False))
    write_vtt(d / "descriptions.vtt", cues)
    write_vtt(d / "captions.vtt", tl.get("subtitles", []))
    print(f"{args.film}: public.json with {len(pub['ad'])} narrated cues, {len(pub['subtitles'])} caption lines")


if __name__ == "__main__":
    main()
