import { Audio } from "@remotion/media";
import React from "react";
import { AbsoluteFill, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { FeatureScene, HookScene, LabTitleScene, OutroScene, ProofScene, SetupScene, WhatIfScene } from "./scenes";
import { beat, C, FormatProps } from "./theme";

// The timeline, in beats of the 110 bpm soundtrack (see video/music/compose.py, pit_window):
// 0-16 quiet intro, 16-32 build, 32 the drop, 64-68 the stop, 68 the final hit.
const CUTS = [0, 8, 16, 24, 32, 36, 46, 54, 64, 68, 77] as const;
const at = (i: number) => beat(CUTS[i]);
const len = (i: number) => beat(CUTS[i + 1]) - beat(CUTS[i]);

// A short dip through black at each cut between two busy layouts
const Dips: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = Math.max(0, ...[2, 3, 6, 7, 8].map(i => interpolate(Math.abs(frame - at(i)), [0, 4], [1, 0], { extrapolateRight: "clamp" })));
  return <AbsoluteFill style={{ background: C.bg, opacity, pointerEvents: "none" }} />;
};

export const Launch: React.FC<FormatProps> = ({ format }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Audio src={staticFile("music/pit-window.wav")} />
    <Sequence name="Hook" from={at(0)} durationInFrames={len(0)}>
      <HookScene format={format} />
    </Sequence>
    <Sequence name="Setup" from={at(1)} durationInFrames={len(1)}>
      <SetupScene format={format} durationInFrames={len(1)} />
    </Sequence>
    <Sequence name="Replay" from={at(2)} durationInFrames={len(2)}>
      <FeatureScene
        format={format} durationInFrames={len(2)}
        num="01" title="REPLAY" headline="Watch any race again."
        line="Every car on the map, lap by lap, with pit stops, flags and weather."
        clip="replay" from={1.6}
        focus={{ landscape: [900, 480], vertical: [520, 760] }} zoom={{ landscape: [1.4, 1.5], vertical: [1.1, 1.18] }}
      />
    </Sequence>
    <Sequence name="Debrief" from={at(3)} durationInFrames={len(3)}>
      <FeatureScene
        format={format} durationInFrames={len(3)}
        num="02" title="DEBRIEF" headline="See why it was won."
        line="Who climbed, who was fastest, and what every pit stop cost."
        clip="debrief" from={1.6}
        focus={{ landscape: [960, 560], vertical: [540, 900] }} zoom={{ landscape: [1.3, 1.36], vertical: [1.0, 1.05] }}
      />
    </Sequence>
    <Sequence name="Lab title" from={at(4)} durationInFrames={len(4)}>
      <LabTitleScene format={format} />
    </Sequence>
    <Sequence name="Strategy" from={at(5)} durationInFrames={len(5)}>
      <FeatureScene
        format={format} durationInFrames={len(5)}
        num="03" title="STRATEGY" headline="Move a pit stop. See where they finish."
        line="Monza 2024: Piastri drops his second stop."
        clip="strategy" from={0.9}
        focus={{ landscape: [960, 360], vertical: [540, 560] }} zoom={{ landscape: [1.2, 1.24], vertical: [1.0, 1.03] }}
      />
    </Sequence>
    <Sequence name="Verdict" from={at(6)} durationInFrames={len(6)}>
      <FeatureScene
        format={format} durationInFrames={len(6)}
        num="03" title="STRATEGY" headline="P1, not P2. With the odds."
        line="Every answer is 500 simulations, a range and a confidence level."
        clip="strategy" from={6.6}
        focus={{ landscape: [960, 420], vertical: [540, 470] }} zoom={{ landscape: [1.2, 1.28], vertical: [1.0, 1.06] }}
      />
    </Sequence>
    <Sequence name="Proof" from={at(7)} durationInFrames={len(7)}>
      <ProofScene format={format} durationInFrames={len(7)} />
    </Sequence>
    <Sequence name="What if" from={at(8)} durationInFrames={len(8)}>
      <WhatIfScene format={format} />
    </Sequence>
    <Sequence name="Outro" from={at(9)}>
      <OutroScene format={format} />
    </Sequence>
    <Dips />
  </AbsoluteFill>
);
