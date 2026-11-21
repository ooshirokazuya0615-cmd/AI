import sys, time, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/user/AI/tools/nonverbal')
import numpy as np, render, sim, stickman_scene
rec = sim.simulate(sim.Params(**stickman_scene.TAKE))
sc = stickman_scene.Scene(None, render.Config(540, 960, 30, 9, 3), rec)
t0 = time.time(); buf = sc.audio(); print('synth', round(time.time()-t0, 2), 's', buf.shape, 'peak', np.abs(buf).max().round(3))
print('tally', sc.sound_tally, 'kept', len(sc.sound_events))
render.master_audio(buf, 'debug/audio.wav')
