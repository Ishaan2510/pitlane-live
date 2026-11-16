"""
Original soundtracks for the Pitlane Live launch videos, synthesised from scratch with
numpy (no samples, no third-party music), so the videos can be posted anywhere.

    python video/music/compose.py lights-out out.wav     # ~20 s teaser: five start lights, then the drop
    python video/music/compose.py pit-window out.wav     # ~42 s walkthrough: film-score style build

Everything sits on one beat grid counted from sample 0, in D minor.
"""
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
rng = np.random.default_rng(7)          # fixed seed: the same file every time


# ── building blocks ───────────────────────────────────────────────────────────

def note_hz(n):
    """MIDI note -> Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.1, s=0.0, r=0.05, hold=None):
    """ADSR envelope, n samples long. hold: seconds at sustain level before release."""
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    hold_n = max(0, n - a_n - d_n - r_n) if hold is None else int(hold * SR)
    e = np.concatenate([np.linspace(0, 1, a_n, endpoint=False), np.linspace(1, s, d_n, endpoint=False),
                        np.full(hold_n, s), np.linspace(s, 0, r_n)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def lowpass(x, hz, order=2):
    return sosfilt(butter(order, min(hz, SR / 2 - 100), 'low', fs=SR, output='sos'), x)


def highpass(x, hz, order=2):
    return sosfilt(butter(order, hz, 'high', fs=SR, output='sos'), x)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (freq * (1 + detune) * t) % 1.0
    return 2 * ph - 1


def sine(freq, n):
    return np.sin(2 * np.pi * freq * np.arange(n) / SR)


def kick(length=0.45, punch=1.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = 42 + 110 * np.exp(-t * 32)                         # pitch drop
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    click = lowpass(rng.standard_normal(n), 3500) * np.exp(-t * 180) * 0.25
    return np.tanh((body + click) * 1.6 * punch) * 0.9


def clap(length=0.35):
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 900, 5000)
    bursts = sum(np.exp(-np.clip(t - k * 0.011, 0, None) * 60) * (t >= k * 0.011) for k in range(3))
    return noise * bursts * np.exp(-t * 14) * 0.5


def hat(length=0.06, open_=False):
    n = int((0.25 if open_ else length) * SR)
    t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.22


def beep(freq, length=0.32):
    """An F1 start-light tone: clean square-ish blip."""
    n = int(length * SR)
    tone = np.tanh(3 * sine(freq, n)) * 0.5 + sine(freq * 2, n) * 0.15
    return tone * env(n, a=0.002, d=0.05, s=0.6, r=0.08)


def riser(length, start=200, end=6000):
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    steps = 24                                              # sweep a band-pass up in steps, crossfaded
    seg = n // steps
    for k in range(steps):
        lo = start * (end / start) ** (k / steps)
        piece = bandpass(noise, lo, min(lo * 2.2, SR / 2 - 200))
        w = np.zeros(n)
        a, b = max(0, (k - 1) * seg), min(n, (k + 2) * seg)
        w[a:b] = np.hanning(b - a)
        out += piece * w
    return out * t ** 2 * 0.35


def impact(length=3.0, root=26):
    """Sub drop plus a noise burst: the hit on a big cut."""
    n = int(length * SR)
    t = np.arange(n) / SR
    f = note_hz(root) * (1 + 1.5 * np.exp(-t * 6))
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    burst = lowpass(rng.standard_normal(n), 2500) * np.exp(-t * 9) * 0.4
    return np.tanh((sub + burst) * 1.4) * 0.8


def braam(freq_note, length=3.5):
    """The film-trailer brass blast: stacked detuned saws, filter opening then closing."""
    n = int(length * SR)
    tone = sum(saw(note_hz(freq_note + iv), n, d) for iv in (0, 12, 7) for d in (-0.004, 0.0, 0.005))
    t = np.arange(n) / SR
    cutoff = 300 + 2200 * np.exp(-t * 1.3) * (1 - np.exp(-t * 30))
    out = np.zeros(n)
    block = 2048                                            # time-varying low-pass in blocks
    for i in range(0, n, block):
        out[i:i + block] = lowpass(tone[max(0, i - 4096):i + block], cutoff[i])[-len(tone[i:i + block]):]
    return np.tanh(out * 0.35) * env(n, a=0.04, d=0.4, s=0.7, r=1.2)


def pad(chord, length, bright=900):
    n = int(length * SR)
    tone = sum(saw(note_hz(m), n, d) for m in chord for d in (-0.006, 0.006))
    return lowpass(tone, bright) * env(n, a=0.6, d=0.4, s=0.8, r=0.8) * 0.07


def reverb(x, seconds=2.2, mix=0.25):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.5 / seconds)
    ir = lowpass(ir, 6000)
    wet = fftconvolve(x, ir)[:len(x)]
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return x * (1 - mix) + wet * mix


class Track:
    def __init__(self, seconds, bpm):
        self.n = int(seconds * SR)
        self.beat = 60 / bpm
        self.bus = {k: np.zeros(self.n) for k in ('drums', 'bass', 'music', 'fx')}
        self.duck = np.ones(self.n)                         # sidechain from the kick

    def at(self, beats):
        return int(round(beats * self.beat * SR))

    def put(self, bus, sound, beats, gain=1.0):
        i = self.at(beats)
        if i >= self.n:
            return
        end = min(self.n, i + len(sound))
        self.bus[bus][i:end] += sound[:end - i] * gain

    def kick(self, beats, gain=1.0):
        self.put('drums', kick(), beats, gain)
        i = self.at(beats)
        d = int(0.22 * SR)
        shape = 1 - 0.75 * np.exp(-np.arange(d) / SR * 14)
        end = min(self.n, i + d)
        self.duck[i:end] = np.minimum(self.duck[i:end], shape[:end - i])

    def bassline(self, start, beats, notes, gain=0.32, cutoff=700):
        """16th-note pulse; notes: one MIDI note per bar (4 beats), repeated."""
        step = 0.25
        n16 = int(step * self.beat * SR)
        k = 0
        while k * step < beats:
            note = notes[int((k * step) // 4) % len(notes)]
            octave = 12 if k % 8 == 6 else 0                # a little lift each half bar
            tone = saw(note_hz(note + octave), n16, 0.003) + saw(note_hz(note + octave), n16, -0.003)
            tone = lowpass(tone, cutoff + 500 * (k % 4 == 0)) * env(n16, a=0.003, d=0.09, s=0.25, r=0.02)
            self.put('bass', tone, start + k * step, gain)
            k += 1

    def arp(self, start, beats, chords, gain=0.08, step=0.5, cutoff=3500):
        n8 = int(step * self.beat * SR)
        k = 0
        while k * step < beats:
            chord = chords[int((k * step) // 4) % len(chords)]
            note = chord[k % len(chord)] + 12
            tone = (saw(note_hz(note), n8, 0.004) + 0.5 * sine(note_hz(note + 12), n8))
            tone = lowpass(tone, cutoff) * env(n8, a=0.004, d=0.18, s=0.0, r=0.02)
            self.put('music', tone, start + k * step, gain)
            k += 1

    def render(self, levels, master_fade_out=1.5):
        mix = (self.bus['drums'] * levels.get('drums', 1)
               + reverb(self.bus['bass'] * self.duck, 1.0, 0.08) * levels.get('bass', 1)
               + reverb(self.bus['music'] * (0.55 + 0.45 * self.duck), 2.6, 0.35) * levels.get('music', 1)
               + reverb(self.bus['fx'], 3.0, 0.3) * levels.get('fx', 1))
        fade = int(master_fade_out * SR)
        mix[-fade:] *= np.linspace(1, 0, fade) ** 2
        mix = np.tanh(mix * 1.3) / np.tanh(1.3)             # gentle glue
        mix /= np.max(np.abs(mix)) + 1e-9
        mix *= 0.89                                          # about -1 dBFS peak
        # wide stereo: a touch of delay on the right for the reverb-heavy parts
        right = np.concatenate([np.zeros(int(0.007 * SR)), mix])[:len(mix)]
        return np.stack([mix, mix * 0.6 + right * 0.4], axis=1)


# D minor: Dm, Bb, F, C (as MIDI roots for the bass, triads for the music)
ROOTS = [38, 34, 41, 36]
CHORDS = [[62, 65, 69], [58, 62, 65], [57, 60, 65], [60, 64, 67]]


def lights_out():
    """~20 s at 120 bpm. Beats 0-4: five start lights; beat 6: lights out, drop;
    beat 34: the logo hit; then the tail."""
    bpm = 120
    tr = Track(20.0, bpm)
    for i in range(5):                                      # five red lights
        tr.put('fx', beep(note_hz(74 if i < 4 else 74)), i, 0.55)
        tr.put('fx', kick(0.25, 0.4), i, 0.25)
    tr.put('fx', riser(1.0, 400, 9000), 5, 0.6)             # the hold before lights out
    tr.put('fx', impact(2.5), 6, 0.9)                       # LIGHTS OUT
    for b in range(6, 34):                                  # the drop: 28 beats
        tr.kick(b)
        if b % 2 == 1:
            tr.put('drums', clap(), b, 0.8)
        tr.put('drums', hat(), b + 0.5, 1.0)
        tr.put('drums', hat(), b + 0.25, 0.35)
        tr.put('drums', hat(), b + 0.75, 0.35)
    tr.bassline(6, 28, ROOTS, 0.34)
    tr.arp(14, 20, CHORDS, 0.07, step=0.25)
    for bar in range(7):
        tr.put('music', pad(CHORDS[bar % 4], 2.0 * tr.beat * 2), 6 + bar * 4, 1.0)
    tr.put('fx', riser(2.0, 300, 8000), 30, 0.55)           # into the logo
    tr.put('fx', impact(4.0), 34, 1.0)                       # logo hit
    tr.put('music', braam(38, 5.0), 34, 0.55)
    tr.put('fx', beep(note_hz(86), 0.5), 34, 0.25)
    return tr.render({'drums': 0.9, 'bass': 1.0, 'music': 1.1, 'fx': 1.0}, master_fade_out=2.0)


def pit_window():
    """~42 s at 110 bpm, film-score style.
    0-16 beats  (0-8.7 s)   ticking clock, pad, pulse fades in
    16-32       (8.7-17.5)  pulse + toms, tension
    32-64       (17.5-34.9) the drive: full beat, bass, arp, braams on bar starts
    64-68       (34.9-37.1) stop, riser
    68-76       (37.1-41.5) final braam + impact, tail"""
    bpm = 110
    tr = Track(42.0, bpm)
    for b in range(0, 64):                                  # the clock: ticking 8ths, getting louder
        tr.put('fx', hat(0.03), b, 0.25 + 0.5 * min(1, b / 32))
        tr.put('fx', hat(0.03), b + 0.5, 0.15 + 0.3 * min(1, b / 32))
    for bar in range(4):
        tr.put('music', pad(CHORDS[bar % 4], 4 * tr.beat, 700), bar * 4, 1.2)
    tr.bassline(8, 24, ROOTS, 0.18, cutoff=400)             # pulse fades in under the pad
    for b in range(16, 32):                                 # toms on 1 and the "and" of 3
        if b % 4 in (0,):
            tr.kick(b, 0.8)
        if b % 4 == 2:
            tr.put('drums', kick(0.5, 0.6), b + 0.5, 0.6)
    tr.put('fx', riser(4 * tr.beat, 200, 7000), 28, 0.5)
    tr.put('fx', impact(3.0), 32, 0.9)
    for b in range(32, 64):                                 # the drive
        tr.kick(b)
        if b % 2 == 1:
            tr.put('drums', clap(), b, 0.7)
        tr.put('drums', hat(), b + 0.5, 0.9)
        tr.put('drums', hat(), b + 0.25, 0.3)
        tr.put('drums', hat(), b + 0.75, 0.3)
    tr.bassline(32, 32, ROOTS, 0.34, cutoff=900)
    tr.arp(40, 24, CHORDS, 0.065, step=0.25)
    for bar in range(8):
        tr.put('music', pad(CHORDS[bar % 4], 4 * tr.beat, 1300), 32 + bar * 4, 1.0)
        if bar % 2 == 0:
            tr.put('music', braam(ROOTS[bar % 4] + 12, 2.5), 32 + bar * 4, 0.28)
    tr.put('fx', riser(4 * tr.beat, 300, 9000), 64, 0.6)     # stop, then rise
    tr.put('fx', impact(4.5), 68, 1.0)
    tr.put('music', braam(38, 5.5), 68, 0.6)
    tr.put('fx', beep(note_hz(86), 0.6), 68, 0.2)
    return tr.render({'drums': 0.85, 'bass': 1.0, 'music': 1.15, 'fx': 0.95}, master_fade_out=3.0)


def write_wav(path, stereo):
    from scipy.io import wavfile
    wavfile.write(path, SR, (np.clip(stereo, -1, 1) * 32767).astype(np.int16))


if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    write_wav(out, {'lights-out': lights_out, 'pit-window': pit_window}[name]())
    print(out)
