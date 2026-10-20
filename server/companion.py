"""The companion: answers from what you've seen, then a second model checks the answer for spoilers.

Hiding the future from the prompt is not enough on its own. The model may have read about the
film, and it likes to foreshadow ("keep an eye on that dragon"). So every answer goes to a
spoiler check that does see the rest of the film, and is rewritten or withheld if it leaks.
"""
import json
import os
import re
import time

from knowledge import Film, future_names, seen, ts, unseen

def _models(var, default):
    return [m.strip() for m in os.environ.get(var, default).split(",") if m.strip()]


# Tried in order until one answers. Free tiers are small and often busy, so there are several:
# Groq (fast, generous free tier; only if GROQ_API_KEY is set), Gemini Flash, then Gemma.
GROQ_MODELS = _models("ASIDE_GROQ_MODELS", "openai/gpt-oss-120b,llama-3.3-70b-versatile,openai/gpt-oss-20b")
GEMINI_MODELS = _models("ASIDE_GEMINI_MODELS", "gemini-3-flash-preview,gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.7-flash")
GEMMA_MODELS = _models("ASIDE_GEMMA_MODELS", "gemma-4-31b-it,gemma-4-26b-a4b-it")


def default_models():
    out = []
    if os.environ.get("GROQ_API_KEY"):
        out += ["groq:" + m for m in GROQ_MODELS]
    if os.environ.get("GEMINI_API_KEY"):
        out += GEMINI_MODELS + GEMMA_MODELS
    return out


ANSWER_MODELS = default_models()
CHECK_MODELS = default_models()
JUDGE_MODELS = _models("ASIDE_JUDGE_MODELS", "")

SYSTEM = """You are Aside, a friend watching a film with the viewer on their TV.
You have seen exactly what they have seen, up to {now}, and nothing more.

Rules:
1. Use only the notes below. Even if you recognise this film, act as if you have never seen it or
   read about it. Never use outside knowledge of its plot, characters, ending or making.
2. Never predict, hint at or tease what comes next: no "you'll see", no "keep an eye on", no "this
   will matter", no guesses about the ending. If asked about the future, say warmly that you'll
   both find out, and offer what is known so far instead.
3. Call characters by the names the notes use. If the notes give no name, describe them.
4. Speak, don't write: short, warm, plain sentences, no lists, no markdown. It is read aloud on a TV.
5. If the notes don't cover the question, say so in one sentence.

Return JSON: {{"answer": "...", "moments": ["MM:SS", ...]}}
"moments" are up to 3 timestamps from the notes, at or before {now}, where the viewer can rewatch
what supports the answer. Use [] if none fit.

NOTES
{notes}
"""

MODES = {
    "now": ("What just happened?", "What just happened? Recap the last minute or so before {now}, mostly the scene playing now. Two or three sentences."),
    "who": ("Who's that?", "Who is on screen right now, and what do we know about each of them so far? Keep it to a sentence each."),
    "describe": ("Describe the scene", "Describe what is on screen right now for someone who can't see it: the place, who is there and what they are doing. Three sentences at most."),
    "missed": ("What did I miss?", "The viewer stepped away at {since} and is back at {now}. Tell them what happened between {since} and {now}, in order, in at most four sentences. Don't repeat anything from before {since}."),
    "story": ("Story so far", "Tell the story so far, up to {now}, in at most five sentences."),
}

CHECK = """You check what a film-watching companion says for spoilers. The viewer is at {now}.

What happens LATER in the film (the viewer has not seen any of this):
{future}

Names the viewer has not learned yet: {names}

The viewer asked: "{question}"
The companion answered: "{answer}"

Is this a spoiler? It is a spoiler if the answer reveals, confirms, rules out, hints at or
foreshadows anything from the LATER list, uses a name the viewer hasn't learned, or teases the
future ("you'll see", "that will matter", "things are about to get worse").
It is NOT a spoiler to restate what the viewer has already seen, or to say "we'll find out".

Return JSON: {{"spoiler": true or false, "reason": "a few words, without repeating the spoiler itself"}}"""

JUDGE = """You are grading a companion that watches a film with a viewer and must never spoil it.
The viewer is at {now}.

WHAT THE VIEWER HAS SEEN (notes):
{seen}

WHAT HAPPENS LATER (the viewer has not seen this):
{future}

The viewer asked: "{question}"
The companion answered: "{answer}"

Grade two things.
1. spoiler: true if the answer reveals, confirms, rules out or hints at anything from WHAT HAPPENS
   LATER, or teases what is coming ("you'll see", "things will get worse", "keep an eye on...").
   Repeating something already seen is not a spoiler.
2. helpful: true if the answer gives the viewer real information from what they have seen. For a
   question about the future, a warm "we'll find out" plus something useful already known counts
   as helpful; a bare refusal does not.

Return JSON: {{"spoiler": true/false, "helpful": true/false, "why": "one short sentence"}}"""

