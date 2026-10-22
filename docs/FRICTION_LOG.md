# Aside: friction log

Developer-tool friction met while building [Aside](https://github.com/JannetEkka/aside-tv) for Build, Ship, Shape: Amazon Developer Hackathon (Fire TV track), on a Fire TV Stick 4K Select (Vega OS) from a Windows laptop, October 2026. Severity: High = blocked without a workaround, Medium = cost an hour or more, Low = an inconvenience.

| # | Task | Severity |
|---|---|---|
| [FL-1](#fl-1) | Enable Developer Mode on a Vega stick from a Windows laptop | High |
| [FL-2](#fl-2) | `vega devmode login` with an account not yet registered as a developer | Medium |
| [FL-3](#fl-3) | `vega devmode login` on a headless Linux machine | Medium |
| [FL-4](#fl-4) | Install a .vpkg without the Vega CLI | Medium |
| [FL-5](#fl-5) | Read answers aloud in a Vega WebView app | Medium (an accessibility feature) |
| [FL-6](#fl-6) | Record the screen of a Vega stick for a demo | Low |
| [FL-7](#fl-7) | Amazon Devices Builder Tools MCP: first calls | Medium |
| [FL-8](#fl-8) | Test a Fire OS app without a device | Medium |

## FL-1

- **Task attempted:** Enable Developer Mode on a Vega stick from a Windows laptop
- **Steps taken:** Settings > About > device name x7 > Developer Options > Developer Mode > Continue (6-digit code); looked for the Vega CLI on Windows.
- **Expected:** a way to confirm the code from Windows or the browser.
- **Actual:** the Vega CLI supports macOS and Ubuntu only.
- **Severity:** High
- **Workaround:** ran `vega devmode login` and `enable-device --code` on a Linux machine (the sign-in is a device-code flow, so the developer approved it in her own browser), then signed the CLI out.
- **Suggestion:** a Windows CLI build, or a "Enable a device" page in the Developer Console that takes the TV's code.

## FL-2

- **Task attempted:** `vega devmode login` with an account not yet registered as a developer
- **Steps taken:** approved the device-code sign-in with a normal Amazon account.
- **Expected:** "This account isn't registered as an Amazon Developer. Register at developer.amazon.com."
- **Actual:** "Failed to verify vendor registration: http 401: invalid_token, Authentication failed". It looked like a token or region problem (the account was originally amazon.in), and we spent three sign-in attempts on it.
- **Severity:** Medium
- **Workaround:** completed developer registration, then signed in again.
- **Suggestion:** detect the missing developer profile and say so, with a link.

## FL-3

- **Task attempted:** `vega devmode login` on a headless Linux machine
- **Steps taken:** completed the sign-in.
- **Expected:** token saved.
- **Actual:** "failed to store token in OS password management system: exec: dbus-launch: executable file not found".
- **Severity:** Medium
- **Workaround:** installed dbus-x11 and gnome-keyring and ran the CLI inside `dbus-run-session` with an unlocked keyring.
- **Suggestion:** fall back to a file-based token store (with a warning) when no keyring exists, or document the requirement.

## FL-4

- **Task attempted:** Install a .vpkg without the Vega CLI
- **Steps taken:** needed to install from Windows.
- **Expected:** a documented route.
- **Actual:** undocumented; we found that `vega device install-app` is `vda push` + `vda shell vpm install`, and that vda is a renamed adb (protocol 41).
- **Severity:** Medium
- **Workaround:** Google's platform-tools adb: `adb connect`, `adb push aside.vpkg /tmp/`, `adb shell vpm install /tmp/aside.vpkg`, `adb shell vlcm launch-app orpheus://<component-id>`. Worked first time.
- **Suggestion:** document this as the supported path for machines without the Vega CLI.

## FL-5

- **Task attempted:** Read answers aloud in a Vega WebView app
- **Steps taken:** called window.speechSynthesis.
- **Expected:** speech, as in Chromium.
- **Actual:** not available in Vega WebView (confirmed by community threads); no WebView-level TTS bridge documented.
- **Severity:** Medium (an accessibility feature)
- **Workaround:** the server renders speech (pre-recorded Kokoro audio, then Groq Orpheus, then Gemini's speech model) and the page plays the audio.
- **Suggestion:** expose speechSynthesis, or document a native TTS module that a WebView app can bridge to.

## FL-6

- **Task attempted:** Record the screen of a Vega stick for a demo
- **Steps taken:** tried the usual Android tools.
- **Expected:** a screen recording command.
- **Actual:** scrcpy/screenrecord are Android-only; no Vega equivalent on a stick.
- **Severity:** Low
- **Workaround:** for the demo video, recorded the same web app in a desktop browser (headless Chromium driven like a remote), so the video doesn't show the stick itself.
- **Suggestion:** `vega device screenrecord`.

## FL-7

- **Task attempted:** Amazon Devices Builder Tools MCP: first calls
- **Steps taken:** started the MCP server (npm, v1.0.17) and called search_documentation.
- **Expected:** results.
- **Actual:** every call returned PROJECT_CONTEXT_REQUIRED until set_project_context was called; then target_platform "FireOS" returned only "Invalid arguments provided for tool search_documentation".
- **Severity:** Medium
- **Workaround:** called set_project_context({config:{}}) first; read the JSON schema to find {device_os:["fire_os"]}.
- **Suggestion:** default to an empty context, and return the validation error (field, expected shape, allowed values).

## FL-8

- **Task attempted:** Test a Fire OS app without a device
- **Steps taken:** looked for a Fire OS simulator for a cloud dev machine.
- **Expected:** a simulator like the Vega Virtual Device.
- **Actual:** none; the Android TV emulator needs KVM.
- **Severity:** Medium
- **Workaround:** compile checks plus a headless browser run of the web UI.
- **Suggestion:** Fire OS images for the Vega Virtual Device, or a cloud device farm.
