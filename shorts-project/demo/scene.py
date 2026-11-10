"""10 s demo: 'What if you had infinite strength?'  Original character, set and script.
Usage: python scene.py -- <out_dir> <samples> <step> [frame ...]
Renders a PNG frame sequence, skipping frames that already exist (resumable)."""
import bpy, sys, os, math, random, time
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
OUT, SAMPLES, STEP = a[0], int(a[1]), int(a[2])
ONLY = [int(x) for x in a[3:]]
os.makedirs(OUT, exist_ok=True)
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.frame_start, S.frame_end = 1, 300
S.render.fps = 30

def mat(name, col, rough=0.5, emit=None, strength=6.0, noise=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if noise:  # two-tone procedural variation
        n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = noise[0]; n.inputs["Detail"].default_value = 6
        r = nt.nodes.new("ShaderNodeValToRGB")
        r.color_ramp.elements[0].color = (*col, 1); r.color_ramp.elements[1].color = (*noise[1], 1)
        r.color_ramp.elements[0].position = 0.35; r.color_ramp.elements[1].position = 0.7
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
        nt.links.new(n.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def key(o, path, val, f, interp='BEZIER'):
    setattr(o, path, val); o.keyframe_insert(path, frame=f)

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
        o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None); S.collection.objects.link(e); e.location = loc
    if parent:
        bpy.context.view_layer.update(); e.parent = parent; e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e

# ---------- world: dusk gradient ----------
w = bpy.data.worlds.new("w"); w.use_nodes = True; S.world = w; nt = w.node_tree
tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); cr = nt.nodes.new("ShaderNodeValToRGB")
mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -0.15; mr.inputs[2].default_value = 0.9
e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = (1.0, 0.42, 0.16, 1); e[1].position = 1.0; e[1].color = (0.02, 0.03, 0.16, 1)
m_ = cr.color_ramp.elements.new(0.28); m_.color = (0.55, 0.16, 0.38, 1)
nt.links.new(tc.outputs["Generated"], sx.inputs[0]); nt.links.new(sx.outputs["Z"], mr.inputs[0])
nt.links.new(mr.outputs[0], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], nt.nodes["Background"].inputs["Color"])
nt.nodes["Background"].inputs["Strength"].default_value = 1.1

# ---------- set: canyon floor, mesas, scattered stones ----------
ground_m = mat("ground", (0.36, 0.17, 0.10), 0.9, noise=(1.2, (0.52, 0.27, 0.15)))
rock_m = mat("rock", (0.30, 0.14, 0.10), 0.85, noise=(2.5, (0.50, 0.25, 0.16)))
boulder_m = mat("boulder", (0.33, 0.30, 0.30), 0.8, noise=(3.0, (0.55, 0.50, 0.46)))
bpy.ops.mesh.primitive_plane_add(size=400); bpy.context.object.data.materials.append(ground_m)
for i, (x, y, r, sz) in enumerate([(-9, 16, 5, 2.2), (8, 20, 6, 2.6), (-3, 30, 7, 2.0), (16, 34, 8, 2.4), (-18, 28, 7, 2.8), (3, 44, 9, 2.2)]):
    rock(f"mesa{i}", (x, y, r * sz * 0.22), r, 4, 0.3, rock_m, (1, 1, sz * 0.5))
for i in range(26):
    x, y = random.uniform(-7, 7), random.uniform(-3, 9)
    if abs(x) < 3.2 and abs(y) < 1.6: continue
    r = random.uniform(0.08, 0.3); rock(f"st{i}", (x, y, r * 0.5), r, 2, 0.4, rock_m)

# ---------- boulder ----------
boulder = rock("boulder", (2.25, 0, 1.25), 1.35, 5, 0.22, boulder_m)

