# Devpost submission (draft)

Paste-ready answers for the form. Sections marked **(after device test)** get filled in once Aside has run on the Fire TV Stick.

## Project name
Aside

## Tagline
A friend on the couch who has seen exactly what you have, and never spoils what comes next.

## Track and mini challenges
- Primary track: **Fire TV**
- Mini challenges: none (AWS Builder needs AWS services we couldn't use without paid credits)

## Description

**What it does.** Aside is a Fire TV app for watching films with an AI that knows the story up to the second you're at. Press Up on the remote and ask *What just happened?*, *Who's that?*, *Describe the scene* or *Story so far*. Stepped out? *What did I miss?* gives you exactly those minutes. Scan a QR code and ask anything out loud from your phone; the answer appears on the TV and the phone. Every answer has "Rewatch 03:12" buttons that jump to the moment it's based on, and it's read aloud by the TV's own speech engine. For blind and low-vision viewers, Aside writes audio description from the video itself and narrates it only in the gaps between dialogue.

**The promise: no spoilers.** Gemini watches each film once and writes a timeline in which every fact carries the second it appears. A question at 08:12 gets only the facts up to 08:12, with names the film hasn't said yet swapped for descriptions. Then a second model, which does see the rest of the film, checks the answer and rewrites or withholds anything that reveals, rules out or teases what's coming. That check matters because models know famous films and love to foreshadow. Aside's knowledge ends at the furthest point you've actually watched, so rewinding doesn't move it. We measured all this with questions written to pry the ending out (eval/RESULTS.md).

**How we built it.** A Python pipeline (Gemini video understanding with ffmpeg shot detection; audio description word-budgeted to each silent gap; narration rendered offline with the open-source Piper voice). A FastAPI server that answers and checks, falling back across Groq, Gemini Flash and Gemma, and serves one-button answers prepared ahead of time. A 10-foot web UI with geometric D-pad focus in plain ES2017 for older Fire OS WebViews. A phone remote using the phone's own speech recognition. And a Kotlin Fire OS app: a full-screen WebView with a leanback launcher entry and banner, which passes Back, Menu and the media keys to the page and speaks with Android's TextToSpeech.

**Why it matters.** Shared TVs mean someone always steps out, and today they pause everyone, rewind, or search and get spoiled. Audio description is written by hand, so most titles have none. Prime Video's X-Ray Recaps summarises up to your minute for Amazon originals; Aside adds a conversation, "what did I miss" for a span, generated audio description and a measured spoiler check, and it works on any film it's given, so any Fire TV app could offer it.

**Demo films:** Sintel and Tears of Steel, © Blender Foundation, CC BY 3.0.

## Built during the submission window
Aside is a new project. All code, data and docs in the repo were created during the hackathon (first commit Oct 20, 2026).

## Repo
https://github.com/JannetEkka/aside-tv (public, MIT)

## Product feedback (after device test, then final)

**Fire TV / Fire OS (Android WebView app, sideloaded on a Fire TV Stick)**
- Used for: the app itself, a WebView app with native key handling and TextToSpeech.
- Worked well: standard Android tooling builds an installable Fire TV app with no Amazon-specific SDK; the leanback launcher plus banner is all the home screen needs; the remote's keys arrive as standard key events with documented codes.
- Needs work: there's no Fire OS simulator. The rules allow "the Fire TV/Vega simulator", but the Vega Virtual Device only runs Vega OS, and an Android TV emulator needs KVM, which cloud dev machines don't have. So every Fire OS check before a real stick was a compile check. A pure web app can't receive the Menu key, so a native wrapper is needed for any app that wants it. **(after device test: WebView behaviour, TTS availability, sideloading)**
- Onboarding: (after device test)
- Build with it again: (after device test)

**Amazon Devices Builder Tools (MCP server, v1.0.17)**
- Used for: searching Fire OS docs from the coding agent. It found the remote key table and two WebView settings our wrapper was missing (`useWideViewPort`, `loadWithOverviewMode`), both of which changed our code.
- Worked well: install in about 30 seconds with npm; the full-text search over curated docs returned the right Fire OS pages with useful snippets.
- Needs work: every call fails with `PROJECT_CONTEXT_REQUIRED` until `set_project_context` is called, which a non-IDE client can't know; a wrong `target_platform` shape returns only "Invalid arguments provided" without saying which field or what's expected; most Fire OS documents are framed as steps of a Fire OS ↔ Vega port, so a plain "build a Fire OS WebView app" starting point is hard to find.
- Build with it again: yes, for doc lookup; we didn't use the Vega profiling tools since this is a Fire OS app.

**Non-Amazon tools:** Google Gemini API (video understanding; answers), Groq (answers and checks), Piper (offline narration), FastAPI, Render (free hosting).

## Feature requests (optional)
1. **A Fire OS simulator, or Fire OS images for the Vega Virtual Device.** Important. Without a device in reach, there's no way to see a Fire OS app run.
2. **A documented hook for "what's playing and at what time" between apps on Fire TV**, with user consent, so a companion like Aside could follow along in partner apps instead of needing its own player. Nice-to-have.
3. **Validation errors from Builder Tools that name the field and the expected shape.** Important for agent use.

## Friction log (optional, up to 10% bonus)

| Task | Steps | Expected | What happened | Severity | Workaround | Suggestion |
|---|---|---|---|---|---|---|
| Search Fire OS docs with Builder Tools | Started the MCP server, called `search_documentation` | Results | `PROJECT_CONTEXT_REQUIRED` on every call | Medium | Called `set_project_context({config: {}})` first | Default to an empty context, or list the requirement in the tool description |
| Filter docs to Fire OS | `target_platform: "FireOS"` | Fire OS results | "Invalid arguments provided for tool search_documentation" | Medium | Read the JSON schema: `{device_os: ["fire_os"]}` | Return the validation error with field and allowed values |
| Test a Fire OS app without a device | Looked for a Fire OS simulator | A simulator like the Vega Virtual Device | None exists; the Android TV emulator needs KVM | High (for remote/cloud developers) | Compile checks plus a headless browser run of the web UI; real-device test on the stick | Ship Fire OS images for the Vega Virtual Device, or a cloud device farm |
| Open the question bar with the Menu key in a web app | Listened for the key in the page | A key event | Menu (and Home, Voice) can't be captured by web apps (documented) | Low | Native wrapper catches `KEYCODE_MENU` in `dispatchKeyEvent` and forwards it | Let WebView apps opt in to receiving Menu |
| (after device test) | | | | | | |
