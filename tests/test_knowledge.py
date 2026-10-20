"""The spoiler rules that don't need a model: what the answer model may see, and when."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import pytest  # noqa: E402

import companion  # noqa: E402
from knowledge import future_names, load_films, seen, ts, unseen  # noqa: E402

FILMS = load_films()


@pytest.mark.parametrize("fid", sorted(FILMS))
def test_seen_never_includes_a_later_fact(fid):
    film = FILMS[fid]
    for t in range(0, int(film.duration), 15):
        notes = seen(film, t)
        for s in film.tl["scenes"]:
            for f in s["facts"]:
                if f["t"] > t and f["text"] not in {g["text"] for sc in film.tl["scenes"] for g in sc["facts"] if g["t"] <= t}:
                    assert f["text"] not in notes, f"{fid} at {ts(t)} leaks the fact from {ts(f['t'])}"


@pytest.mark.parametrize("fid", sorted(FILMS))
def test_unseen_is_exactly_the_later_facts(fid):
    film = FILMS[fid]
    t = film.duration / 2
    later = unseen(film, t)
    assert later and all(x[:5] > ts(t) or x[:5] == ts(t) for x in later)


def test_names_are_hidden_until_the_film_says_them():
    sintel = FILMS["sintel"]
    assert "Scales" not in seen(sintel, 200)          # named at 03:48
    assert "Scales" in seen(sintel, 240)
    assert "Scales" in future_names(sintel, 200)
    assert "Sintel" not in future_names(sintel, 0)    # the title already says it


def test_shared_names_count_as_known_once_said():
    tos = FILMS["tears-of-steel"]
    # young Thom is named at 00:23; the old man is revealed as Thom later, but the name itself is known
    assert "Thom" not in future_names(tos, 60)


def test_name_check_fails_an_answer_without_calling_a_model():
    spoiler, reason = companion.check(FILMS["sintel"], 200, "Who is that?", "That's Scales, her dragon.")
    assert spoiler and "name" in reason


def test_prepared_answers_never_come_from_later_in_the_film():
    film = FILMS["sintel"]
    film.prepared = {"now": {"300": {"answer": "a", "t": 300}, "330": {"answer": "b", "t": 330}}}
    assert film.prepared_answer("now", 329)["t"] == 300
    assert film.prepared_answer("now", 330)["t"] == 330
    assert film.prepared_answer("now", 299) is None
    assert film.prepared_answer("now", 400) is None      # too old to describe "just now"
