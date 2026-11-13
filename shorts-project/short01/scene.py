"""Short 01: 'What if you had infinite strength?'  34 s, 6 shots, original character 'Kip'.
Usage: python scene.py -- <out_dir> <samples> <step> [frame ...]
Renders PNG frames (odd frames when step=2 = animated on twos). Skips frames that exist (resumable)."""
import bpy, sys, os, math, random, time
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
OUT, SAMPLES, STEP = a[0], int(a[1]), int(a[2])
ONLY = [int(x) for x in a[3:]]
os.makedirs(OUT, exist_ok=True)
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
FPS, END = 30, 1020
S.frame_start, S.frame_end, S.render.fps = 1, END, FPS
def F(t): return int(round(t * FPS)) + 1          # seconds -> frame
SH = [1, 157, 277, 469, 631, 799]                 # shot start frames (all odd, so cuts land on rendered frames)
D = math.radians

# ---------------- helpers ----------------
def mat(name, col, rough=0.5, emit=None, strength=6.0, noise=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if noise:
        n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = noise[0]; n.inputs["Detail"].default_value = 6
        r = nt.nodes.new("ShaderNodeValToRGB")
        r.color_ramp.elements[0].color = (*col, 1); r.color_ramp.elements[1].color = (*noise[1], 1)
        r.color_ramp.elements[0].position = 0.35; r.color_ramp.elements[1].position = 0.7
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
        nt.links.new(n.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def key(o, path, val, f):
    setattr(o, path, val); o.keyframe_insert(path, frame=f)

def keys(o, path, pairs):
    for f, v in pairs: key(o, path, v, f)

HIDE, SHOW = (0.001, 0.001, 0.001), (1, 1, 1)
def visible(o, f_on, f_off=None, full=None):
    full = full or tuple(o.scale)
    key(o, "scale", HIDE, 1)
    if f_on > 1: key(o, "scale", HIDE, f_on - 1)
    key(o, "scale", full, f_on)
    if f_off: key(o, "scale", full, f_off - 1); key(o, "scale", HIDE, f_off)

def rock(name, loc, r, sub=4, strength=0.45, m=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=sub, location=loc); o = bpy.context.object; o.name = name
    o.scale = scale
    t = bpy.data.textures.new(name + "t", 'VORONOI'); t.noise_scale = r * 0.9
    d = o.modifiers.new("d", 'DISPLACE'); d.texture = t; d.strength = r * strength
    bpy.ops.object.shade_smooth()
    if m: o.data.materials.append(m)
    return o

def sphere(name, loc, scale, m, parent=None, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc); o = bpy.context.object
    o.name = name; o.scale = scale; bpy.ops.object.shade_smooth(); o.data.materials.append(m)
    if parent:
        bpy.context.view_layer.update(); o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None); S.collection.objects.link(e); e.location = loc
    if parent:
        bpy.context.view_layer.update(); e.parent = parent; e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e

# ---------------- world + set (kit: dusk canyon) ----------------
w = bpy.data.worlds.new("w"); w.use_nodes = True; S.world = w; nt = w.node_tree
tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); cr = nt.nodes.new("ShaderNodeValToRGB")
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -0.15; mr.inputs[2].default_value = 0.9
e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = (1.0, 0.42, 0.16, 1); e[1].position = 1.0; e[1].color = (0.02, 0.03, 0.16, 1)
cr.color_ramp.elements.new(0.28).color = (0.55, 0.16, 0.38, 1)
nt.links.new(tc.outputs["Generated"], sx.inputs[0]); nt.links.new(sx.outputs["Z"], mr.inputs[0])
nt.links.new(mr.outputs[0], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], nt.nodes["Background"].inputs["Color"])
nt.nodes["Background"].inputs["Strength"].default_value = 1.1

ground_m = mat("ground", (0.36, 0.17, 0.10), 0.9, noise=(1.2, (0.52, 0.27, 0.15)))
rock_m = mat("rock", (0.30, 0.14, 0.10), 0.85, noise=(2.5, (0.50, 0.25, 0.16)))
boulder_m = mat("boulder", (0.33, 0.30, 0.30), 0.8, noise=(3.0, (0.55, 0.50, 0.46)))
dark_m = mat("crater", (0.03, 0.015, 0.01), 1.0)
dust_m = mat("dust", (0.40, 0.24, 0.16), 1.0)
bpy.ops.mesh.primitive_plane_add(size=400); bpy.context.object.data.materials.append(ground_m)
for i, (x, y, r, sz) in enumerate([(-9, 16, 5, 2.2), (8, 20, 6, 2.6), (-3, 30, 7, 2.0), (16, 34, 8, 2.4), (-18, 28, 7, 2.8), (3, 44, 9, 2.2), (-14, 14, 4, 2.0)]):
    rock(f"mesa{i}", (x, y, r * sz * 0.22), r, 4, 0.3, rock_m, (1, 1, sz * 0.5))
