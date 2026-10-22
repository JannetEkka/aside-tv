"""Pre-record spoken answers with Kokoro, so the TV can read them out with no API at all.

    python pipeline/voice.py

Reads every prepared answer (data/films/*/prepared.json) plus Aside's fixed replies, and writes
data/voice/<sha1 of the text>.mp3. The server's /api/speak serves these first.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish import kokoro_wav  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "voice"
sys.path.insert(0, str(ROOT / "server"))
import companion  # noqa: E402

FIXED = [companion.SAFE]


def texts():
    out = list(FIXED)
    for p in sorted((ROOT / "data" / "films").glob("*/prepared.json")):
        for table in json.loads(p.read_text()).values():
            out += [a["answer"] for a in table.values() if a.get("answer")]
    return list(dict.fromkeys(t.strip()[:700] for t in out))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = 0
    for text in texts():
        path = OUT / (hashlib.sha1(text.encode()).hexdigest() + ".mp3")
        if path.exists():
            continue
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            kokoro_wav(text, wav.name, speed=1.0)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav.name, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                            "-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", "64k", str(path)], check=True)
        made += 1
    print(f"{made} new voice files, {len(list(OUT.glob('*.mp3')))} in total")


if __name__ == "__main__":
    main()
