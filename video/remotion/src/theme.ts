import { loadFont as loadBebas } from "@remotion/google-fonts/BebasNeue";
import { loadFont as loadMono } from "@remotion/google-fonts/DMMono";
import { loadFont as loadSans } from "@remotion/google-fonts/WorkSans";
import { Easing, interpolate } from "remotion";

// The site's own type and colours (frontend/src/assets/theme.css)
export const bebas = loadBebas("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
export const mono = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;
export const sans = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;

export const C = {
  bg: "#080808",
  card: "#111111",
  border: "#2a2a2a",
  text: "#f5f5f5",
  muted: "#9a9a9a",
  red: "#e10600",
  green: "#66dd88",
};

export const FPS = 30;
// The soundtrack ("Pit Window", video/music/compose.py) is 110 bpm: every cut is on a beat.
export const BPM = 110;
export const beat = (n: number) => Math.round((n * 60 * FPS) / BPM);
export const DURATION = 42 * FPS;

export type Format = "landscape" | "vertical";
export type FormatProps = { format: Format };

export const outExpo = Easing.bezier(0.16, 1, 0.3, 1);

// 0 -> 1 between frames a and b, clamped, with an ease-out
export const rise = (frame: number, a: number, b: number) =>
  interpolate(frame, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: outExpo });
