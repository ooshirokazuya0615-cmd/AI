"""
Time bpy renders of scene.blend per engine.

  venv/bin/python render_bench.py --engine CYCLES --samples 32 --frames 300,301,302
"""
import argparse
import json
import os
import time
from pathlib import Path

import bpy

ap = argparse.ArgumentParser()
ap.add_argument('--engine', required=True, choices=['WORKBENCH', 'EEVEE', 'CYCLES'])
ap.add_argument('--frames', default='300,301,302')
ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--res', default='1080x1920')
ap.add_argument('--tag', default='')
ap.add_argument('--raytrace', type=int, default=1, help='EEVEE: screen-space raytracing on/off')
ap.add_argument('--noise', type=int, default=1, help='Cycles: OIDN denoise on/off')
ap.add_argument('--outdir', default='renders')
a = ap.parse_args()

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'scene.blend'))
sc = bpy.context.scene
W, H = (int(v) for v in a.res.split('x'))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
sc.render.image_settings.compression = 15

if a.engine == 'WORKBENCH':
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = True
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_specular_highlight = True
    sc.display.render_aa = '8'
elif a.engine == 'EEVEE':
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    ee = sc.eevee
    ee.taa_render_samples = a.samples
    ee.use_raytracing = bool(a.raytrace)
    ee.ray_tracing_method = 'SCREEN'
    ee.use_shadows = True
    ee.use_fast_gi = True
else:
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = a.samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = bool(a.noise)
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.denoising_prefilter = 'ACCURATE'
    cy.max_bounces = 8
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 4
    cy.transmission_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 10
    sc.render.use_persistent_data = True   # keep BVH/shaders between animation frames

out = HERE / a.outdir
out.mkdir(exist_ok=True)
tag = a.tag or f'{a.engine.lower()}'
times = []
for f in (int(v) for v in a.frames.split(',')):
    sc.frame_set(f)
    sc.render.filepath = str(out / f'{tag}-f{f:04d}.png')
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    times.append(time.perf_counter() - t0)
    print(f'BENCH {tag} frame {f}: {times[-1]:.2f} s', flush=True)
res = dict(tag=tag, engine=a.engine, res=a.res, samples=a.samples, times=times,
           first=times[0], steady=sum(times[1:]) / max(1, len(times) - 1))
print('RESULT', json.dumps(res), flush=True)
with open(HERE / 'bench_results.jsonl', 'a') as fh:
    fh.write(json.dumps(res) + '\n')
