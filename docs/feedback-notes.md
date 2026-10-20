# Build notes for the product feedback and friction log

Raw notes, written as things happened. The submission's feedback answer and friction log are built from these.

## Amazon Devices Builder Tools MCP (v1.0.17), 2026-10-20
- Install: `npm i @amazon-devices/amazon-devices-buildertools-mcp` took about 30 s. The server started over stdio and listed 9 tools: docs search and read, Perfetto trace analysis, CPU hot functions, crash symbolication, workflow status, project context.
- Friction: every call returned `PROJECT_CONTEXT_REQUIRED` until `set_project_context` was called first. The message says exactly what to do, which helped, but a client that isn't an IDE agent has no way to know this up front. Suggestion: default to an empty context instead of refusing.
- Friction: `search_documentation` with `target_platform: "FireOS"` returned only "Invalid arguments provided for tool search_documentation". It doesn't say which argument or what shape is expected. The schema wants `{"device_os": ["fire_os"]}`. Suggestion: return the validation error (field, expected type, allowed values).
- Worked well: the Fire OS search found the WebView guide's two required settings (`setUseWideViewPort`, `setLoadWithOverviewMode`) that our wrapper was missing, and the remote key table (Play/Pause 179, Rewind 227, Fast Forward 228; Menu and Home can't be captured by web apps). Both changed our code.
- Observation: most Fire OS documents are written as steps in a Fire OS <-> Vega port. A plain "build a Fire OS WebView app" starting point is harder to find.

## Fire OS testing without a device in the loop
- The rules allow a demo on "the Fire TV/Vega simulator", but the Vega Virtual Device only runs Vega OS. Fire OS has no simulator of its own, and an Android TV emulator needs KVM, which a cloud dev container doesn't have. So every Fire OS check before Jannet's stick was a compile check plus a headless-browser run of the web app.

## Web apps on Fire OS
- Menu can't be captured by a pure web app (Amazon's table says so). Aside uses Menu to open its question bar, so the wrapper catches KEYCODE_MENU in `dispatchKeyEvent` and forwards it to the page.

## Vega Developer Mode from a Windows laptop, 2026-10-20/21
- Jannet's stick turned out to be Vega OS (Fire TV Stick 4K Select), so the Android APK couldn't run. We rebuilt the shell from the `vegaWebview` template (SDK 0.24.12112, CLI 1.4.5) in about 20 minutes. The template, WebView key handling and build were smooth: three VPKGs (armv7, aarch64, x86_64) from one `npm run build:release`.
- Friction: the Vega CLI supports macOS and Ubuntu only. The laptop is Windows. Developer Mode enabling is a cloud step (device-code sign-in plus the TV's code), so we ran `vega devmode login` / `enable-device` from a Linux cloud session while Jannet approved on her own browser, then signed the CLI out.
- Friction: with an Amazon account that wasn't yet registered as a developer, `vega devmode login` failed with `Failed to verify vendor registration: http 401 invalid_token "Authentication failed"`. It looked like a token or region problem; the real cause was the missing developer registration (the CLI has a clearer "No vendors found" message, but this path never reaches it). Suggestion: when the account has no developer profile, say so and link to the registration page.
- Friction: on a headless Linux box, login then failed at the very end: `failed to store token in OS password management system: exec: "dbus-launch": executable file not found`. Fix: install `dbus-x11 gnome-keyring` and run the CLI inside `dbus-run-session` with an unlocked keyring. Suggestion: fall back to a file-based token store (with a warning) when no keyring is available, as many CLIs do.
- Worked well: once registered, `enable-device --code` took a second and the stick rebooted into Developer Mode. The `vda` device tool is a renamed `adb` (protocol 41), so `vega device install-app` is `push` + `vpm install`.
