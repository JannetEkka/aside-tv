"""What the viewer has seen so far, and what they haven't.

Everything the companion says is built from `seen(film, t)`. The future, `unseen(film, t)`,
is only ever shown to the spoiler check, never to the model that writes the answer.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "films"


def ts(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


@dataclass
class Film:
    id: str
    tl: dict
    public: dict = field(default_factory=dict)

    @property
    def title(self):
        return self.tl["title"]

    @property
    def duration(self):
        return self.tl["duration"]

    def label(self, cid, t):
        """A character's name once the film has said it; their description before that."""
        for c in self.tl["characters"]:
            if c["id"] == cid:
                if c.get("name") and c.get("name_revealed_at") is not None and c["name_revealed_at"] <= t:
                    return c["name"]
                return c["label"]
        return cid

    def scene_at(self, t):
        for s in self.tl["scenes"]:
            if s["start"] <= t < s["end"]:
                return s
        return self.tl["scenes"][-1]


def load_films():
    films = {}
    for d in sorted(DATA.iterdir()):
        p = d / "timeline.json"
        if p.exists():
            tl = json.loads(p.read_text())
            pub = json.loads((d / "public.json").read_text()) if (d / "public.json").exists() else {}
            films[tl["id"]] = Film(tl["id"], tl, pub)
    return films


def seen(film: Film, t: float, since: float = 0.0):
    """Notes for everything on screen up to second t, as plain text for the model."""
    tl = film.tl
    lines = [f"FILM: {film.title} ({tl.get('year', '')}). The viewer is at {ts(t)} of {ts(film.duration)}."]

    chars = [c for c in tl["characters"] if c["first_seen"] <= t]
    if chars:
        lines.append("\nCHARACTERS SEEN SO FAR:")
        for c in chars:
            lines.append(f"- {film.label(c['id'], t)}: {c['look']} (first seen {ts(c['first_seen'])})")

    lines.append("\nWHAT HAS HAPPENED, scene by scene:")
    for s in tl["scenes"]:
        if s["start"] > t:
            break
        who = ", ".join(film.label(c, t) for c in s["characters"])
        facts = [f for f in s["facts"] if f["t"] <= t]
        finished = s["end"] <= t
        head = f"[{ts(s['start'])}-{ts(min(s['end'], t))}] {s['location']}" + (f" | on screen: {who}" if who else "")
        if s["end"] <= since:
            head = "(before the viewer left) " + head
        lines.append(head)
        if finished:
            lines.append(f"  {s['summary']}")
        for f in facts:
            lines.append(f"  - {ts(f['t'])} {f['text']}")
        if not finished:
            lines.append("  (this scene is still playing)")

    said = [x for x in tl.get("subtitles", []) if x["start"] <= t]
    if said:
        lines.append("\nDIALOGUE SO FAR:")
        lines += [f"[{ts(x['start'])}] {x['text']}" for x in said]

    ad = [x for x in tl.get("ad", []) if x["start"] <= t]
    if ad:
        lines.append("\nVISUAL DESCRIPTIONS SO FAR:")
        lines += [f"[{ts(x['start'])}] {x['text']}" for x in ad[-25:]]
    return "\n".join(_hide_future_names(film, lines, t))


def _hide_future_names(film, lines, t):
    """Scene notes are written once for the whole film, so a name revealed at 05:00 can appear in a
    fact from 02:00. Swap such names for the character's description until the film says them."""
    swaps = [(c["name"], c["label"]) for c in film.tl["characters"] if c.get("name") in future_names(film, t)]
    if not swaps:
        return lines
    out = []
    for line in lines:
        for name, label in swaps:
            line = line.replace(name, label)
        out.append(line)
    return out


def unseen(film: Film, t: float):
    """Facts that become known after second t. Only the spoiler check reads these."""
    out = []
    for s in film.tl["scenes"]:
        for f in s["facts"]:
            if f["t"] > t:
                out.append(f"{ts(f['t'])} {f['text']}")
    return out


def future_names(film: Film, t: float):
    """Names the film hasn't said yet. A name counts as known once any character carrying it has
    been named (young and old Thom share one)."""
    known = {c["name"] for c in film.tl["characters"]
             if c.get("name") and c.get("name_revealed_at") is not None and c["name_revealed_at"] <= t}
    return sorted({c["name"] for c in film.tl["characters"] if c.get("name") and c["name"] not in known})
