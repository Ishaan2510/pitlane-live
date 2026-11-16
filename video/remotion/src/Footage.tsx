import { Video } from "@remotion/media";
import React from "react";
import { interpolate, staticFile, useCurrentFrame } from "remotion";
import { C, Format, FPS } from "./theme";

type Props = {
  clip: string;            // footage/<clip>-<format>.mp4 (recorded by video/footage/record.mjs)
  format: Format;
  from: number;            // seconds into the clip where this shot starts
  rate?: number;           // playback speed
  box: { left: number; top: number; width: number; height: number };
  focus: [number, number]; // point of the recorded frame kept in the middle of the box
  zoom: [number, number];  // zoom at the start and end of the shot (1 = the frame covers the box)
  durationInFrames: number;
};

// A window onto real recorded footage of the site: a crop that can push in slowly.
export const Footage: React.FC<Props> = ({ clip, format, from, rate = 1, box, focus, zoom, durationInFrames }) => {
  const frame = useCurrentFrame();
  const fw = format === "vertical" ? 1080 : 1920;
  const fh = format === "vertical" ? 1920 : 1080;
  const z = interpolate(frame, [0, durationInFrames], zoom, { extrapolateRight: "clamp" });
  const s = Math.max(box.width / fw, box.height / fh) * z;
  const w = fw * s, h = fh * s;
  const left = Math.min(0, Math.max(box.width - w, box.width / 2 - focus[0] * s));
  const top = Math.min(0, Math.max(box.height - h, box.height / 2 - focus[1] * s));
  return (
    <div style={{ position: "absolute", ...box, overflow: "hidden", border: `1px solid ${C.border}`, background: C.bg }}>
      {/* the Video draws at its natural size unless its box sets it */}
      <div style={{ position: "absolute", left, top, width: w, height: h }}>
        <Video
          src={staticFile(`footage/${clip}-${format}.mp4`)}
          trimBefore={Math.round(from * FPS)}
          playbackRate={rate}
          muted
          style={{ width: "100%", height: "100%", objectFit: "fill" }}
        />
      </div>
    </div>
  );
};
