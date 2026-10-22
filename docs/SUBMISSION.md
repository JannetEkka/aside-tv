# Devpost submission: paste-ready answers

Each heading is a field on the Devpost form, in the form's order. Copy the text under it.

---

## Project name
Aside: an AI that watches with you and never spoils

## Elevator pitch
A Fire TV app that answers "What just happened?", "Who's that?" and "What did I miss?" from exactly what you've seen, never spoils what's next, and narrates audio description for blind viewers.

## Thumbnail
`docs/submission/thumbnail.png` (1500×1000, 3:2)

## About the project

```markdown
## Inspiration
Somebody always steps out during a film: the kitchen, the kids, a phone call. When they come back they either pause everyone, rewind, ask the person next to them (who then misses the next bit), or search online and get spoiled. And for blind and low-vision viewers, audio description is written by hand, so most titles simply don't have it. We wanted a friend on the couch who has seen exactly what you have: someone you can ask anything, who never gives away what comes next.

## What it does
Aside is a Fire TV app. Press **Up** on the remote at any moment of a film and ask:
- **What just happened?** The last minute, in two or three spoken sentences.
- **Who's that?** Who's on screen and what we know about them *so far*. A name only appears once the film has said it.
- **Describe the scene.** For someone who can't see the screen.
- **What did I miss?** Stepped out for two minutes? You get exactly those two minutes.
- **Story so far.** Offered on its own when you come back after a long pause.
- **Ask by phone.** Scan a QR code, tap the mic, ask anything. The answer appears on the TV, is read aloud, and shows on the phone.

Every answer has **Rewatch 03:12** buttons that jump back to the moment it's based on. Switch on **audio description** and Aside narrates what's on screen whenever nobody is speaking, with the film dipping gently underneath.

It runs on a real **Fire TV Stick 4K Select (Vega OS)**, built from Amazon's Vega WebView template, and on Fire OS sticks through a Kotlin wrapper. The demo films are *Sintel* and *Tears of Steel* (Blender Foundation, CC BY 3.0).

## How we built it
- **A timeline stamped to the second.** Gemini watches each film once with its subtitles and writes scenes, characters (with the second each name is first said) and facts, each with the second it appears. Scene edges are snapped to real shot cuts found with ffmpeg.
- **Audio description that never talks over dialogue.** Silent gaps come from the subtitle timings; each gap gets a word budget (2.5 words a second), Gemini writes a description for it while watching, and the narration is levelled and fitted to the gap. The track is also exported as standard WebVTT.
- **Answers from only what you've seen.** For a question at 08:12 the server passes only the facts up to 08:12, and swaps names the film hasn't said yet for descriptions. The model is told never to assert or deny anything the film hasn't shown.
- **A second model checks every answer against the rest of the film.** It sees what you've seen and what happens later, and rewrites or withholds anything that reveals, rules out or teases the future. Button answers that still fail fall back to a plain recap stitched from the timeline's own facts, so they can't spoil.
- **Fire TV apps.** The TV UI is plain ES2017 on a 1920×1080 stage with geometric D-pad focus. On Vega, a React Native for Vega app hosts it in a Vega WebView (`allowSystemKeyEvents` for Back, `postMessage` to exit); Vega's WebView has no speech API, so answers are read aloud by the server (pre-recorded with the open Kokoro voice for prepared answers; Groq Orpheus or Gemini speech for live ones). On Fire OS, a Kotlin WebView wrapper forwards Back, Menu and media keys and uses Android TextToSpeech.
- **Free tiers only.** FastAPI on Render's free plan; answers and checks fall back across Groq (gpt-oss-120b, Qwen 3.8, gpt-oss-20b), Gemini Flash and Gemma; the one-button answers are prepared ahead of time every 30 seconds so they stay instant when free tiers are busy.

## Measured, not promised
24 questions over both films, 16 of them written to pry the ending out ("Does she ever find Scales?", "How does it end?"), each answered three ways and graded by a separate judge model that sees the whole film:

| Setup | Spoiled a future-probing question | Helpful on what you've seen |
|---|---|---|
| Whole film in the prompt, told not to spoil | 6 of 16 | 7 of 8 |
| Only what you've seen | 1 of 16 | 8 of 8 |
| **Aside** | **0 of 16** | **8 of 8** |

Telling a model not to spoil isn't enough. Most of the gain comes from never giving it the future; the check is the safety net. On the live server it caught a model claiming "No, the cave dragon isn't Scales" (false, and it rules out the twist).

## Challenges we ran into
- **Our stick turned out to run Vega OS**, which doesn't run Android apps. We rebuilt the shell from Amazon's `vegaWebview` template the same evening. The Vega CLI doesn't run on Windows, so we enabled Developer Mode with its device-code sign-in from a Linux machine and installed with plain `adb` (Vega's `vda` is a renamed adb).
- **Free AI tiers are small and busy.** Gemini's free tier allows 20 requests per model per day; Groq's speech model 10 a minute. We built model fallbacks, per-call timeouts and prepared answers so the TV never waits long.
- **The spoiler check needed context.** At first it only saw the future, so it flagged honest recaps ("she named him Scales" was already on screen). Giving it what the viewer has seen fixed that.

## Accomplishments that we're proud of
- It runs on a real Vega OS Fire TV Stick, driven by the remote, with spoken answers, phone questions and audio description all working.
- 0 of 16 spoilers on questions written to break it, while staying helpful.
- Audio description generated from the video itself, placed only in silent gaps.

## What we learned
Spoiler safety is a data problem before it's a prompt problem: stamp every fact with its second and the model simply doesn't have the future to leak. And Fire TV now means two platforms (Fire OS and Vega OS); a web app inside a thin native shell runs on both.

## What's next
Inside a streaming player (Prime Video's X-Ray Recaps already summarises up to your minute for Amazon originals), Aside would add the conversation, "what did I miss" for a span, and generated audio description, for any title. Next steps: Alexa voice questions on the TV itself, per-profile memory ("you stopped here last night"), and series support with "previously on" recaps.
```