# ---------- character (original: 'Kip', a round clay-like hero with a glowing chest core) ----------
skin = mat("skin", (0.95, 0.62, 0.28), 0.55); suit = mat("suit", (0.10, 0.22, 0.62), 0.5)
white = mat("white", (0.95, 0.95, 0.95), 0.25); black = mat("black", (0.01, 0.01, 0.01), 0.15)
core = mat("core", (0.2, 0.9, 1.0), 0.3, emit=(0.15, 0.85, 1.0), strength=12); scarf = mat("scarf", (0.85, 0.10, 0.12), 0.6)
root = empty("kip", (0, 0, 0))
body = empty("body", (0, 0, 0.55), root)
sphere("torso", (0, 0, 0.78), (0.33, 0.30, 0.40), suit, body)
sphere("core", (0.27, 0, 0.84), (0.09, 0.11, 0.11), core, body)
sphere("scarf", (0, 0, 1.14), (0.27, 0.27, 0.10), scarf, body)
tail = sphere("scarftail", (-0.34, 0.05, 1.05), (0.26, 0.05, 0.09), scarf, body); tail.rotation_euler = (0, 0.5, 0)
head = empty("head", (0, 0, 1.2), body)
sphere("skull", (0, 0, 1.52), (0.36, 0.34, 0.33), skin, head)
eyes = []
for s in (1, -1):
    ew = sphere("eye", (0.27, 0.14 * s, 1.56), (0.09, 0.10, 0.12), white, head); eyes.append(ew)
    sphere("pupil", (0.335, 0.14 * s, 1.56), (0.04, 0.05, 0.065), black, ew)
    sphere("foot", (0.06, 0.16 * s, 0.09), (0.19, 0.12, 0.09), suit, root)
    sphere("leg", (0, 0.16 * s, 0.32), (0.10, 0.10, 0.22), suit, body)
shoulderF = empty("shF", (0.05, -0.33, 1.0), body)     # camera-side arm does the flick
sphere("armF", (0.05, -0.36, 0.76), (0.085, 0.085, 0.26), suit, shoulderF)
sphere("handF", (0.05, -0.36, 0.47), (0.12, 0.11, 0.12), skin, shoulderF)
shoulderB = empty("shB", (0.05, 0.33, 1.0), body)
sphere("armB", (0.05, 0.36, 0.76), (0.085, 0.085, 0.26), suit, shoulderB)
sphere("handB", (0.05, 0.36, 0.47), (0.12, 0.11, 0.12), skin, shoulderB)
root.location = (0.15, 0, 0)

# idle bob + anticipation + flick (shot A/B), all eased bezier
for f, z in ((1, 0.55), (16, 0.58), (31, 0.55), (46, 0.58), (58, 0.55), (84, 0.47), (92, 0.60), (104, 0.55)):
    key(body, "location", (0, 0, z), f)
key(shoulderF, "rotation_euler", (0, 0, 0), 40)
key(shoulderF, "rotation_euler", (0, math.radians(-95), 0), 62)      # arm up, pointing at the boulder
key(shoulderF, "rotation_euler", (0, math.radians(-70), 0), 84)      # wind back (anticipation, 22 f)
key(shoulderF, "rotation_euler", (0, math.radians(-108), 0), 90)     # flick (6 f)
key(shoulderF, "rotation_euler", (0, math.radians(-95), 0), 110)
key(head, "rotation_euler", (0, 0, 0), 100); key(head, "rotation_euler", (0, math.radians(-38), 0), 122)  # watch it go
key(head, "rotation_euler", (0, math.radians(-38), 0), 190)

# boulder launch at f90: squash, then gone along a steep arc
key(boulder, "scale", (1, 1, 1), 86); key(boulder, "scale", (0.82, 1.1, 1.1), 90); key(boulder, "scale", (1.25, 0.9, 0.9), 93)
key(boulder, "location", (2.25, 0, 1.25), 90)
key(boulder, "location", (7, 2, 6), 94); key(boulder, "location", (40, 30, 55), 112); key(boulder, "location", (160, 160, 330), 160)
key(boulder, "scale", (1, 1, 1), 100)

