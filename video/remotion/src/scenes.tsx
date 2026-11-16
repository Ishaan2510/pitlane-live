import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Footage } from "./Footage";
import { bebas, C, Format, FormatProps, mono, rise, sans } from "./theme";

const V = (f: Format) => f === "vertical";

// Words of a line arriving one after another
const Words: React.FC<{ text: string; start: number; step?: number; style?: React.CSSProperties }> = ({ text, start, step = 3, style }) => {
  const frame = useCurrentFrame();
  return (
    <div style={style}>
      {text.split(" ").map((w, i) => {
        const k = rise(frame, start + i * step, start + i * step + 10);
        return (
          <span key={i} style={{ display: "inline-block", opacity: k, translate: `0 ${(1 - k) * 28}px`, marginRight: "0.24em" }}>{w}</span>
        );
      })}
    </div>
  );
};

const Glow: React.FC<{ strength?: number; y?: string }> = ({ strength = 0.2, y = "35%" }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% ${y}, rgba(225,6,0,${strength}), transparent 62%)` }} />
);

// ── 1. Hook ──────────────────────────────────────────────────────────────────
export const HookScene: React.FC<FormatProps> = ({ format }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center", padding: v ? 90 : 160 }}>
      <Glow strength={interpolate(frame, [0, 120], [0.05, 0.22], { extrapolateRight: "clamp" })} />
      <div style={{ fontFamily: mono, fontSize: v ? 34 : 30, letterSpacing: "0.3em", color: C.red, opacity: rise(frame, 4, 20), marginBottom: 36 }}>PITLANE LIVE</div>
      <Words text="EVERY RACE HAS A STORY." start={10} step={4} style={{ fontFamily: bebas, fontSize: v ? 190 : 210, lineHeight: 0.95, color: C.text, letterSpacing: "0.02em" }} />
    </AbsoluteFill>
  );
};

// ── 2. Setup over the race library ───────────────────────────────────────────
export const SetupScene: React.FC<FormatProps & { durationInFrames: number }> = ({ format, durationInFrames }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  const box = { left: 0, top: 0, width: v ? 1080 : 1920, height: v ? 1920 : 1080 };
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", inset: 0, opacity: 0.22, filter: "blur(2px)" }}>
        <Footage clip="library" format={format} from={0.5} box={box} focus={[box.width / 2, box.height / 2]} zoom={[1.08, 1.0]} durationInFrames={durationInFrames} />
      </div>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(8,8,8,0.6), rgba(8,8,8,0.95))" }} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", padding: v ? 90 : 200 }}>
        <Words text="68 RACES. EVERY LAP. EVERY STOP." start={2} step={3} style={{ fontFamily: bebas, fontSize: v ? 150 : 170, lineHeight: 0.95, color: C.text }} />
        <div style={{ marginTop: 44, fontFamily: sans, fontSize: v ? 46 : 44, color: C.muted, opacity: rise(frame, 30, 46) }}>Built from real timing data, 2024 to today.</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Feature scenes: a label, a headline, a line, and the real site in use ────
type FeatureProps = FormatProps & {
  durationInFrames: number;
  num: string;
  title: string;
  headline: string;
  line: string;
  clip: string;
  from: number;
  focus: { landscape: [number, number]; vertical: [number, number] };
  zoom: { landscape: [number, number]; vertical: [number, number] };
};

export const FeatureScene: React.FC<FeatureProps> = ({ format, durationInFrames, num, title, headline, line, clip, from, focus, zoom }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  const card = v ? { left: 60, top: 740, width: 960, height: 700 } : { left: 760, top: 150, width: 1080, height: 780 };
  const enter = rise(frame, 0, 16);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", ...(v ? { left: 80, top: 260, right: 80 } : { left: 110, top: 300, width: 560 }) }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 18, opacity: enter, translate: `0 ${(1 - enter) * 20}px` }}>
          <span style={{ fontFamily: mono, fontSize: v ? 34 : 30, color: C.red, letterSpacing: "0.1em" }}>{num}</span>
          <span style={{ fontFamily: mono, fontSize: v ? 34 : 30, color: C.text, letterSpacing: "0.3em" }}>{title}</span>
        </div>
        <div style={{ height: 3, background: C.red, width: (v ? 140 : 120) * rise(frame, 4, 20), margin: "22px 0 26px" }} />
        <Words text={headline} start={6} step={3} style={{ fontFamily: bebas, fontSize: v ? 104 : 96, lineHeight: 0.95, color: C.text }} />
        <div style={{ marginTop: 26, fontFamily: sans, fontSize: v ? 40 : 34, lineHeight: 1.4, color: C.muted, opacity: rise(frame, 22, 38), translate: `0 ${(1 - rise(frame, 22, 38)) * 14}px` }}>{line}</div>
      </div>
      <div style={{ opacity: rise(frame, 2, 16), translate: `${v ? 0 : (1 - rise(frame, 2, 18)) * 60}px ${v ? (1 - rise(frame, 2, 18)) * 60 : 0}px` }}>
        <Footage clip={clip} format={format} from={from} box={card} focus={v ? focus.vertical : focus.landscape} zoom={v ? zoom.vertical : zoom.landscape} durationInFrames={durationInFrames} />
      </div>
    </AbsoluteFill>
  );
};

// ── The Strategy Lab title slam (on the drop) ────────────────────────────────
export const LabTitleScene: React.FC<FormatProps> = ({ format }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  const s = interpolate(frame, [0, 10], [1.35, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <Glow strength={0.3} y="50%" />
      <div style={{ fontFamily: mono, fontSize: v ? 34 : 32, letterSpacing: "0.3em", color: C.red, opacity: rise(frame, 6, 18), marginBottom: 20 }}>NEW</div>
      <div style={{ fontFamily: bebas, fontSize: v ? 220 : 260, lineHeight: 0.9, color: C.text, scale: s }}>THE STRATEGY<br />LAB</div>
      <AbsoluteFill style={{ background: "#fff", opacity: interpolate(frame, [0, 8], [0.75, 0], { extrapolateRight: "clamp" }) }} />
    </AbsoluteFill>
  );
};

// ── Numbers: how good the model is, beside the degradation chart ─────────────
export const ProofScene: React.FC<FormatProps & { durationInFrames: number }> = ({ format, durationInFrames }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  const card = v ? { left: 60, top: 980, width: 960, height: 520 } : { left: 760, top: 150, width: 1080, height: 780 };
  const stat = (big: string, small: string, at: number) => (
    <div style={{ opacity: rise(frame, at, at + 14), translate: `0 ${(1 - rise(frame, at, at + 14)) * 18}px`, marginBottom: v ? 26 : 34 }}>
      <div style={{ fontFamily: bebas, fontSize: v ? 120 : 112, lineHeight: 0.9, color: C.text }}>{big}</div>
      <div style={{ fontFamily: sans, fontSize: v ? 34 : 30, color: C.muted, marginTop: 6 }}>{small}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", ...(v ? { left: 80, top: 250, right: 80 } : { left: 110, top: 190, width: 600 }) }}>
        <div style={{ fontFamily: mono, fontSize: v ? 32 : 28, color: C.red, letterSpacing: "0.24em", marginBottom: 26, opacity: rise(frame, 0, 12) }}>TESTED ON EVERY RACE</div>
        {v ? (
          <div style={{ display: "flex", gap: 60 }}>
            {stat("0.53 s", "error per lap, on drivers the model never saw", 6)}
            {stat("65 / 68", "races with a tyre model", 16)}
          </div>
        ) : (
          <>
            {stat("0.53 s", "error per lap, on drivers the model never saw", 6)}
            {stat("65 / 68", "races with a tyre model", 16)}
            {stat("500", "simulations behind every answer", 26)}
          </>
        )}
      </div>
      <div style={{ opacity: rise(frame, 2, 16) }}>
        <Footage clip="degradation" format={format} from={2.0} box={card} focus={v ? [540, 760] : [960, 560]} zoom={v ? [1.0, 1.05] : [1.25, 1.32]} durationInFrames={durationInFrames} />
      </div>
    </AbsoluteFill>
  );
};

// ── The question, on black (the music stops here) ───────────────────────────
export const WhatIfScene: React.FC<FormatProps> = ({ format }) => {
  const v = V(format);
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center", padding: 100 }}>
      <Words text="SO, WHAT IF THEY'D STAYED OUT?" start={2} step={4} style={{ fontFamily: bebas, fontSize: v ? 170 : 190, lineHeight: 0.95, color: C.text }} />
    </AbsoluteFill>
  );
};

// ── Outro ────────────────────────────────────────────────────────────────────
export const OutroScene: React.FC<FormatProps> = ({ format }) => {
  const frame = useCurrentFrame();
  const v = V(format);
  const s = interpolate(frame, [0, 12], [1.2, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <Glow strength={0.28} y="45%" />
      <div style={{ fontFamily: bebas, fontSize: v ? 240 : 290, letterSpacing: "0.08em", lineHeight: 1, color: C.text, scale: s }}>
        PITLANE<span style={{ color: C.red }}>.</span>
      </div>
      <div style={{ fontFamily: sans, fontSize: v ? 52 : 52, color: C.muted, marginTop: 40, opacity: rise(frame, 10, 24), translate: `0 ${(1 - rise(frame, 10, 24)) * 14}px`, maxWidth: v ? 900 : 1400, lineHeight: 1.35 }}>
        Ask your own what-if.{v ? <br /> : " "}Share the link.
      </div>
      <AbsoluteFill style={{ background: "#fff", opacity: interpolate(frame, [0, 8], [0.7, 0], { extrapolateRight: "clamp" }) }} />
    </AbsoluteFill>
  );
};