for i in range(60):
    x, y = random.uniform(-10, 10), random.uniform(-3, 10)
    if abs(y) < 1.7 and -7.5 < x < 6.5: continue
    r = random.uniform(0.08, 0.3); rock(f"st{i}", (x, y, r * 0.5), r, 2, 0.4, rock_m)

# ---------------- effects kit ----------------
def burst(c, n, f0, spread=(0.4, 1.2), up=(1.0, 2.5), size=(0.06, 0.18), life=18):
    for i in range(n):
        ang = random.uniform(0, math.tau); r0 = random.uniform(0.15, 0.5); sz = random.uniform(*size)
        p = Vector((c[0] + math.cos(ang) * r0, c[1] + math.sin(ang) * r0, c[2]))
        o = rock(f"deb{f0}_{i}", p, sz, 1, 0.3, rock_m); visible(o, f0)
        out = Vector((math.cos(ang), math.sin(ang), 0)); dist = random.uniform(*spread); h = random.uniform(*up)
        keys(o, "location", [(f0, p), (f0 + life // 2, p + out * dist * 0.5 + Vector((0, 0, h))), (f0 + life, p + out * dist + Vector((0, 0, sz * 0.4 - c[2])))])
        keys(o, "rotation_euler", [(f0, (0, 0, 0)), (f0 + life, (random.uniform(-6, 6), random.uniform(-6, 6), 0))])

def cracks(c, n, f0, lmin=0.8, lmax=2.0, r0=0.5):
    for i in range(n):
        ang = i / n * math.tau + random.uniform(-0.3, 0.3); L = random.uniform(lmin, lmax)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(c[0] + math.cos(ang) * (r0 + L / 2), c[1] + math.sin(ang) * (r0 + L / 2), 0.006))
        o = bpy.context.object; o.rotation_euler = (0, 0, ang); o.data.materials.append(dark_m)
        keys(o, "scale", [(1, (0.001, 0.05, 0.01)), (f0 - 1, (0.001, 0.05, 0.01)), (f0 + 5, (L, 0.06, 0.01))])

def crater(c, r, f0):
    bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.02, vertices=48, location=(c[0], c[1], 0.012)); o = bpy.context.object
    o.data.materials.append(dark_m); keys(o, "scale", [(1, (0.001, 0.001, 1)), (f0 - 1, (0.001, 0.001, 1)), (f0 + 4, (r, r, 1))])
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.07, location=(c[0], c[1], 0.0)); rim = bpy.context.object
    rim.data.materials.append(ground_m); rim.scale = (r * 1.05, r * 1.05, 0.35); visible(rim, f0)
    keys(rim, "scale", [(f0, (r * 0.6, r * 0.6, 0.2)), (f0 + 4, (r * 1.05, r * 1.05, 0.35))])