# impact flash + shock ring (emissive, scale-animated)
flash_m = mat("flash", (1, 0.9, 0.6), 0.5, emit=(1.0, 0.75, 0.3), strength=14)
flash = sphere("flash", (0.95, -0.3, 1.25), (1, 1, 1), flash_m)
for f, s in ((88, 0.001), (90, 0.36), (94, 0.18), (99, 0.001)): key(flash, "scale", (s, s, s), f)
bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.035, location=(2.25, 0, 0.04))
ring = bpy.context.object; ring.data.materials.append(core); bpy.ops.object.shade_smooth()
for f, s in ((89, 0.001), (90, 0.3), (104, 3.2), (112, 5.0)): key(ring, "scale", (s, s, s), f)
key(ring, "location", (2.25, 0, 0.04), 112); key(ring, "location", (2.25, 0, -30), 113)
trail_m = mat("trail", (1, 0.6, 0.2), 0.5, emit=(1.0, 0.5, 0.15), strength=25)
for i in range(14):   # glowing embers that follow the boulder, staggered
    t = sphere(f"ember{i}", (2.25, 0, -5), (0.09,) * 3, trail_m, seg=12); d = 1 + i
    key(t, "location", (2.25, 0, -5), 90 + d)
    p0 = Vector((3 + random.uniform(-.3, .3), random.uniform(-.3, .3), 2 + random.uniform(-.3, .3)))
    key(t, "location", p0, 91 + d); key(t, "location", p0 + Vector((6 + i * 1.5, 4 + i, 9 + i * 2.2)), 118 + d * 2)
    key(t, "scale", (0.16,) * 3, 91 + d); key(t, "scale", (0.001,) * 3, 122 + d * 2)

# shot C: the ground gives way (Newton's third law). Kip drops to chest depth, debris jumps, eyes go wide.
crater_m = mat("crater", (0.03, 0.015, 0.01), 1.0)
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.02, vertices=48, location=(0.15, 0, 0.012)); crater = bpy.context.object
crater.data.materials.append(crater_m)
key(crater, "scale", (0.001, 0.001, 1), 205); key(crater, "scale", (0.75, 0.75, 1), 211)
key(root, "location", (0.15, 0, 0), 205); key(root, "location", (0.15, 0, -0.95), 212)
key(root, "location", (0.15, 0, -0.88), 218); key(root, "location", (0.15, 0, -0.90), 300)
key(head, "rotation_euler", (0, math.radians(-38), 0), 196); key(head, "rotation_euler", (0, 0, 0), 204)
key(head, "rotation_euler", (0, math.radians(18), 0), 222); key(head, "rotation_euler", (0, math.radians(-12), math.radians(-35)), 262)
for ew in eyes:
    key(ew, "scale", (0.09, 0.10, 0.12), 205); key(ew, "scale", (0.11, 0.135, 0.17), 211)
    key(ew, "scale", (0.11, 0.135, 0.03), 240); key(ew, "scale", (0.11, 0.135, 0.17), 244)   # blink
key(shoulderF, "rotation_euler", (0, math.radians(-95), 0), 204); key(shoulderF, "rotation_euler", (math.radians(75), 0, 0), 214)
key(shoulderB, "rotation_euler", (0, 0, 0), 204); key(shoulderB, "rotation_euler", (math.radians(-75), 0, 0), 214)
for i in range(22):
    ang = random.uniform(0, math.tau); r0 = random.uniform(0.5, 0.9); sz = random.uniform(0.06, 0.2)
    c = rock(f"deb{i}", (0.15 + math.cos(ang) * r0, math.sin(ang) * r0, -1), sz, 1, 0.3, rock_m)
    p = Vector((0.15 + math.cos(ang) * r0, math.sin(ang) * r0, 0)); out = Vector((math.cos(ang), math.sin(ang), 0))
    up = random.uniform(1.0, 2.6); dist = random.uniform(0.6, 1.8)
    key(c, "location", p + Vector((0, 0, -1)), 205); key(c, "location", p, 207)
    key(c, "location", p + out * dist * 0.5 + Vector((0, 0, up)), 216); key(c, "location", p + out * dist + Vector((0, 0, sz * 0.4)), 228)
    key(c, "rotation_euler", (0, 0, 0), 207); key(c, "rotation_euler", (random.uniform(-6, 6), random.uniform(-6, 6), 0), 228)
