# Installing Aside on a Vega OS Fire TV Stick (from a Windows laptop)

Vega OS sticks (Fire TV Stick 4K Select, Fire TV Stick HD 2026 and newer) don't run Android apps, so they use the Vega build of Aside (`vega-app/`, package at `<server>/vpkg`). Installing it takes three steps: turn on Developer Mode, switch the stick to network connections, and install from the laptop. About 20 minutes, once.

You need: a free Amazon Developer account (developer.amazon.com), the stick and the laptop on the same Wi-Fi.

## 1. Update the stick and turn on Developer Mode

1. **Settings → My Fire TV → About → Check for Updates.** Install anything offered (the Vega app needs Vega OS 1.2 or newer).
2. In **About**, highlight your device name and press Select **7 times** until it says you're a developer.
3. Press Back. Open **Developer Options → Developer Mode → Continue**. The TV shows a **6-digit code**.
4. The code is confirmed with Amazon by the Vega command-line tool, signed in with your developer account (`vega devmode login`, then `vega devmode enable-device --code <code>`). The tool doesn't run on Windows, so Claude runs these two commands from its cloud session:
   - Claude sends you a web address and a short sign-in code. Open the address on your phone or laptop, sign in with your **Amazon Developer** account and enter the code. This lets the Vega tool act for your developer account; Claude signs it out (`vega devmode logout`) as soon as the stick is enabled.
   - Send Claude the TV's 6-digit code. The stick reboots with Developer Mode on.

## 2. Switch the stick to network connections

1. **Settings → My Fire TV → About → Network**: note the **IP address** (for example `192.168.1.23`).
2. **Settings → My Fire TV → Developer Options → Connection Mode → TCP/IP → Use standard port 5555 → Continue.** The stick reboots.

## 3. Install Aside from the laptop

1. Download Google's **SDK Platform-Tools for Windows** from [developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools) and unzip it. It contains `adb.exe`. (Vega's own device tool is a version of `adb`, so the standard one talks to the stick.)
2. Open `https://aside-tv.onrender.com/vpkg` in the laptop's browser. It downloads `aside.vpkg`. Move it into the unzipped `platform-tools` folder.
3. Open a terminal in that folder (Shift + right-click inside the folder → **Open in Terminal**) and run, one line at a time, with your stick's IP:
   ```
   .\adb connect 192.168.1.23:5555
   .\adb push aside.vpkg /tmp/aside.vpkg
   .\adb shell vpm install /tmp/aside.vpkg
   .\adb shell vlcm launch-app orpheus://com.jannetekka.aside.main
   ```
   If the TV asks whether to allow the computer, tick **Always allow** and choose **OK**, then repeat the line that failed.
4. Aside opens on the TV. Afterwards it's in **Your Apps & Channels**.

To update the app later, repeat step 3 (download the new `aside.vpkg`, then push and install again). Most updates don't need this, because the screens and answers come from the server.

## If something fails

- `adb connect` says *cannot connect*: check the IP, that Connection Mode shows TCP/IP, and that the laptop is on the same Wi-Fi (not a guest network).
- `vpm install` complains about the OS version: run **Check for Updates** on the stick and try again; tell Claude the Vega OS version shown under About.
- Anything else: copy the exact message to Claude.

## Recording the screen for the demo

Screen-mirroring tools such as scrcpy are built for Android and don't work with Vega. Film the TV with your phone instead: phone on a stand or a pile of books, landscape, TV filling the frame, room lights down. It also records the sound. See [DEMO.md](DEMO.md) for the shot list.
