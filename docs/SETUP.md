# Setting up Aside: server, Fire TV, recording

Three jobs, in this order. Each takes about five minutes.

## 1. Deploy the server on Render (free)

You need two free API keys first. Neither needs a card. Never paste a key into a chat or a file in this repo.

- **Gemini**: [aistudio.google.com](https://aistudio.google.com) → Get API key → Create API key (in a new project).
- **Groq**: [console.groq.com](https://console.groq.com) → API Keys → Create API Key.

Then:

1. Open [dashboard.render.com](https://dashboard.render.com) and sign in with GitHub.
2. **New** → **Blueprint** → pick `JannetEkka/aside-tv`. Render reads `render.yaml`.
3. It asks for `GEMINI_API_KEY` and `GROQ_API_KEY`: paste each key there. Then **Apply**.
4. Wait for the deploy to show **Live** (3 to 5 minutes). The address is at the top of the service page, something like `https://aside-tv.onrender.com`. Send that address to Claude.

Free Render services fall asleep after 15 minutes without visitors, and the first visit then takes about a minute. Before you use the TV or record, open the address in your phone's browser once to wake it.

## 2. Install Aside on the Fire TV Stick

Once only:

1. **Turn on developer options.** Settings → My Fire TV → About. Select your device name 7 times until it says you're a developer.
2. **Install Downloader.** On the Fire TV home screen, search for **Downloader** (the orange app by AFTVnews) and install it. It's free.
3. **Allow it to install apps.** Settings → My Fire TV → Developer Options → Install unknown apps → **Downloader: On**. On older sticks the setting is called *Apps from Unknown Sources*.

Then install Aside:

4. Open Downloader. In the address box, type your Render address followed by `/apk`, for example `aside-tv.onrender.com/apk`, then **Go**.
5. When the download finishes, choose **Install**, then **Done**. When Downloader offers to delete the file, say yes; the app stays installed.
6. Aside is now under **Your Apps & Channels** (hold the Home button → Apps). To put it on the home row, highlight it, press the Menu button (☰), then **Move to front**.

To update later, repeat steps 4 and 5. The app installs over the old one.

**If Downloader doesn't show up in search** (it's sometimes hidden in some regions): look under Find → App Store → Categories → **Utilities**; the publisher is AFTVnews. Don't install look-alike "downloader" apps from other publishers. Or install from a laptop instead:

1. On the TV: Settings → My Fire TV → Developer Options → **ADB debugging: On**. Note the IP address under Settings → My Fire TV → About → Network.
2. On the laptop: download [scrcpy](https://github.com/Genymobile/scrcpy#get-the-app) (it includes `adb`; you'll use it for recording too) and unzip it. Open `https://aside-tv.onrender.com/apk` in the laptop's browser to download `aside.apk`, and move it into the scrcpy folder.
3. Open a terminal in that folder (on Windows: Shift + right-click → *Open in Terminal*) and run:
   ```
   adb connect <IP>:5555
   adb install -r aside.apk
   ```
   The TV asks to allow the computer the first time: tick *Always allow* and choose OK, then run the second line again if it failed. It prints `Success`.

**Using it:** the remote's D-pad moves around and the centre button selects. During a film, **Up** or **Menu (☰)** opens Aside's questions, **Left/Right** skip 10 seconds, **Back** closes whatever is open. **Ask by phone** shows a QR code: scan it with your phone's camera and ask out loud.

## 3. Record the screen for the demo

Nobody needs to be on camera. Pick one of these.

**A. Record straight from the stick (sharpest).** Needs a laptop on the same Wi-Fi.
1. On the TV: Settings → My Fire TV → Developer Options → **ADB debugging: On**. Note the stick's IP address under Settings → My Fire TV → About → Network.
2. On the laptop, install [scrcpy](https://github.com/Genymobile/scrcpy#get-the-app) (it includes `adb`).
3. Run `adb connect <IP>:5555` and accept the prompt that appears on the TV.
4. Run `scrcpy --record aside-take1.mp4`. Use the TV remote as normal, and close the scrcpy window to stop. On newer sticks (Fire OS 8) the recording includes sound; on older ones it's silent, and Claude adds the narration and audio afterwards.

**B. Film the TV with your phone.** Put the phone on a stand or a pile of books, landscape, with the TV filling the frame, and turn the room lights down. It records the sound from the TV too.

Follow the shot list in [DEMO.md](DEMO.md). Upload each take to Google Drive and tell Claude; Claude edits them into the final video.
