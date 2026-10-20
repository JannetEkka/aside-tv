"""Pass 2: audio description cues for blind and low-vision viewers.

    python pipeline/describe.py sintel --video media/sintel-analysis.mp4 --cuts media/sintel-cuts.txt

Cues only go where nobody is speaking, so the narration never talks over dialogue.
Each slot gets a word budget from its length (about 2.5 spoken words a second).
Writes the cues into data/films/<id>/timeline.json under "ad".
"""
import argparse
import json

from common import FILMS, client, fmt_ts, generate_json, read_cuts, upload_video

WORDS_PER_SEC = 2.5
MIN_GAP = 3.0       # shorter silences are left alone
PAD = 0.4           # keep clear of the line before and after
MAX_SLOT = 12.0     # long silences are split into several cues


def silent_gaps(subs, start, end):
    gaps, t = [], start
    for s in subs:
        if s["start"] - PAD - t >= MIN_GAP:
            gaps.append((t, s["start"] - PAD))
        t = max(t, s["end"] + PAD)
    if end - t >= MIN_GAP:
        gaps.append((t, end))
    return gaps


def slots_for(gaps, scene_starts, cuts):
    """Split each silence into slots, starting new ones at scene changes or cuts."""
    slots = []
    for a, b in gaps:
        marks = [a]
        for t in sorted(set(scene_starts) | set(cuts)):
            if marks[-1] + 5.0 <= t <= b - 3.0 and (t in scene_starts or t - marks[-1] >= MAX_SLOT * 0.75):
                marks.append(t)
        # long stretches with no usable cut still get split
        filled = []
        for i, m in enumerate(marks):
            nxt = marks[i + 1] if i + 1 < len(marks) else b
            filled.append(m)
            while nxt - filled[-1] > MAX_SLOT * 1.5:
                filled.append(filled[-1] + MAX_SLOT)
        for i, m in enumerate(filled):
            nxt = filled[i + 1] if i + 1 < len(filled) else b
            words = int((nxt - m - PAD) * WORDS_PER_SEC)
            if words >= 5:
                slots.append({"start": round(m + 0.2, 2), "end": round(nxt, 2), "max_words": min(words, 32)})
    return slots


PROMPT = """You are an audio describer writing a description track for blind and low-vision viewers,
following standard audio description practice:
- Present tense, plain words, describe what is visible: who, where, actions, expressions, key objects, on-screen text.
- Never interpret feelings beyond what faces and bodies show. Never describe sound the viewer can hear.
- Refer to a character by name only once the film has revealed it; before that use a short description.
- Each cue describes what is on screen between its start and end time only. Nothing that happens later.
- Stay within the word limit. Short is better. If a cue would only repeat the previous one, return "".

Characters and when their names are revealed:
{characters}

Write one description for each slot below. Return {{"cues": [{{"i": <slot index>, "text": "..."}}]}}.

SLOTS
{slots}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--video", required=True)
    ap.add_argument("--cuts")
    args = ap.parse_args()

    path = FILMS / args.film / "timeline.json"
    tl = json.loads(path.read_text())
    cuts = read_cuts(args.cuts)
    gaps = silent_gaps(tl["subtitles"], 0.5, tl["credits_start"])
    slots = slots_for(gaps, [s["start"] for s in tl["scenes"]], cuts)
    print(f"{len(gaps)} silent stretches -> {len(slots)} slots")

    chars = "\n".join(
        f"- {c['label']}" + (f" = {c['name']} (name revealed at {fmt_ts(c['name_revealed_at'])})" if c.get("name_revealed_at") is not None else " (never named)")
        for c in tl["characters"])
    slot_text = "\n".join(f"{i}. {fmt_ts(s['start'])}-{fmt_ts(s['end'])}, at most {s['max_words']} words" for i, s in enumerate(slots))

    c = client()
    video = upload_video(c, args.video)
    raw, model = generate_json(c, [video, PROMPT.format(characters=chars, slots=slot_text)],
                               media_resolution="MEDIA_RESOLUTION_LOW")
    texts = {int(x["i"]): x["text"].strip() for x in raw["cues"]}

    ad = []
    for i, s in enumerate(slots):
        t = texts.get(i, "")
        words = t.split()
        if not t:
            continue
        if len(words) > s["max_words"]:
            t = " ".join(words[: s["max_words"]]).rstrip(",;") + "."
        ad.append({"id": f"ad{len(ad) + 1:03d}", "start": s["start"], "end": s["end"], "text": t})
    tl["ad"] = ad
    tl["ad_written_by"] = model
    path.write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    print(f"{model}: {len(ad)} cues")


if __name__ == "__main__":
    main()