def puffs(c, n, f0, rad=0.8, size=0.35, life=40):
    for i in range(n):
        ang = random.uniform(0, math.tau); p = Vector((c[0] + math.cos(ang) * 0.2, c[1] + math.sin(ang) * 0.2, c[2] + 0.15))
        o = sphere(f"puff{f0}_{i}", p, HIDE, dust_m, seg=16); s = size * 0.7 * random.uniform(0.7, 1.3)
        q = p + Vector((math.cos(ang) * rad * random.uniform(0.8, 1.6), math.sin(ang) * rad * random.uniform(0.8, 1.6), random.uniform(0.1, 0.5)))
        keys(o, "location", [(f0, p), (f0 + life, q)])
        keys(o, "scale", [(1, HIDE), (f0 - 1, HIDE), (f0 + 3, (s, s, s * 0.8)), (f0 + life * 2 // 3, (s * 1.2,) * 3), (f0 + life, HIDE)])

# ---------------- character kit: 'Kip' ----------------
skin = mat("skin", (0.95, 0.62, 0.28), 0.55); suit = mat("suit", (0.10, 0.22, 0.62), 0.5)
white = mat("white", (0.95, 0.95, 0.95), 0.25); black = mat("black", (0.01, 0.01, 0.01), 0.15)
core_m = mat("core", (0.2, 0.9, 1.0), 0.3, emit=(0.15, 0.85, 1.0), strength=12); scarf = mat("scarf", (0.85, 0.10, 0.12), 0.6)
root = empty("kip", (0, 0, 0))
body = empty("body", (0, 0, 0.55), root)
sphere("torso", (0, 0, 0.78), (0.33, 0.30, 0.40), suit, body)
core = sphere("core", (0.27, 0, 0.84), (0.09, 0.11, 0.11), core_m, body)
sphere("scarf", (0, 0, 1.14), (0.27, 0.27, 0.10), scarf, body)
tail = sphere("scarftail", (-0.34, 0.05, 1.05), (0.26, 0.05, 0.09), scarf, body); tail.rotation_euler = (0, 0.5, 0)
head = empty("head", (0, 0, 1.2), body)
sphere("skull", (0, 0, 1.52), (0.36, 0.34, 0.33), skin, head)
eyes, hips = [], []
for s in (1, -1):
    ew = sphere("eye", (0.27, 0.14 * s, 1.56), (0.09, 0.10, 0.12), white, head); eyes.append(ew)
    sphere("pupil", (0.335, 0.14 * s, 1.56), (0.04, 0.05, 0.065), black, ew)
    hp = empty("hip", (0, 0.16 * s, 0.52), body); hips.append(hp)
    sphere("leg", (0, 0.16 * s, 0.32), (0.10, 0.10, 0.22), suit, hp)
    sphere("foot", (0.06, 0.16 * s, 0.09), (0.19, 0.12, 0.09), suit, hp)
hipB, hipF = hips                                   # hipF is camera side (y<0)
shF = empty("shF", (0.05, -0.33, 1.0), body)
sphere("armF", (0.05, -0.36, 0.76), (0.085, 0.085, 0.26), suit, shF)
sphere("handF", (0.05, -0.36, 0.47), (0.12, 0.11, 0.12), skin, shF)
shB = empty("shB", (0.05, 0.33, 1.0), body)
sphere("armB", (0.05, 0.36, 0.76), (0.085, 0.085, 0.26), suit, shB)
sphere("handB", (0.05, 0.36, 0.47), (0.12, 0.11, 0.12), skin, shB)
# held boulder rides the arm: centre sits 1.55 m out along the arm, so arm-forward = resting on the ground in front
BR = 0.9
held = rock("heldBoulder", (0.05, -0.36, 1.0 - 1.55), BR, 5, 0.22, boulder_m)
bpy.context.view_layer.update(); held.parent = shF; held.matrix_parent_inverse = shF.matrix_world.inverted()
pebble = rock("pebble", (0.05, -0.36, 1.0 - 0.70), 0.08, 2, 0.35, boulder_m)
bpy.context.view_layer.update(); pebble.parent = shF; pebble.matrix_parent_inverse = shF.matrix_world.inverted()

def arm(sh, deg, f): key(sh, "rotation_euler", (0, D(deg), 0), f)   # 0 = down, -90 = forward, -180 = straight up
def look(pitch, yaw, f): key(head, "rotation_euler", (0, D(pitch), D(yaw)), f)
def eyes_scale(k, f):
    for ew in eyes: key(ew, "scale", (0.09 * k[0], 0.10 * k[0], 0.12 * k[1]), f)
def cut(o, path, old, new, f):                      # instant change at frame f (made CONSTANT below)
    key(o, path, old, f - 1); key(o, path, new, f)

# ======================= SHOT 1 (f1-156): hook + rules =======================
ground_b = rock("groundBoulder", (1.6, -0.36, 1.0), BR, 5, 0.22, boulder_m); visible(ground_b, 1, SH[1])
keys(body, "location", [(1, (0, 0, 0.55)), (16, (0, 0, 0.58)), (31, (0, 0, 0.55)), (46, (0, 0, 0.58)), (61, (0, 0, 0.55))])
arm(shF, 0, 1); arm(shB, 0, 1); look(0, 0, 1)
# 'never tire': core flares, Kip puffs up
keys(core, "scale", [(1, (0.09, 0.11, 0.11)), (76, (0.09, 0.11, 0.11)), (84, (0.13, 0.16, 0.16)), (100, (0.11, 0.13, 0.13))])
keys(body, "scale", [(70, (1, 1, 1)), (80, (1.06, 1.06, 1.08)), (96, (1.0, 1.0, 1.0))])
keys(body, "location", [(76, (0, 0, 0.55)), (82, (0, 0, 0.62)), (96, (0, 0, 0.56))])
look(0, 0, 100); look(-8, -55, 116); look(-8, -55, 150)                     # glances to camera on 'can't break'
eyes_scale((1, 1), 126); eyes_scale((1, 0.2), 129); eyes_scale((1, 1), 132)
visible(held, SH[1])

# ======================= SHOT 2 (f157-276): one-finger lift =======================
cut(shF, "rotation_euler", (0, 0, 0), (0, D(-90), 0), SH[1])
cut(head, "rotation_euler", (0, D(-8), D(-55)), (0, D(10), 0), SH[1])
keys(body, "location", [(SH[1], (0, 0, 0.56)), (192, (0, 0, 0.50)), (200, (0, 0, 0.47)), (214, (0, 0, 0.57)), (236, (0, 0, 0.55))])
arm(shF, -90, 200); arm(shF, -184, 232); arm(shF, -180, 240)
look(10, 0, 200); look(-30, 0, 228); look(-10, -50, 262)                    # watches it rise, then deadpan to camera
arm(shB, 0, 200); arm(shB, 20, 222); arm(shB, 0, 240)
eyes_scale((1, 1), 250); eyes_scale((1, 0.2), 253); eyes_scale((1, 1), 256)

# ======================= SHOT 3 (f277-468): walk, foot punches through =======================
X3 = -5.4
cut(root, "location", (0, 0, 0), (X3, 0, 0), SH[2])
cut(head, "rotation_euler", (0, D(-10), D(-50)), (0, 0, 0), SH[2])
step = 15
for i, f in enumerate(range(SH[2] + 9, 376, step)):
    key(root, "location", (X3 + 0.21 * i, 0, 0), f)
    key(body, "location", (0, 0, 0.55), f); key(body, "location", (0, 0, 0.60), f + step // 2)
    s = 1 if i % 2 else -1
    key(hipF, "rotation_euler", (0, D(22 * s), 0), f); key(hipB, "rotation_euler", (0, D(-22 * s), 0), f)
XI = X3 + 0.21 * 6 + 0.25                           # impact point, front foot
keys(root, "location", [(376, (X3 + 1.26, 0, 0)), (381, (X3 + 1.36, 0, -0.42)), (386, (X3 + 1.36, 0, -0.36))])
keys(root, "rotation_euler", [(376, (0, 0, 0)), (381, (0, D(9), 0)), (390, (0, D(6), 0))])
keys(hipF, "rotation_euler", [(376, (0, D(-25), 0)), (381, (0, D(-8), 0))]); keys(hipB, "rotation_euler", [(376, (0, D(20), 0)), (381, (0, D(35), 0))])
crater((XI, -0.16, 0), 0.45, 381); cracks((XI, -0.16), 6, 381, 0.6, 1.4, 0.35); burst((XI, -0.16, 0.1), 14, 381, (0.4, 1.0), (0.6, 1.6)); puffs((XI, -0.16, 0), 5, 381, 0.6, 0.28)
look(0, 0, 382); look(28, 0, 396); look(28, 0, 420); look(-6, -55, 440)        # looks down at the hole, then at camera
eyes_scale((1, 1), 381); eyes_scale((1.2, 1.35), 386); eyes_scale((1.2, 1.35), 430); eyes_scale((1, 1), 440)

# ======================= SHOT 4 (f469-630): throw, Newton slides him back =======================
X4 = 4.0
cut(root, "location", (X3 + 1.36, 0, -0.36), (X4, 0, 0), SH[3])
cut(root, "rotation_euler", (0, D(6), 0), (0, 0, 0), SH[3])
cut(hipF, "rotation_euler", (0, D(-8), 0), (0, D(-12), 0), SH[3]); cut(hipB, "rotation_euler", (0, D(35), 0), (0, D(12), 0), SH[3])
cut(head, "rotation_euler", (0, D(-6), D(-55)), (0, 0, 0), SH[3])
REL = 519
arm(shF, -180, 490); arm(shF, -208, 512); arm(shF, -120, REL); arm(shF, -60, 526); arm(shF, -40, 560)
keys(body, "rotation_euler", [(490, (0, 0, 0)), (512, (0, D(-14), 0)), (REL, (0, D(12), 0)), (540, (0, D(-10), 0)), (575, (0, 0, 0))])
keys(body, "location", [(490, (0, 0, 0.55)), (512, (0, 0, 0.48)), (REL, (0, 0, 0.52))])
keys(root, "location", [(REL, (X4, 0, 0)), (523, (X4 - 0.6, 0, 0)), (545, (X4 - 2.2, 0, 0)), (566, (X4 - 2.6, 0, 0))])
look(0, 0, REL); look(-22, 0, 532); look(-22, 0, 575); look(-8, -55, 600)
eyes_scale((1, 1), REL); eyes_scale((1.2, 1.35), 523); eyes_scale((1.2, 1.35), 590); eyes_scale((1, 0.2), 600); eyes_scale((1, 1), 603)
key(held, "scale", (1, 1, 1), REL - 1); key(held, "scale", HIDE, REL)
bpy.context.view_layer.update(); S.frame_set(REL - 1); p0 = held.matrix_world.translation.copy()
fly = rock("flyBoulder", p0, BR, 5, 0.22, boulder_m); visible(fly, REL)
keys(fly, "location", [(REL, p0), (REL + 6, p0 + Vector((0.8, 0.8, 2.0))), (REL + 16, p0 + Vector((2, 3, 6))), (REL + 30, p0 + Vector((5, 10, 16))), (REL + 50, p0 + Vector((20, 40, 70)))])
keys(fly, "rotation_euler", [(REL, (0, 0, 0)), (REL + 40, (0, 8, 3))])
for k in range(5):                                   # twin trench grooves + dust as he skids back
    f = REL + 4 + k * 8; x = X4 - 0.6 - k * 0.45
    puffs((x, 0, 0), 2, f, 0.5, 0.25, 30)
for yy in (-0.16, 0.16):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(X4, yy, 0.006)); g = bpy.context.object; g.data.materials.append(dark_m)
    g.scale = (0.001, 0.12, 0.01); keys(g, "scale", [(1, (0.001, 0.12, 0.01)), (REL, (0.001, 0.12, 0.01)), (545, (4.4, 0.12, 0.01)), (566, (5.2, 0.12, 0.01))])
    keys(g, "location", [(REL, (X4 + 0.1, yy, 0.006)), (545, (X4 - 2.2 + 2.3, yy, 0.006)), (566, (X4 - 2.6 + 2.6, yy, 0.006))])
burst((X4 + 0.6, -0.3, 1.2), 6, REL, (0.5, 1.2), (0.4, 1.0), (0.04, 0.09), 14)

# ======================= SHOT 5 (f631-798): jump, gone, landing =======================
cut(root, "location", (X4 - 2.6, 0, 0), (0, 0, 0), SH[4])
cut(shF, "rotation_euler", (0, D(-40), 0), (0, 0, 0), SH[4]); cut(body, "rotation_euler", (0, 0, 0), (0, 0, 0), SH[4])
cut(head, "rotation_euler", (0, D(-8), D(-55)), (0, D(-15), 0), SH[4])
cut(hipF, "rotation_euler", (0, D(-12), 0), (0, 0, 0), SH[4]); cut(hipB, "rotation_euler", (0, D(12), 0), (0, 0, 0), SH[4])
LA = 657
keys(body, "location", [(SH[4], (0, 0, 0.55)), (640, (0, 0, 0.55)), (654, (0, 0, 0.36)), (LA, (0, 0, 0.62))])
arm(shF, 0, 640); arm(shF, 40, 654); arm(shF, -175, LA + 2)
key(shB, "rotation_euler", (0, 0, 0), 640); key(shB, "rotation_euler", (0, D(40), 0), 654); key(shB, "rotation_euler", (0, D(-175), 0), LA + 2)
look(-15, 0, 640); look(-35, 0, 654)
keys(root, "location", [(LA, (0, 0, 0)), (LA + 4, (0, 0, 3.5)), (LA + 12, (0, 0, 30))])
burst((0, 0, 0.05), 16, LA, (0.5, 1.4), (0.6, 2.0)); puffs((0, 0, 0), 7, LA, 1.0, 0.35, 40); cracks((0, 0), 5, LA, 0.4, 0.9, 0.3)
LD = 760                                            # landing on 'the ground DOESN'T'
keys(root, "location", [(LA + 12, (0, 0, 30)), (LD - 8, (0, 0, 30)), (LD - 4, (0, 0, 9)), (LD, (0, 0, -0.5)), (LD + 4, (0, 0, -0.4))])
look(-35, 0, LD - 8); look(20, 0, LD); look(0, 0, LD + 12)
arm(shF, -175, LD - 1); arm(shF, -60, LD + 2); arm(shF, 0, LD + 14)
key(shB, "rotation_euler", (0, D(-175), 0), LD - 1); key(shB, "rotation_euler", (0, D(-60), 0), LD + 2); key(shB, "rotation_euler", (0, 0, 0), LD + 14)
crater((0, 0, 0), 1.25, LD); cracks((0, 0), 9, LD, 1.4, 3.0, 1.1); burst((0, 0, 0.1), 26, LD, (0.8, 2.4), (1.2, 3.2), (0.07, 0.22), 22); puffs((0, 0, 0), 10, LD, 1.6, 0.45, 50)
eyes_scale((1, 1), LD - 1); eyes_scale((1.2, 0.25), LD + 1); eyes_scale((1.2, 1.3), LD + 8)

# ======================= SHOT 6 (f799-1020): the pebble =======================
cut(head, "rotation_euler", (0, 0, 0), (0, D(8), D(-20)), SH[5])
visible(pebble, SH[5], None, (1, 1, 1)); key(held, "scale", HIDE, SH[5])
arm(shF, 0, SH[5]); arm(shF, 0, 818); arm(shF, -128, 846); arm(shF, -126, 900)
look(8, -20, 820); look(-10, 0, 846); look(-10, 0, 902)
eyes_scale((1.2, 1.3), SH[5]); eyes_scale((1, 1), 830)
CR = 905                                            # pebble crumbles right before 'is how to be gentle'
bpy.context.view_layer.update(); S.frame_set(CR - 1); pp = pebble.matrix_world.translation.copy()
key(pebble, "scale", (1, 1, 1), CR - 1); key(pebble, "scale", HIDE, CR + 1)
grain_m = mat("grain", (0.55, 0.50, 0.46), 0.9)
for i in range(28):
    g = sphere(f"grain{i}", pp, HIDE, grain_m, seg=8); s = random.uniform(0.008, 0.02)
    v = Vector((random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), random.uniform(0, 0.05)))
    keys(g, "scale", [(1, HIDE), (CR - 1, HIDE), (CR, (s, s, s))])
    keys(g, "location", [(CR, pp), (CR + 8, pp + v * 1.5 + Vector((0, 0, -0.05))), (CR + 24, Vector((pp.x + v.x * 3, pp.y + v.y * 3, -0.48)))])
puffs((pp.x, pp.y, pp.z - 0.15), 3, CR, 0.12, 0.05, 30)
eyes_scale((1, 1), CR); eyes_scale((1.25, 1.4), CR + 4); eyes_scale((1.25, 1.4), 950); eyes_scale((1.15, 0.6), 962)
look(-10, 0, CR + 2); look(14, 0, 925); look(14, -45, 960); look(14, -45, END)
arm(shF, -126, 930); arm(shF, -105, 960)

# ---------------- lights follow Kip ----------------
lr = empty("lightrig", (0, 0, 0)); c = lr.constraints.new('COPY_LOCATION'); c.target = root; c.use_y = c.use_z = False
bpy.ops.object.light_add(type='SUN', rotation=(D(68), 0, D(125))); sun = bpy.context.object
sun.data.energy = 4.5; sun.data.color = (1.0, 0.72, 0.5); sun.data.angle = D(3)
bpy.ops.object.light_add(type='AREA', location=(-3, -6, 4)); fill = bpy.context.object; fill.data.energy = 500; fill.data.size = 6; fill.data.color = (0.55, 0.65, 1.0)
bpy.ops.object.light_add(type='AREA', location=(-2.5, 4, 3.5)); rim = bpy.context.object; rim.data.energy = 1400; rim.data.size = 2; rim.data.color = (0.3, 0.8, 1.0)
for l in (fill, rim):
    l.parent = lr; c = l.constraints.new('TRACK_TO'); c.target = root

# ---------------- cameras (one per shot) ----------------
def camera(name, loc, lens, aim, fstop=2.8, focus=None):
    t = empty(name + "_aim", aim)
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object; cam.name = name; cam.data.lens = lens
    cc = cam.constraints.new('TRACK_TO'); cc.target = t
    cam.data.dof.use_dof = True; cam.data.dof.focus_object = focus or root; cam.data.dof.aperture_fstop = fstop
    return cam, t
def shake(cam, f0, amp, n=8):
    base = cam.location.copy()
    for i in range(n):
        d = amp * (1 - i / n)
        key(cam, "location", base + Vector((random.uniform(-d, d), 0, random.uniform(-d, d))), f0 + i)
    key(cam, "location", base, f0 + n)

c1, a1 = camera("cam1", (1.0, -11.5, 1.3), 42, (1.0, 0, 2.3))
keys(c1, "location", [(1, (1.0, -11.5, 1.3)), (156, (1.0, -8.6, 1.3))])
c2, a2 = camera("cam2", (4.2, -4.6, 0.35), 24, (1.0, 0, 1.9), 4.0)
keys(c2, "location", [(SH[1], (4.2, -4.6, 0.35)), (276, (3.8, -4.1, 0.30))])
keys(a2, "location", [(200, (1.0, 0, 1.6)), (236, (0.6, 0, 2.4))])
c3, a3 = camera("cam3", (X3 + 0.4, -7.6, 1.1), 35, (X3 + 0.4, 0, 1.9))
keys(c3, "location", [(SH[2], (X3 + 0.4, -7.6, 1.1)), (376, (X3 + 1.7, -7.6, 1.1)), (468, (X3 + 1.9, -6.8, 0.9))])
keys(a3, "location", [(SH[2], (X3 + 0.4, 0, 1.9)), (376, (X3 + 1.7, 0, 1.9)), (400, (X3 + 1.7, 0, 1.5)), (468, (X3 + 1.7, 0, 1.5))])
c4, a4 = camera("cam4", (3.4, -8.6, 1.3), 30, (3.6, 0, 2.6))
keys(c4, "location", [(SH[3], (3.4, -8.6, 1.3)), (630, (3.0, -8.0, 1.2))])
c5, a5 = camera("cam5", (0.6, -8.5, 0.9), 32, (0, 0, 1.6))
keys(a5, "location", [(SH[4], (0, 0, 1.6)), (LA, (0, 0, 1.6)), (LA + 10, (0, 0, 3.6)), (700, (0, 0, 3.6)), (LD - 6, (0, 0, 1.4))])
c6, a6 = camera("cam6", (3.0, -3.6, 1.2), 50, (0.3, -0.1, 0.85), 2.0)
keys(c6, "location", [(SH[5], (3.0, -3.6, 1.2)), (END, (2.3, -2.8, 1.1))])
shake(c3, 381, 0.08); shake(c4, REL, 0.06); shake(c5, LA, 0.08); shake(c5, LD, 0.22, 12)
for f, cam in zip(SH, (c1, c2, c3, c4, c5, c6)):
    S.timeline_markers.new(f"s{f}", frame=f).camera = cam
S.camera = c1

# instant changes: any key followed by another within 1 frame holds (CONSTANT) so motion blur never smears a cut
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        ad = o.animation_data.action
        curves = ad.fcurves if hasattr(ad, "fcurves") else [fc for l in ad.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
        for fc in curves:
            kp = fc.keyframe_points
            for i in range(len(kp) - 1):
                if kp[i + 1].co.x - kp[i].co.x <= 1.01: kp[i].interpolation = 'CONSTANT'

# ---------------- render ----------------
r = S.render
r.engine = 'CYCLES'; r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, 100
r.image_settings.file_format = 'PNG'; r.image_settings.compression = 15
r.use_motion_blur = True; r.motion_blur_shutter = 0.5; r.use_persistent_data = True
cy = S.cycles; cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = False; cy.use_denoising = True
cy.max_bounces = 3; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.caustics_reflective = False; cy.caustics_refractive = False
S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "..", "short01.blend"))
frames = ONLY or list(range(1, END + 1, STEP))
for f in frames:
    p = os.path.join(OUT, f"f{f:04d}.png")
    if os.path.exists(p): continue
    S.frame_set(f); r.filepath = p; t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time() - t:.1f}s", flush=True)
