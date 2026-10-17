import sys, itertools, sim
for bv, fr, tone in itertools.product([520, 700], [0.3, 0.45], [0.6, 1.0]):
    for s in range(3):
        rec = sim.simulate(sim.Params(seed=s, ball_v=bv, stair_fric=fr, tone=tone))
        ok, score, n = sim.evaluate(rec)
        print(bv, fr, tone, s, ok, round(score,1), n['steps'], n['pegs'], n['t_pad'], n['pad_bounces'], n['end'], n['rest_speed'])
