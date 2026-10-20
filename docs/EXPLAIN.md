# How Aside works, in plain words

For Jannet, so you can explain every part to a judge. Read it once; it takes about ten minutes.

## The idea in one breath

Gemini watches each film once and writes down what happens, with the exact second each thing becomes visible. When you ask a question at 08:12, the server hands the AI only what happened up to 08:12. A second AI, which does know the rest, checks the answer for spoilers before it reaches the TV.

## The parts

**1. The pipeline (runs once per film, on a computer, not on the TV)**
- `analyze.py` uploads a small copy of the film to Gemini with the subtitles and asks for a timeline: about 15 scenes, the characters (with the second each name is first said), and 2 to 6 facts per scene, each stamped with its second. ffmpeg finds the real cuts in the film, and scene starts are moved onto the nearest cut, so a scene doesn't begin half a second early.
- `describe.py` finds the stretches where nobody speaks (from the subtitle timings), cuts them into slots, and gives each slot a word limit of 2.5 words per second. Gemini writes an audio description for each slot, seeing the video. That's why the narration never talks over dialogue.
- `publish.py` makes the public files: title, captions, the audio description cues and an MP3 for each cue, spoken by Piper (an open-source voice that runs offline; the LJSpeech voice is trained on public-domain recordings).
- `prepare.py` answers the one-button questions every 30 seconds of the film, ahead of time, through the same spoiler check. That way the buttons are instant and still work when the free AI services are busy.

**2. The server (`server/`, on Render)**
- `knowledge.py` has two functions that matter. `seen(film, t)` writes the notes for everything up to second t, and swaps any name the film hasn't said yet for a description ("the old shaman"). `unseen(film, t)` lists the facts after t. Only the spoiler check ever sees `unseen`.
- `companion.py` asks the answer model with `seen(t)`, then asks the check model, with `unseen(t)`, whether the answer gives anything away. If it does, the answer is rewritten once. If the rewrite still leaks, Aside says "That's still ahead of us" instead. A quick name check runs first: if the answer uses a name the film hasn't said yet, it fails straight away.
- Models: Groq (if a key is set), then Gemini Flash, then Gemma. Each free tier is small (Gemini's free tier allows 20 requests per model per day), so the server moves to the next model as soon as one is busy or slow (12-second limit).
- `app.py`: the API the TV calls, the phone pairing (a 4-letter room code; the phone posts questions, the TV picks them up every 1.2 seconds), and the files. The full timeline is never sent to the TV.

**3. The TV app**
- `web/tv/` is a web page made for the TV: everything is drawn on a fixed 1920×1080 canvas and scaled to the screen. The remote's arrows move a highlight to the nearest button in that direction.
- The **knowledge horizon** is the furthest point you've watched. It only grows while the film plays normally, so rewinding to rewatch doesn't move it.
- `tv-app/` is the Android app that runs on Fire OS: a full-screen browser view showing that page, plus three things a page can't do on its own: catch the Menu and media keys and the Back key, keep the screen awake, and speak with the TV's built-in voice.

**4. The phone page** (`web/phone/`): opened from the QR code. It uses the phone's own speech recognition, sends the text to the room, and shows the answers.

## Numbers to know

- Sintel: 14 scenes, 48 timed facts, 59 audio description cues. Tears of Steel: 12 scenes, 42 facts, 41 cues.
- Gemini's timeline matched the subtitles to the second where we checked (the shaman's first line at 01:47; the twist at 10:27).
- The spoiler evaluation's results are in `eval/RESULTS.md` (filled in once the free AI quota allows a full run).

## Honest limits (say these before a judge finds them)

- It doesn't work on top of Prime Video or YouTube: an app on Fire TV can't see another app's video. It's a building block that a streaming app, Prime Video included, would put inside its own player. Here it runs on two openly licensed films.
- The timeline is only as good as Gemini's viewing. It's made at low video resolution (to fit the free tier), so small details can be wrong, especially in fast action.
- Free AI tiers are slow and small. That's why the one-button answers are prepared ahead of time and live answers fall back across several models.
- The spoiler check is another AI, so it can miss things. The evaluation measures how often.

## Questions a judge might ask

- *Why not give the AI the whole film and tell it not to spoil?* Because it does spoil. Setup A in the evaluation is exactly that.
- *Why a second model, if the first never sees the future?* The model may know the film from its training (Sintel is famous), and models foreshadow. The check catches both.
- *What's Fire TV-specific?* The 10-foot UI and D-pad focus, the remote keys including Menu (a plain web app can't receive it), the leanback launcher and banner, on-device speech, and Amazon's WebView settings for Fire OS.
- *Could Prime Video use this?* X-Ray Recaps already does spoiler-free summaries for Amazon originals. Aside adds a conversation, "what did I miss" for a span, generated audio description, and a measured check, and works on any film you feed it.
