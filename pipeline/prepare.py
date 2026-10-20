"""Pass 4: answer the one-button questions ahead of time, every few seconds of each film.

    python pipeline/prepare.py sintel --step 30
    python pipeline/prepare.py sintel --step 30 --server https://aside-tv.onrender.com   # use a deployed server's keys

Each answer goes through the same spoiler check as a live one. The server serves the latest
prepared answer at or before the viewer's position, so the buttons work instantly and keep
working when the free AI tiers are busy. Typed and spoken questions are always answered live.
Safe to stop and re-run: finished answers are kept.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import companion  # noqa: E402
from knowledge import load_films, ts  # noqa: E402

JOBS = [("now", None), ("who", None), ("story", None), ("describe", None), ("missed", 2), ("missed", 5)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--step", type=int, default=30)
    ap.add_argument("--modes", default="now,who,story,describe,missed")
    ap.add_argument("--patience", type=int, default=3600, help="seconds to keep retrying when every model is busy")
    ap.add_argument("--server", help="answer through this Aside server instead of calling the models from here")
    args = ap.parse_args()

    def ask(t, mode, since):
        if not args.server:
            return companion.ask(film, t, mode, "", since)
        body = json.dumps({"film": args.film, "t": t, "mode": mode, "since": since}).encode()
        req = urllib.request.Request(args.server.rstrip("/") + "/api/ask", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
        if "answer" not in out:
            raise RuntimeError(out.get("error", "no answer"))
        return out

    film = load_films()[args.film]
    path = ROOT / "data" / "films" / args.film / "prepared.json"
    prepared = json.loads(path.read_text()) if path.exists() else {}
    modes = set(args.modes.split(","))
    end = int(film.tl.get("credits_start") or film.duration)

    for mode, mins in JOBS:
        if mode not in modes:
            continue
        key = mode if mins is None else f"missed-{mins}"
        table = prepared.setdefault(key, {})
        for t in range(args.step, end + 1, args.step):
            if str(t) in table or (mins and t < mins * 60):
                continue
            since = t - mins * 60 if mins else None
            started = time.time()
            while True:
                try:
                    r = ask(t, mode, since)
                    break
                except Exception as e:
                    if time.time() - started > args.patience:
                        print(f"giving up on {key} {ts(t)}: {e}")
                        path.write_text(json.dumps(prepared, indent=1, ensure_ascii=False))
                        return
                    print(f"  busy ({str(e)[:70]}); waiting", flush=True)
                    time.sleep(60)
            table[str(t)] = {k: r.get(k) for k in ["question", "answer", "t", "moments", "checked", "rewritten", "withheld", "plain", "model"]}
            path.write_text(json.dumps(prepared, indent=1, ensure_ascii=False))
            print(f"{args.film} {key:9s} {ts(t)} {'rewritten ' if r['rewritten'] else ''}{r['answer'][:80]}", flush=True)
            time.sleep(10 if args.server else 4)


if __name__ == "__main__":
    main()