## Built with
amazon-fire-tv, vega-os, vega-sdk, react-native, webview, javascript, html5, css3, python, fastapi, google-gemini, gemma, groq, gpt-oss, qwen, kokoro-tts, ffmpeg, kotlin, android, render, amazon-devices-builder-tools, mcp, webvtt, claude-code

## "Try it out" links
- https://github.com/JannetEkka/aside-tv
- https://aside-tv.onrender.com/tv/

## Image gallery
`docs/submission/gallery-1.jpg` … `gallery-8.jpg` (1920×1280, 3:2, captioned)

## Video demo link
(YouTube link, public, under 3 minutes)

## Upload a file (optional)
`dist/aside-tv-packages.zip`: the Vega packages (armv7 for current sticks, aarch64, x86_64 for the Vega Virtual Device) and the Fire OS APK.

## Submitter Type
Individual

## Organization Name
N/A

## Submitter Country of Residence
India

## Canada province
N/A

## Primary Track
Fire TV

## Code repository URL
https://github.com/JannetEkka/aside-tv

## New or existing
New

## AWS Builder Mini Challenge
No

## AWS Builder: which AWS services
Not applicable: not entering the AWS Builder Mini Challenge.

## Open Source Mini Challenge
No

## Feature Requests

```
1. A Fire OS simulator, or Fire OS images for the Vega Virtual Device (Important). Without a Fire TV device in reach there's no way to see a Fire OS app run: the Vega Virtual Device only runs Vega OS, and an Android TV emulator needs KVM, which cloud development machines don't have.

2. Vega CLI on Windows (Important). Developer Mode can only be enabled with the Vega CLI, which runs on macOS and Ubuntu. Many developers (and most families' laptops) are on Windows. A Windows build, or Developer Mode enablement from the Developer Console in the browser, would remove the biggest setup hurdle.

3. A speech API in Vega WebView (Important). window.speechSynthesis isn't available, so a web app has to fetch spoken audio from a server to read anything aloud. For accessibility features this matters a lot.

4. A screen recording command for Vega devices (Nice-to-have). scrcpy and screenrecord are Android-only; we had to film the TV with a phone for the demo. `vega device screenrecord` would make demos and bug reports far easier.

5. Clear errors from Builder Tools and the Vega CLI (Important for agent use): name the failing field and expected shape for invalid MCP tool arguments, and say "this account isn't registered as a developer" instead of "invalid_token".
```

## Friction Log

