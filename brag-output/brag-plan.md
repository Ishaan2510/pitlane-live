# /brag plan: Pitlane Live

**What it is:** a website that replays every F1 race since 2024 from real timing data,
explains it, and lets you rewrite a driver's pit strategy to see where they would have finished.
**For:** F1 fans who argue about strategy calls on Sunday night.
**Sets it apart:** it doesn't just replay the race, it answers "what if", with an honest range.
**Most impressive claim:** drag a pit stop and the verdict changes live: "PIA finishes P1, not P2",
500 simulations, a range, a confidence tag.
**Visual hook:** the five F1 start lights, synced to the beat, then lights out.
**Real UI shown:** the Replay (Monaco 2025 playing), the Strategy Lab drag (Monza 2024, Piastri's
second stop dragged off the bar), the verdict card.
**Tone:** cinematic (trailer-scale type, hard cuts on the beat), with the F1 start as the joke-free
hook. **Share caption:** "What if they'd pitted a lap later? Now you can check."

**Personal data:** none. Driver codes and race data are public timing data; no user accounts
or usernames appear.

## Visual identity (from the project)
- Background `#080808`, text `#f5f5f5`, accent `#e10600` (`theme.css`)
- Display: Bebas Neue; labels: DM Mono; body: Work Sans
- Square corners, 1 px borders, no gradients on UI (the video adds a soft red glow only behind
  the start lights)

## Music
"Lights Out", original, synthesised (`video/music/compose.py lights-out`), D minor, **120 bpm**
(beat = 0.5 s). Five start-light beeps on beats 0-4, riser on beat 5, the drop on beat 6
(3.0 s), logo hit on beat 34 (17.0 s), tail to 20.0 s. Every cut below is on a beat.

## Storyboard (20.0 s, 30 fps, 600 frames)

| # | Time | Beats | Scene | On screen |
|---|---|---|---|---|
| 1 | 0.0-3.0 | 0-6 | Hook | Five start lights come on one per beat. "WHAT IF THEY'D PITTED A LAP LATER?" (on by 0.9 s, 2.1 s to read) |
| 2 | 3.0-6.0 | 6-12 | Reveal | Lights out, flash. **PITLANE.** wordmark slams in. "Every F1 race. Replayed, debriefed, rewritten." |
| 3 | 6.0-10.0 | 12-20 | Highlight 1 | "01 REPLAY ANY RACE" + Monaco 2025 replay playing (real footage), slow push-in |
| 4 | 10.0-14.0 | 20-28 | Highlight 2 | "02 MOVE THE PIT STOP" + Piastri's second stop dragged off the bar (real footage) |
| 5 | 14.0-17.0 | 28-34 | Highlight 3 | "03 SEE THE ODDS" + zoom on the verdict: "PIA FINISHES P1, NOT P2", "P1 to P2 in 80% of 500 simulations" |
| 6 | 17.0-20.0 | 34-40 | Outro | **PITLANE.** wordmark, "Ask your own what-if. Share the link." (the address goes in the post text, not the video) |

Vertical (1080x1920): same timeline; footage is the phone layout of the site; every line meant
to be read sits between y 250 and 1536, away from the right 140 px in the lower half.

Transitions: hard cuts on beats with a 4-frame dip through black between scenes 2-3, 3-4 and
5-6 (no crossfades between busy layouts).