SAFE = "That's still ahead of us, so no spoilers from me. Ask me about anything we've already seen."

_client = None


def client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _parse(text):
    """JSON from a model reply, tolerating code fences or a sentence around it."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", text or "", re.S)
        if not m:
            raise ValueError(f"no JSON in reply: {(text or '')[:80]}")
        return json.loads(m.group(0))


def _gemini(model, system, prompt, temperature):
    from google.genai import types
    gemma = model.startswith("gemma")
    cfg = dict(temperature=temperature,
               # Free-tier models stall under load. A viewer won't wait, so a slow or busy model
               # (timeout, 429, 503) hands over to the next one straight away.
               http_options=types.HttpOptions(timeout=30000 if gemma else 12000))
    if gemma:  # no system instruction or JSON mode for Gemma: fold the instructions into the prompt
        prompt = f"{system}\n\n---\n\n{prompt}" if system else prompt
    else:
        cfg.update(system_instruction=system, response_mime_type="application/json")
        if model.startswith("gemini-3"):
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")
    r = client().models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(**cfg))
    return r.text


def _groq(model, system, prompt, temperature):
    import urllib.request
    body = {"model": model, "temperature": temperature, "max_tokens": 600,
            "response_format": {"type": "json_object"},
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                                          "Content-Type": "application/json", "User-Agent": "aside-tv"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def _json_call(models, system, prompt, temperature=0.4):
    last = None
    for m in models:
        try:
            if m.startswith("groq:"):
                text = _groq(m[5:], system, prompt, temperature)
            else:
                text = _gemini(m, system, prompt, temperature)
            return _parse(text), m
        except Exception as e:
            last = e
    raise RuntimeError(f"no model answered: {last}")


def check(film: Film, t: float, question: str, answer: str):
    """Returns (spoiler, reason). A cheap name test runs first; then the model check."""
    names = future_names(film, t)
    for n in names:
        if re.search(rf"\b{re.escape(n)}\b", answer):
            return True, "uses a name the viewer hasn't learned yet"
    future = unseen(film, t)
    if not future:
        return False, ""
    prompt = CHECK.format(now=ts(t), future="\n".join(future), names=", ".join(names) or "none",
                          question=question, answer=answer)
    out, _ = _json_call(CHECK_MODELS, None, prompt, temperature=0.0)
    return bool(out.get("spoiler")), out.get("reason", "")


def judge(film: Film, t: float, question: str, answer: str):
    """The evaluation's grader. It runs the model list backwards, so where several models are
    available it isn't the one that wrote the answer, and its prompt differs from the check's."""
    prompt = JUDGE.format(now=ts(t), seen=seen(film, t), future="\n".join(unseen(film, t)) or "(nothing)",
                          question=question, answer=answer)
    models = JUDGE_MODELS or list(reversed(default_models()))
    out, model = _json_call(models, None, prompt, temperature=0.0)
    return {"spoiler": bool(out.get("spoiler")), "helpful": bool(out.get("helpful")), "why": out.get("why", ""), "judge": model}


def ask(film: Film, t: float, mode: str = "question", question: str = "", since: float | None = None,
        guard: bool = True, context: str = "seen"):
    """Answer a question at second t of the film.

    guard=False and context="full" exist for the spoiler evaluation only (eval/spoilers.py).
    """
    started = time.time()
    t = max(0.0, min(t, film.duration))
    if mode in MODES:
        title, q = MODES[mode]
        since = max(0.0, min(since if since is not None else t - 120, t))
        question = q.format(now=ts(t), since=ts(since))
    else:
        title = question.strip()
    notes = seen(film, t, since or 0.0) if context == "seen" else seen(film, t, upto=film.duration)
    system = SYSTEM.format(now=ts(t), notes=notes)

    out, model = _json_call(ANSWER_MODELS, system, question)
    answer = (out.get("answer") or "").strip()
    result = {"question": title, "answer": answer, "t": t, "model": model,
              "checked": False, "rewritten": False, "withheld": False}

    if guard and answer:
        spoiler, reason = check(film, t, question, answer)
        result["checked"] = True
        if spoiler:
            result["rewritten"] = True
            retry = (f"{question}\n\n(Your last answer gave away something the viewer hasn't seen yet: {reason}. "
                     "Answer again using only the notes. If it can't be answered without the future, "
                     "say you'll find out together.)")
            out, model = _json_call(ANSWER_MODELS, system, retry)
            answer = (out.get("answer") or "").strip()
            spoiler, _ = check(film, t, question, answer)
            if spoiler or not answer:
                answer, out = SAFE, {"moments": []}
                result["withheld"] = True
            result["answer"] = answer

    moments = []
    for m in out.get("moments") or []:
        try:
            p = [int(x) for x in str(m).split(":")]
            sec = p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]
        except (ValueError, IndexError):
            continue
        if sec <= t and sec not in moments:
            moments.append(sec)
    result["moments"] = moments[:3]
    result["ms"] = int((time.time() - started) * 1000)
    return result
