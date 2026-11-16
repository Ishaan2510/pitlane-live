# Launch videos

Two launch videos for Pitlane Live, each in 16:9 (1920x1080) and 9:16 (1080x1920), 30 fps.

| Video | Length | Made with | Feel | Use it for |
|---|---|---|---|---|
| **Teaser** ("Lights Out") | 20 s | the `/brag` workflow: an HTML page rendered frame by frame in headless Chrome | Punchy hook: the five F1 start lights, lights out, three features, logo | LinkedIn and X posts, Reels, the first thing people see |
| **Walkthrough** ("Pit Window") | 42 s | [Remotion](https://www.remotion.dev) (React) | Film-score build, explains Replay, Debrief and the Strategy Lab with the accuracy numbers | The launch post, YouTube, the README |

Both use real footage of the site, recorded from the running app, and original music
synthesised in code, so they can be posted anywhere without copyright claims.

The finished files are in `docs/media/` (16:9) and in the folders listed below.

## The pieces

```
video/
├── music/compose.py          Original soundtracks, synthesised with numpy (no samples)
├── footage/record.mjs        Records the real site in use, frame by frame, from headless Chrome
├── brag/composition.html     The teaser: every frame is a pure function of time
├── brag/render.mjs           Renders it frame by frame and adds the music
└── remotion/                 The walkthrough as a Remotion project (src/Launch.tsx)
brag-output/                  The teaser's plan, share copy and final MP4s
```

## Rebuild everything

Recorded footage, music files and renders are not committed (they are large and come from
the scripts). From the repository root, with Node 20+, Python 3.11 (numpy, scipy), ffmpeg
and Google Chrome installed:

```bash
# 1. Music
python video/music/compose.py lights-out video/music/lights-out.wav
python video/music/compose.py pit-window video/music/pit-window.wav

# 2. Serve the site and start a headless Chrome for the recorder
cd frontend && npm run build && npx vite preview --port 4173     # leave running
"C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --remote-debugging-port=9555 --user-data-dir=%TEMP%/pitlane-rec   # leave running

# 3. Footage: replay strategy strategyCharts debrief degradation library, in both shapes
SITE=http://localhost:4173 node video/footage/record.mjs replay landscape video/footage/raw
SITE=http://localhost:4173 node video/footage/record.mjs replay vertical video/footage/raw
#    ... and the same for the other clips

# 4. The teaser
node video/brag/render.mjs landscape brag-output/brag.mp4
node video/brag/render.mjs vertical  brag-output/brag-vertical.mp4

# 5. The walkthrough: encode the footage for Remotion, then render
for d in video/footage/raw/*/; do ffmpeg -framerate 30 -i $d/f%05d.jpg -c:v libx264 -crf 20 -pix_fmt yuv420p -g 15 video/remotion/public/footage/$(basename $d).mp4; done
cp video/music/pit-window.wav video/remotion/public/music/
cd video/remotion && npm install
npx remotion studio                                  # preview and edit
npx remotion render Launch out/launch-landscape.mp4
npx remotion render LaunchVertical out/launch-vertical.mp4
```

## Editing

- **Teaser:** timings, text and crops are in the `setTime()` timeline at the bottom of
  `brag/composition.html`. Every cut is on a beat of the 120 bpm track (0.5 s).
- **Walkthrough:** `remotion/src/Launch.tsx` lists the scenes in beats of the 110 bpm track;
  each scene's text, footage clip, crop and zoom are props there. `remotion studio` shows it
  live.
- **Music:** `music/compose.py` holds both arrangements (`lights_out`, `pit_window`). Change
  the tempo there and the cut points in the two timelines together.

## Music and licences

The soundtracks are original and synthesised from scratch, so they are free to use anywhere.
To use a commercial song instead (for example on Instagram Reels or TikTok, which license
songs inside their apps), post the `-nomusic` version and add the song in the app. Do not
add copyrighted music, including instrumental versions of film scores, to the files
themselves: LinkedIn and YouTube will mute or block the video.

Remotion is free for individuals and companies of up to 3 people; see its
[licence](https://www.remotion.dev/docs/license).
