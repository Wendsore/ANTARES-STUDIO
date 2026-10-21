"""Script exécuté PAR Blender (``blender -b --python planete.py -- SORTIE IMAGES LARGEUR HAUTEUR TOURS C1 C2 ECH``).

Planète : sphère lisse, texture procédurale (bruit → dégradé entre deux couleurs), inclinaison 23,4°,
rotation linéaire de ``TOURS`` tours sur ``IMAGES`` images, fond transparent, rendu Cycles CPU.
Aucune donnée extérieure n'est lue : la géométrie est générée localement (master prompt §9.1).
"""

import math
import os
import sys

import bpy


def _color(hex6: str) -> tuple[float, float, float, float]:
    h = hex6.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)  # type: ignore[return-value]


argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
out = argv[0]
frames = int(argv[1])
width, height = int(argv[2]), int(argv[3])
turns = float(argv[4])
c1, c2 = _color(argv[5]), _color(argv[6])
samples = int(argv[7])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.frame_start, scene.frame_end = 1, frames
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True
scene.render.filepath = os.path.join(out, "frame_")

bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
planet = bpy.context.active_object
bpy.ops.object.shade_smooth()
mat = bpy.data.materials.new("Planete")
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
bsdf = nodes["Principled BSDF"]
noise = nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 4.0
ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = c1
ramp.color_ramp.elements[1].color = c2
links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
planet.data.materials.append(mat)
planet.rotation_euler = (math.radians(23.4), 0.0, 0.0)
planet.keyframe_insert("rotation_euler", frame=1)
planet.rotation_euler = (math.radians(23.4), 0.0, math.tau * turns)
planet.keyframe_insert(
    "rotation_euler", frame=frames + 1
)  # boucle exacte : la dernière image précède le retour
for fc in planet.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
bpy.ops.object.light_add(type="SUN", location=(5, -5, 5))
bpy.context.active_object.data.energy = 4.0
bpy.ops.object.camera_add(location=(0.0, -4.5, 0.0), rotation=(math.radians(90), 0.0, 0.0))
scene.camera = bpy.context.active_object
bpy.ops.render.render(animation=True)
print("ANTARES_BLENDER_DONE", len([f for f in os.listdir(out) if f.endswith(".png")]))
