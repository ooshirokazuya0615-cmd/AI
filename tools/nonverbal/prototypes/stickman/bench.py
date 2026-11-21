import sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/user/AI/tools/nonverbal')
import render, sim, stickman_scene
w, h = int(sys.argv[1]), int(sys.argv[2])
rec = sim.simulate(sim.Params(**stickman_scene.TAKE))
gpu = render.Gpu(w, h)
sc = stickman_scene.Scene(gpu, render.Config(w, h, 60, 9, 3), rec)
sc.render(0); gpu.read()
t0 = time.time()
fs = list(range(0, sc.frame_count, sc.frame_count // 24))
for f in fs:
    sc.render(f); gpu.read()
print(w, h, 'render+readback fps', round(len(fs) / (time.time() - t0), 2))
