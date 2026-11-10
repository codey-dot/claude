import bpy, sys, time, math, json, os
out = sys.argv[sys.argv.index("--") + 1]
engine = sys.argv[sys.argv.index("--") + 2]
samples = int(sys.argv[sys.argv.index("--") + 3])
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene

def mat(name, col, rough=0.5, metal=0.0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 8
    return m

# set: floor, back wall, pillars, props (~40 objects)
bpy.ops.mesh.primitive_plane_add(size=40); bpy.context.object.data.materials.append(mat("floor", (0.08, 0.07, 0.10), 0.25))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 8, 0), rotation=(math.pi/2, 0, 0)); bpy.context.object.data.materials.append(mat("wall", (0.10, 0.12, 0.2), 0.8))
pm = mat("pillar", (0.5, 0.45, 0.4), 0.6)
for i in range(-4, 5):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=8, location=(i*2.2, 6, 4), vertices=48); o = bpy.context.object
    o.data.materials.append(pm); bpy.ops.object.shade_smooth()
gm = mat("glow", (0.1, 0.4, 1.0), 0.3, emit=(0.1, 0.5, 1.0))
for i in range(24):
    a = i/24*math.tau
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.12, subdivisions=3, location=(math.cos(a)*1.6, math.sin(a)*1.6, 1.2+0.5*math.sin(3*a)))
    bpy.context.object.data.materials.append(gm)

# character: skinned primitives on an armature (stand-in for a stylized rig), subsurf level 2
bpy.ops.object.armature_add(location=(0, 0, 0)); arm = bpy.context.object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones; root = eb[0]; root.name = "spine"; root.head = (0, 0, 0.9); root.tail = (0, 0, 1.5)
def bone(n, h, t, p):
    b = eb.new(n); b.head = h; b.tail = t; b.parent = eb[p]; return b
bone("head", (0, 0, 1.5), (0, 0, 1.9), "spine")
for s, x in (("L", 1), ("R", -1)):
    bone("uarm"+s, (0.22*x, 0, 1.45), (0.5*x, 0, 1.45), "spine"); bone("larm"+s, (0.5*x, 0, 1.45), (0.8*x, 0, 1.45), "uarm"+s)
    bone("uleg"+s, (0.12*x, 0, 0.9), (0.12*x, 0, 0.45), "spine"); bone("lleg"+s, (0.12*x, 0, 0.45), (0.12*x, 0, 0), "uleg"+s)
bpy.ops.object.mode_set(mode='OBJECT')
skin = mat("skin", (0.8, 0.5, 0.35), 0.45); cloth = mat("cloth", (0.6, 0.08, 0.1), 0.7)
parts = [("spine", (0, 0, 1.2), (0.25, 0.16, 0.34), cloth), ("head", (0, 0, 1.72), (0.2, 0.2, 0.22), skin)]
for s, x in (("L", 1), ("R", -1)):
    parts += [("uarm"+s, (0.36*x, 0, 1.45), (0.16, 0.07, 0.07), cloth), ("larm"+s, (0.65*x, 0, 1.45), (0.16, 0.06, 0.06), skin),
              ("uleg"+s, (0.12*x, 0, 0.67), (0.09, 0.09, 0.24), cloth), ("lleg"+s, (0.12*x, 0, 0.22), (0.08, 0.08, 0.24), cloth)]
for bn, loc, sc, m in parts:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc, scale=sc); o = bpy.context.object
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    o.modifiers.new("ss", "SUBSURF").levels = 2; o.modifiers["ss"].render_levels = 2
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bn
    o.matrix_world.translation = loc
# animate: arm swing + body turn so motion blur has work
for f, r in ((1, -0.8), (13, 0.8), (25, -0.8)):
    for bn in ("uarmL", "uarmR", "ulegL"):
        pb = arm.pose.bones[bn]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (r, 0, r/2); pb.keyframe_insert("rotation_euler", frame=f)
    arm.rotation_euler = (0, 0, r/3); arm.keyframe_insert("rotation_euler", frame=f)

# lights: key, fill, rim + world
def light(t, loc, e, col, size=2):
    bpy.ops.object.light_add(type=t, location=loc); l = bpy.context.object; l.data.energy = e; l.data.color = col
    if t == 'AREA': l.data.size = size
    c = l.constraints.new('TRACK_TO'); c.target = arm; return l
light('AREA', (3, -4, 4), 900, (1, 0.85, 0.7)); light('AREA', (-4, -3, 2), 250, (0.5, 0.6, 1), 4); light('SPOT', (0, 5, 4), 2500, (0.3, 0.6, 1))
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.015, 0.04, 1); S.world = w
# camera with DoF
bpy.ops.object.camera_add(location=(0.6, -5.2, 1.5)); cam = bpy.context.object; S.camera = cam
cam.data.lens = 50; cam.data.dof.use_dof = True; cam.data.dof.focus_object = arm; cam.data.dof.aperture_fstop = 1.8
c = cam.constraints.new('TRACK_TO'); c.target = arm
e = bpy.data.objects.new("aim", None); S.collection.objects.link(e); e.location = (0, 0, 1.2); c.target = e

S.render.resolution_x, S.render.resolution_y, S.render.resolution_percentage = 1080, 1920, 100
S.render.fps = 30; S.render.image_settings.file_format = 'PNG'; S.render.use_motion_blur = True
S.render.engine = engine
if engine == 'CYCLES':
    S.cycles.device = 'CPU'; S.cycles.samples = samples; S.cycles.use_denoising = True
    S.cycles.use_adaptive_sampling = True; S.cycles.max_bounces = 6
else:
    S.eevee.taa_render_samples = samples
res = {"engine": engine, "samples": samples, "frames": []}
for f in (5, 9):
    S.frame_set(f); S.render.filepath = os.path.join(out, f"{engine}_{samples}_{f:04d}.png")
    t = time.time()
    try:
        bpy.ops.render.render(write_still=True); res["frames"].append(round(time.time()-t, 2))
    except Exception as ex:
        res["error"] = str(ex); break
print("BENCH", json.dumps(res))
