"""Pass 1: Gemini watches the whole film once and writes a timestamped timeline.

    python pipeline/analyze.py sintel --video media/sintel-analysis.mp4 \
        --srt media/sintel-en.srt --cuts media/sintel-cuts.txt

Writes data/films/<id>/timeline.json. Every fact carries the second it becomes
known on screen, which is what lets the server answer from "what you've seen so far".
"""
import argparse
import json

from common import FILMS, client, fmt_ts, generate_json, parse_ts, read_cuts, read_srt, snap, upload_video

PROMPT = """You are preparing notes for an AI companion that watches a film together with a viewer.
The companion may only ever use notes timestamped at or before the viewer's current position,
so precise timing matters more than anything else.

Watch the whole film (video and audio). The dialogue transcript with exact times is below.

Return JSON with:
- "logline": one sentence on the premise as set up in the first two minutes. No later events.
- "credits_start": "MM:SS" when the story ends and end credits begin.
- "characters": everyone who matters to the story. For each:
  - "id": short lowercase slug.
  - "name": the name the film gives them, or null if it never does.
  - "name_revealed_at": "MM:SS" when the name is first said or shown on screen, or null.
  - "label": how to refer to them before their name is known, e.g. "the old shaman", "a baby dragon".
  - "first_seen": "MM:SS" of their first appearance.
  - "look": one sentence on how they look when first seen (for a blind viewer).
- "scenes": consecutive, covering the film from 00:00 to the end with no gaps. A scene is a
  continuous stretch in one place and time; aim for 15 to 40 scenes. For each:
  - "start", "end": "MM:SS".
  - "location": a few words.
  - "characters": ids of characters on screen.
  - "summary": 1 to 3 plain sentences on what happens, only what is shown or said.
  - "facts": 2 to 6 atomic facts the viewer learns in this scene, each with "t" ("MM:SS", the
    moment it becomes visible or is said) and "text". Include reveals, relationships, motives,
    objects that matter later, and emotional beats. Refer to characters by name only once the
    name has been revealed; before that use their label.
Do not interpret beyond what is on screen. Do not mention anything from outside the film.

TRANSCRIPT
{transcript}
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "logline": {"type": "string"},
        "credits_start": {"type": "string"},
        "characters": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "name": {"type": "string", "nullable": True},
            "name_revealed_at": {"type": "string", "nullable": True}, "label": {"type": "string"},
            "first_seen": {"type": "string"}, "look": {"type": "string"}},
            "required": ["id", "label", "first_seen", "look"]}},
        "scenes": {"type": "array", "items": {"type": "object", "properties": {
            "start": {"type": "string"}, "end": {"type": "string"}, "location": {"type": "string"},
            "characters": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
            "facts": {"type": "array", "items": {"type": "object", "properties": {
                "t": {"type": "string"}, "text": {"type": "string"}}, "required": ["t", "text"]}}},
            "required": ["start", "end", "location", "characters", "summary", "facts"]}},
    },
    "required": ["logline", "credits_start", "characters", "scenes"],
}


def normalise(raw, subs, cuts, duration):
    scenes = sorted(raw["scenes"], key=lambda s: parse_ts(s["start"]))
    out = []
    for i, s in enumerate(scenes):
        start = 0.0 if i == 0 else snap(parse_ts(s["start"]), cuts)
        facts = []
        for f in s["facts"]:
            t = min(max(parse_ts(f["t"]), start), duration)
            facts.append({"t": round(t, 1), "text": f["text"].strip()})
        out.append({"id": f"s{i + 1:02d}", "start": start, "location": s["location"],
                    "characters": s["characters"], "summary": s["summary"].strip(),
                    "facts": sorted(facts, key=lambda f: f["t"])})
    for i, s in enumerate(out):  # scenes tile the film: each ends where the next starts
        s["end"] = out[i + 1]["start"] if i + 1 < len(out) else round(duration, 2)
    chars = []
    for c in raw["characters"]:
        chars.append({
            "id": c["id"], "name": c.get("name"), "label": c["label"],
            "name_revealed_at": parse_ts(c["name_revealed_at"]) if c.get("name") and c.get("name_revealed_at") else None,
            "first_seen": parse_ts(c["first_seen"]), "look": c["look"],
        })
    return {
        "logline": raw["logline"].strip(),
        "credits_start": parse_ts(raw["credits_start"]),
        "characters": chars,
        "scenes": out,
        "subtitles": subs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--cuts")
    ap.add_argument("--duration", type=float, required=True)
    args = ap.parse_args()

    subs = read_srt(args.srt)
    cuts = read_cuts(args.cuts)
    transcript = "\n".join(f"[{fmt_ts(s['start'])}] {s['text']}" for s in subs)

    c = client()
    print("uploading", args.video)
    video = upload_video(c, args.video)
    print("analysing")
    # Low resolution (66 tokens a frame) keeps a 15-minute film inside the free tier's per-minute limit.
    raw, model = generate_json(c, [video, PROMPT.format(transcript=transcript)], SCHEMA,
                               media_resolution="MEDIA_RESOLUTION_LOW")
    timeline = normalise(raw, subs, cuts, args.duration)
    timeline["analysed_by"] = model

    out = FILMS / args.film
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "film.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    timeline = {**meta, "duration": args.duration, **timeline}
    if meta.get("logline"):  # the hand-written, spoiler-free logline wins
        timeline["gemini_logline"], timeline["logline"] = timeline["logline"], meta["logline"]
    for ch in timeline["characters"]:  # "Sintel": the title says the name before the film does
        if ch.get("name") and ch["name"].lower() in meta.get("title", "").lower():
            ch["name_revealed_at"] = 0.0
    (out / "timeline.json").write_text(json.dumps(timeline, indent=1, ensure_ascii=False))
    (out / "raw_analysis.json").write_text(json.dumps(raw, indent=1, ensure_ascii=False))
    print(f"{model}: {len(timeline['scenes'])} scenes, {sum(len(s['facts']) for s in timeline['scenes'])} facts, "
          f"{len(timeline['characters'])} characters")


if __name__ == "__main__":
    main()