```
FL-1. Enable Developer Mode on a Vega stick from a Windows laptop
Steps: Settings > About > device name x7 > Developer Options > Developer Mode > Continue (6-digit code); looked for the Vega CLI on Windows.
Expected: a way to confirm the code from Windows or the browser.
Actual: the Vega CLI supports macOS and Ubuntu only.
Severity: High
Workaround: ran `vega devmode login` and `enable-device --code` on a Linux machine (the sign-in is a device-code flow, so the developer approved it in her own browser), then signed the CLI out.
Suggestion: a Windows CLI build, or a "Enable a device" page in the Developer Console that takes the TV's code.

FL-2. `vega devmode login` with an account not yet registered as a developer
Steps: approved the device-code sign-in with a normal Amazon account.
Expected: "This account isn't registered as an Amazon Developer. Register at developer.amazon.com."
Actual: "Failed to verify vendor registration: http 401: invalid_token, Authentication failed". It looked like a token or region problem (the account was originally amazon.in), and we spent three sign-in attempts on it.
Severity: Medium
Workaround: completed developer registration, then signed in again.
Suggestion: detect the missing developer profile and say so, with a link.

FL-3. `vega devmode login` on a headless Linux machine
Steps: completed the sign-in.
Expected: token saved.
Actual: "failed to store token in OS password management system: exec: dbus-launch: executable file not found".
Severity: Medium
Workaround: installed dbus-x11 and gnome-keyring and ran the CLI inside `dbus-run-session` with an unlocked keyring.
Suggestion: fall back to a file-based token store (with a warning) when no keyring exists, or document the requirement.

FL-4. Install a .vpkg without the Vega CLI
Steps: needed to install from Windows.
Expected: a documented route.
Actual: undocumented; we found that `vega device install-app` is `vda push` + `vda shell vpm install`, and that vda is a renamed adb (protocol 41).
Severity: Medium
Workaround: Google's platform-tools adb: `adb connect`, `adb push aside.vpkg /tmp/`, `adb shell vpm install /tmp/aside.vpkg`, `adb shell vlcm launch-app orpheus://<component-id>`. Worked first time.
Suggestion: document this as the supported path for machines without the Vega CLI.

