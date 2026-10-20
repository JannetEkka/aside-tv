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