for i in range(7):   # cracks: thin dark slabs radiating from the crater
    ang = i / 7 * math.tau + 0.3; L = random.uniform(1.2, 2.4)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.15 + math.cos(ang) * (0.7 + L / 2), math.sin(ang) * (0.7 + L / 2), 0.006)); c = bpy.context.object
    c.rotation_euler = (0, 0, ang); c.data.materials.append(crater_m)
    key(c, "scale", (0.001, 0.05, 0.01), 207); key(c, "scale", (L, 0.07, 0.01), 213)

# ---------- lights: warm low key (sun), cool fill, cyan rim ----------
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(68), 0, math.radians(125))); sun = bpy.context.object
sun.data.energy = 4.5; sun.data.color = (1.0, 0.72, 0.5); sun.data.angle = math.radians(3)
bpy.ops.object.light_add(type='AREA', location=(-3, -6, 4)); fill = bpy.context.object; fill.data.energy = 500; fill.data.size = 6; fill.data.color = (0.55, 0.65, 1.0)
bpy.ops.object.light_add(type='AREA', location=(-2.5, 4, 3.5)); rim = bpy.context.object; rim.data.energy = 1400; rim.data.size = 2; rim.data.color = (0.3, 0.8, 1.0)
for l in (fill, rim):
    c = l.constraints.new('TRACK_TO'); c.target = root

# ---------- cameras ----------
aim = empty("aim", (1.0, 0, 2.3))
bpy.ops.object.camera_add(location=(1.0, -11.5, 1.3)); camA = bpy.context.object; camA.data.lens = 42
c = camA.constraints.new('TRACK_TO'); c.target = aim
camA.data.dof.use_dof = True; camA.data.dof.focus_object = root; camA.data.dof.aperture_fstop = 2.8
key(camA, "location", (1.0, -11.5, 1.3), 1); key(camA, "location", (1.0, -9.2, 1.3), 86)        # slow push-in, 85 f
key(camA, "location", (1.0, -9.6, 1.25), 92); key(camA, "location", (0.6, -10.5, 1.0), 195)     # recoil, then drift back
key(aim, "location", (1.0, 0, 2.3), 92); key(aim, "location", (2.4, 0, 5.2), 122); key(aim, "location", (2.6, 0, 5.6), 195)  # tilt up after the boulder
aimC = empty("aimC", (0.15, 0, 1.75))
bpy.ops.object.camera_add(location=(4.6, -5.2, 2.3)); camC = bpy.context.object; camC.data.lens = 42
c = camC.constraints.new('TRACK_TO'); c.target = aimC
camC.data.dof.use_dof = True; camC.data.dof.focus_object = root; camC.data.dof.aperture_fstop = 2.0
key(camC, "location", (4.6, -5.2, 2.3), 196); key(camC, "location", (3.9, -4.6, 1.9), 300)       # push-in on the reaction
key(camC, "location", (4.6, -5.2, 2.45), 211); key(camC, "location", (4.5, -5.1, 2.2), 215)      # impact shake
key(aimC, "location", (0.15, 0, 1.75), 205); key(aimC, "location", (0.15, 0, 1.35), 214)
for f, cam in ((1, camA), (196, camC)):
    mk = S.timeline_markers.new(f"c{f}", frame=f); mk.camera = cam
S.camera = camA

# ---------- render ----------
r = S.render
r.engine = 'CYCLES'; r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, 100
r.image_settings.file_format = 'PNG'; r.image_settings.compression = 15
r.use_motion_blur = True; r.motion_blur_shutter = 0.5; r.use_persistent_data = True
cy = S.cycles; cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = False; cy.use_denoising = True
cy.max_bounces = 3; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.caustics_reflective = False; cy.caustics_refractive = False
S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Medium High Contrast'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "..", "demo.blend"))
frames = ONLY or list(range(1, 301, STEP))
for f in frames:
    p = os.path.join(OUT, f"f{f:04d}.png")
    if os.path.exists(p): continue
    S.frame_set(f); r.filepath = p; t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time() - t:.1f}s", flush=True)
