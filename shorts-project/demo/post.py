"""CPU post for the demo: captions (PIL) + voice/music/SFX mix (numpy) + ffmpeg encode.
Usage: python post.py <frames_dir> <tts_dir> <font.ttf> <out.mp4> [voice]"""
import sys, os, subprocess, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
FR, TTS, FONT, OUT = sys.argv[1:5]
VOICE = sys.argv[5] if len(sys.argv) > 5 else "am_michael"
FPS, N, W, H, SR = 30, 300, 1080, 1920, 48000
YEL, WHITE = (255, 214, 10), (255, 255, 255)
LINE_START = [0.20, 2.55, 5.20, 7.90]                      # seconds, placed against picture beats (flick f90, drop f205)
CHUNKS = [[("WHAT IF YOU HAD", None), ("INFINITE STRENGTH?", "INFINITE")],
          [("ONE FLICK,", "FLICK,"), ("AND A BOULDER", None), ("LEAVES THE PLANET.", "PLANET.")],
          [("BUT THE GROUND", "GROUND"), ("CAN'T PUSH BACK", None), ("THAT HARD.", None)],
          [("SO YOU SINK.", "SINK.")]]

# ---- audio ----
def load(i):
    s, sr = sf.read(os.path.join(TTS, f"{VOICE}_{i}.wav")); assert sr == 24000
    return np.repeat(s, 2)                                  # 24k -> 48k
t = np.arange(N * SR // FPS) / SR
voice = np.zeros_like(t); durs = []
for i, st in enumerate(LINE_START):
    s = load(i); a = int(st * SR); voice[a:a + len(s)] += s[:len(voice) - a]; durs.append(len(s) / SR)
rng = np.random.default_rng(3)
def lp(x, k):                                               # crude one-pole low-pass via cumulative moving average
    c = np.cumsum(np.insert(x, 0, 0)); y = (c[k:] - c[:-k]) / k; return np.pad(y, (0, len(x) - len(y)))
def env(t0, att, dec): return np.where(t < t0, 0, np.minimum((t - t0) / att, 1) * np.exp(-np.maximum(t - t0 - att, 0) / dec))
pad = sum(np.sin(2 * np.pi * f * t + p) * a for f, a, p in ((73.42, .5, 0), (110.0, .35, 1), (146.83, .25, 2), (220.0, .1, 3), (293.66, .07, 4)))
pad *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.25 * t)
pulse = np.sin(2 * np.pi * 55 * t) * np.exp(-((t * 100 / 60) % 1) * 9) * 0.6          # 100 BPM heartbeat
music = (pad * 0.5 + pulse) * np.minimum(t / 0.3, 1) * np.minimum((10 - t) / 0.4, 1)
riser = lp(rng.standard_normal(len(t)), 40) * np.clip((t - 1.9) / 1.1, 0, 1) ** 3 * (t < 3.0) * 1.6
def boom(t0, f0, g): return np.sin(2 * np.pi * (35 * (t - t0) + (f0 - 35) * 0.12 * (1 - np.exp(-(t - t0) / 0.12)))) * env(t0, 0.004, 0.35) * g
whoosh = lp(rng.standard_normal(len(t)), 12) * env(3.0, 0.05, 0.45) * 0.9
crack = rng.standard_normal(len(t)) * env(6.85, 0.002, 0.06) * 0.5 + lp(rng.standard_normal(len(t)), 90) * env(6.87, 0.02, 0.5) * 3.0
duck = 1 - 0.55 * np.clip(lp(np.abs(voice), 2400) * 12, 0, 1)                         # music ducks under voice
mix = voice * 0.95 + music * 0.16 * duck + riser * 0.25 + boom(3.0, 120, 0.8) + whoosh * 0.3 + crack * 0.35 + boom(6.87, 90, 0.7)
mix = np.tanh(mix * 1.1) * 0.89
sf.write(OUT + ".wav", mix, SR)

# ---- captions: each chunk shown while it is spoken; time split by character count ----
cues = []
for li, chunks in enumerate(CHUNKS):
    tot = sum(len(c[0]) for c in chunks); st = LINE_START[li]
    for c, emph in chunks:
        d = durs[li] * len(c) / tot; cues.append([st, st + d, c, emph]); st += d
cues[0][0] = 0.0                                             # hook caption is on screen at frame 0
for a, b in zip(cues, cues[1:]): a[1] = min(b[0], a[1] + 0.35)   # hold through short gaps
cues[-1][1] = 9.7
font_cache = {}
def font(sz):
    if sz not in font_cache: font_cache[sz] = ImageFont.truetype(FONT, sz)
    return font_cache[sz]
def draw_caption(img, text, emph, k):
    """k = frames since cue start. Pop-in: 82% -> 106% -> 100% over 5 frames."""
    scale = (0.82, 0.95, 1.06, 1.03, 1.0)[min(k, 4)]
    f = font(int(124 * scale)); d = ImageDraw.Draw(img); words = text.split()
    sp = d.textlength(" ", font=f); ws = [d.textlength(w, font=f) for w in words]
    x = (W - (sum(ws) + sp * (len(words) - 1))) / 2; y = 560
    for w, wl in zip(words, ws):
        d.text((x, y), w, font=f, fill=YEL if w == emph else WHITE, stroke_width=int(11 * scale), stroke_fill=(0, 0, 0), anchor="ls")
        x += wl + sp
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", OUT + ".wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
last = None
for n in range(N):                                          # n = 0-based output frame; renders are on twos (odd frame numbers)
    src = n + 1 if (n + 1) % 2 == 1 else n
    p = os.path.join(FR, f"f{src:04d}.png")
    if os.path.exists(p): last = p
    img = Image.open(last).convert("RGB")
    ts = n / FPS
    for a, b, text, emph in cues:
        if a <= ts < b: draw_caption(img, text, emph, n - int(round(a * FPS)))
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
print("cues", [(round(a, 2), round(b, 2), c) for a, b, c, _ in cues])
