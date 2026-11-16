import React from "react";
import { Composition } from "remotion";
import { Launch } from "./Launch";
import { DURATION, FPS } from "./theme";

// Two versions of the same video: 16:9 for the README, YouTube and LinkedIn,
// 9:16 for Reels, TikTok and Shorts.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Launch" component={Launch} durationInFrames={DURATION} fps={FPS} width={1920} height={1080} defaultProps={{ format: "landscape" as const }} />
    <Composition id="LaunchVertical" component={Launch} durationInFrames={DURATION} fps={FPS} width={1080} height={1920} defaultProps={{ format: "vertical" as const }} />
  </>
);
