"""CPU post: captions (PIL) + voice/music/SFX mix (numpy) + ffmpeg encode, driven by timeline.json.
Usage: python post.py <timeline.json> <frames_dir> <vo_dir> <font.ttf> <out.mp4>"""
import sys, os, json, subprocess, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
TL, FR, VO, FONT, OUT = sys.argv[1:6]
T = json.load(open(TL))
FPS, N, W, H, SR = T["fps"], T["frames"], 1080, 1920, 48000
YEL, WHITE, MAXW = (255, 214, 10), (255, 255, 255), 960
dur = N / FPS
t = np.arange(int(dur * SR)) / SR
rng = np.random.default_rng(5)

# ---------- voice ----------
voice = np.zeros_like(t); durs = []
for i, L in enumerate(T["lines"]):
    s, sr = sf.read(os.path.join(VO, f"l{i}.wav")); assert sr == 24000
    s = np.repeat(s, 2); a = int(L["t"] * SR); n = min(len(s), len(t) - a)
    voice[a:a + n] += s[:n]; durs.append(len(s) / SR)

# ---------- sound design (all synthesized here; no third-party audio) ----------
def lp(x, k):
    c = np.cumsum(np.insert(x, 0, 0)); y = (c[k:] - c[:-k]) / k; return np.pad(y, (0, len(x) - len(y)))
def env(t0, att, dec): return np.where(t < t0, 0, np.minimum((t - t0) / att, 1) * np.exp(-np.maximum(t - t0 - att, 0) / dec))
def win(a, b): return ((t >= a) & (t < b)).astype(float)
def boom(t0, f0, g, dec=0.35):
    tt = np.maximum(t - t0, 0)
    return np.sin(2 * np.pi * (35 * tt + (f0 - 35) * 0.12 * (1 - np.exp(-tt / 0.12)))) * env(t0, 0.004, dec) * g
noise = rng.standard_normal(len(t))
sfx = np.zeros_like(t); X = T["sfx"]
for a in X["hum"]: sfx += np.sin(2 * np.pi * 220 * t) * np.sin(2 * np.pi * 3 * t) ** 2 * env(a, 0.3, 0.8) * 0.25
for a, b in X["rumble"]: sfx += lp(noise, 300) * win(a, b) * np.minimum((t - a) / 0.4, 1) * 6
for a in X["step"]: sfx += boom(a, 80, 0.35, 0.08)
for a in X["impact_small"]: sfx += boom(a, 110, 0.9) + noise * env(a, 0.002, 0.05) * 0.4 + lp(noise, 80) * env(a + 0.02, 0.02, 0.4) * 3
for a in X["impact_mid"]: sfx += boom(a, 120, 0.8) + lp(noise, 12) * env(a, 0.05, 0.45) * 0.35
for a, b in X["grind"]: sfx += lp(noise, 25) * win(a, b) * np.exp(-(t - a) / 0.9) * 1.4
for a in X["launch"]: sfx += boom(a, 140, 1.0, 0.5) + lp(noise, 10) * env(a, 0.03, 0.6) * 0.4
for a, b in X["fall"]:
    tt = np.clip((t - a) / (b - a), 0, 1); sfx += np.sin(2 * np.pi * np.cumsum(1400 - 900 * tt) / SR) * win(a, b) * tt * 0.18
for a in X["impact_big"]: sfx += boom(a, 100, 1.2, 0.8) + noise * env(a, 0.002, 0.08) * 0.6 + lp(noise, 120) * env(a + 0.03, 0.03, 0.9) * 5
for a in X["crumble"]:
    grains = (rng.random(len(t)) < 0.004) * rng.standard_normal(len(t))
    sfx += lp(grains, 3) * win(a, a + 0.6) * np.exp(-(t - a) / 0.25) * 3

# ---------- music: D minor pad + 100 BPM pulse; pulse drops out for the twist ----------
pad = sum(np.sin(2 * np.pi * f * t + p) * g for f, g, p in ((73.42, .5, 0), (110.0, .35, 1), (146.83, .25, 2), (174.61, .12, 5), (220.0, .1, 3)))
pad *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.25 * t)
drop = T["music_drop"]
pulse = np.sin(2 * np.pi * 55 * t) * np.exp(-((t * 100 / 60) % 1) * 9) * 0.6 * (t < drop)
bell = np.sin(2 * np.pi * 587.33 * t) * env(30.6, 0.01, 1.5) * 0.12 + np.sin(2 * np.pi * 880 * t) * env(31.4, 0.01, 1.8) * 0.08
fa, fb = T["end_fade"]
music = (pad * (0.5 - 0.25 * (t >= drop)) + pulse + bell) * np.minimum(t / 0.3, 1) * np.clip((fb - t) / (fb - fa), 0, 1)
duck = 1 - 0.55 * np.clip(lp(np.abs(voice), 2400) * 12, 0, 1)
mix = voice * 0.95 + music * 0.17 * duck + sfx * 0.32
mix = np.tanh(mix * 1.1) * 0.89
sf.write(OUT + ".wav", mix, SR)

# ---------- captions: chunk time split by character count within each spoken line ----------
cues = []
for i, L in enumerate(T["lines"]):
    tot = sum(len(c[0]) for c in L["chunks"]); st = L["t"]
    for c, emph in L["chunks"]:
        d = durs[i] * len(c) / tot; cues.append([st, st + d, c, emph]); st += d
cues[0][0] = 0.0
for a, b in zip(cues, cues[1:]): a[1] = min(b[0], a[1] + 0.35)
cues[-1][1] = fa + 0.6
fc = {}
def font(sz):
    if sz not in fc: fc[sz] = ImageFont.truetype(FONT, sz)
    return fc[sz]
def draw_caption(img, text, emph, k):
    pop = (0.82, 0.95, 1.06, 1.03, 1.0)[min(k, 4)]
    d = ImageDraw.Draw(img); words = text.split()
    base = 124
    while True:                                   # shrink long lines to fit 960 px (60 px side margins)
        f = font(base); sp = d.textlength(" ", font=f); wl = sum(d.textlength(w, font=f) for w in words) + sp * (len(words) - 1)
        if wl <= MAXW or base <= 70: break
        base -= 4
    sz = int(base * pop); f = font(sz); sp = d.textlength(" ", font=f); ws = [d.textlength(w, font=f) for w in words]
    x = (W - (sum(ws) + sp * (len(words) - 1))) / 2; y = 560
    for w, wl in zip(words, ws):
        d.text((x, y), w, font=f, fill=YEL if w == emph else WHITE, stroke_width=max(6, int(sz * 0.09)), stroke_fill=(0, 0, 0), anchor="ls")
        x += wl + sp
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", OUT + ".wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
last = None
for n in range(N):                                # renders exist on odd frame numbers (animated on twos)
    src = n + 1 if (n + 1) % 2 == 1 else n
    p = os.path.join(FR, f"f{src:04d}.png")
    if os.path.exists(p): last = p
    img = Image.open(last).convert("RGB"); ts = n / FPS
    for a, b, text, emph in cues:
        if a <= ts < b: draw_caption(img, text, emph, n - int(round(a * FPS)))
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
os.remove(OUT + ".wav")
json.dump([[round(a, 2), round(b, 2), c] for a, b, c, _ in cues], open(OUT + ".cues.json", "w"), indent=0)