FL-5. Read answers aloud in a Vega WebView app
Steps: called window.speechSynthesis.
Expected: speech, as in Chromium.
Actual: not available in Vega WebView (confirmed by community threads); no WebView-level TTS bridge documented.
Severity: Medium (an accessibility feature)
Workaround: the server renders speech (pre-recorded Kokoro audio, then Groq Orpheus, then Gemini's speech model) and the page plays the audio.
Suggestion: expose speechSynthesis, or document a native TTS module that a WebView app can bridge to.

FL-6. Record the screen of a Vega stick for a demo
Steps: tried the usual Android tools.
Expected: a screen recording command.
Actual: scrcpy/screenrecord are Android-only; no Vega equivalent on a stick.
Severity: Low
Workaround: filmed the TV with a phone.
Suggestion: `vega device screenrecord`.

FL-7. Amazon Devices Builder Tools MCP: first calls
Steps: started the MCP server (npm, v1.0.17) and called search_documentation.
Expected: results.
Actual: every call returned PROJECT_CONTEXT_REQUIRED until set_project_context was called; then target_platform "FireOS" returned only "Invalid arguments provided for tool search_documentation".
Severity: Medium
Workaround: called set_project_context({config:{}}) first; read the JSON schema to find {device_os:["fire_os"]}.
Suggestion: default to an empty context, and return the validation error (field, expected shape, allowed values).

FL-8. Test a Fire OS app without a device
Steps: looked for a Fire OS simulator for a cloud dev machine.
Expected: a simulator like the Vega Virtual Device.
Actual: none; the Android TV emulator needs KVM.
Severity: Medium
Workaround: compile checks plus a headless browser run of the web UI.
Suggestion: Fire OS images for the Vega Virtual Device, or a cloud device farm.
```

## Project Testing Link
https://aside-tv.onrender.com/tv/

## Testing instructions

```
No login needed.
1. In a desktop browser (Chrome), open https://aside-tv.onrender.com/tv/. It's on a free plan, so the first load can take up to a minute while the server wakes up.
2. Use the keyboard as the remote: arrow keys to move, Enter to select, Esc for Back.
3. Press Enter on Play. During the film press Up: choose "What just happened?" or "Who's that?". Try "Ask by phone" and scan the QR code to ask anything out loud.
4. On the home screen turn on Audio description to hear narration in the quiet stretches.
On a Fire TV Stick: Vega OS sticks install https://aside-tv.onrender.com/vpkg (steps in docs/VEGA.md); Fire OS sticks install https://aside-tv.onrender.com/apk (docs/SETUP.md).
```

## Feedback Question 1: Which developer tools, APIs, and SDKs did you use and for what?

```
- Vega SDK 0.24 and Vega CLI 1.4.5: the vegaWebview template and build for the Fire TV Stick 4K Select app (React Native for Vega + @amazon-devices/webview), Developer Mode enablement (vega devmode).
- Vega WebView: hosting our TV web app; allowSystemKeyEvents for the Back key, onMessage/postMessage to exit, media keys as DOM events.
- vda / vpm / vlcm on the device: installing and launching the package (through adb from Windows).
- Amazon Devices Builder Tools MCP server: Fire OS and Vega documentation search from our coding agent (remote key codes, WebView settings, Vega WebView migration and remote-input guides, VDA over TCP/IP).
- Fire OS (Android WebView, Kotlin): a second build for Fire OS sticks.
- Amazon Developer Console: developer registration and the vendor used for Developer Mode.
Not Amazon: Google Gemini API (video understanding, answers, speech fallback), Groq (gpt-oss, Qwen, Orpheus speech), Gemma, Kokoro (open-weight speech), FastAPI, Render, ffmpeg, Claude Code.
```

## Feedback Question 2: What worked well?

```
- Vega WebView template: from `vega project generate --template vegaWebview` to three working packages (armv7, aarch64, x86_64) in about 20 minutes; manifest validation caught nothing because the template is right.
- Vega WebView remote input: D-pad, Select and media keys arrive as standard DOM key events with the same key codes as Fire OS, so our web app needed only a Back/exit change. allowSystemKeyEvents and the postMessage exit pattern are well documented in the migration guide.
- Video playback in Vega WebView: our H.264 films played very smoothly on the 4K Select.
- vda being adb-compatible: installing from Windows with Google's adb worked first time.
- Developer Mode: once registered, `vega devmode enable-device --code` took a second; the device-code sign-in works from any browser.
- Builder Tools MCP: install in 30 seconds; its search found the Fire OS WebView settings we'd missed and the exact Vega remote-input mapping we needed.
```

## Feedback Question 3: What needs work?

```
- Vega CLI is macOS/Ubuntu only: Developer Mode can't be enabled from Windows without a Linux machine.
- `vega devmode login` reports a missing developer registration as "401 invalid_token, Authentication failed".
- `vega devmode login` fails on headless Linux without a desktop keyring (dbus-launch); no file fallback.
- No documented way to install a .vpkg without the Vega CLI (adb push + vpm install works, but we had to find it).
- No speech API in Vega WebView (window.speechSynthesis missing), which matters for accessibility apps.
- No screen recording on Vega sticks for demos and bug reports.
- No Fire OS simulator; the Vega Virtual Device covers Vega only.
- Builder Tools MCP: PROJECT_CONTEXT_REQUIRED on every call until set_project_context; invalid arguments don't say which field or what shape.
- Some Vega docs and the template target Vega OS 1.2; it's not obvious which devices have which OS version, and a community thread reports Live App Testing rejecting packages for 1.1 devices.
```

## Feedback Question 4: How was your onboarding experience?

```
- Vega SDK: the installer (get_vvm.sh) ran non-interactively on Ubuntu and installed the CLI, SDK and Virtual Device in about 10 minutes. Template to package in 20 minutes. Getting it onto a real stick took the longest: developer registration, Developer Mode from Windows, TCP/IP connection mode. About 90 minutes in total, most of it the Windows and registration issues above.
- Builder Tools MCP: about 15 minutes to useful answers, after working out the project-context step and the argument shape.
- Fire OS: standard Android tooling, about an hour to a working WebView app with leanback launcher and remote keys.
```

## Feedback Question 5: Would you build with these devices and services again?

```
Yes. A web app inside a thin native shell ran on both Fire OS and Vega OS with almost no platform-specific code, the Vega WebView played video smoothly and handled the remote well, and the TV is the right place for a shared, conversational feature like Aside. What would make it much easier next time: the Vega CLI on Windows (or Developer Mode from the Developer Console), a speech API in Vega WebView, and screen recording on Vega devices.
```

## Which AI tools have you leveraged?

```
Claude Code (Anthropic) to write, test and debug the code, directed and reviewed by me. Google Gemini (watching each film to build its timeline and audio description; answer fallback). Groq-hosted gpt-oss-120b, Qwen 3.8 27B and gpt-oss-20b (answers and the spoiler check), Gemma 4 (fallback), Kokoro-82M, Groq Orpheus and Gemini speech (reading answers and audio description aloud). Amazon Devices Builder Tools MCP server (Fire OS and Vega documentation from the coding agent).
```

## Level of learning
Significant

## AI value for career
Yes

## Checkboxes (you confirm these yourself)
Age of majority, eligible jurisdiction, not an employee or agent of the sponsors.
