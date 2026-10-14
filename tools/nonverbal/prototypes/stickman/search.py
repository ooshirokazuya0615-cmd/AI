"""Story tuner: run many seeded variants in parallel and rank them by story beats."""
import ast
import itertools
import sys
import time
from multiprocessing import Pool

import numpy as np

import sim


def extra(rec):
    ev = [e for e in rec.events if e['other'] == 'body' and e['a'] == 'pad']
    if not ev:
        return 0, 0, 0
    i0 = int(ev[0]['t'] / sim.DT)
    tor = rec.bodies[i0:, 0, 1]
    pad_min = rec.pad[:, 0].min() - sim.PAD_TOP_REST
    lows = tor[:int(0.25 / sim.DT)].min()
    bounce = tor[int(0.1 / sim.DT):int(1.2 / sim.DT)].max() - lows if len(tor) > int(1.2 / sim.DT) else 0
    cx = np.abs(rec.bodies[int(3 / sim.DT):int(5 / sim.DT), 0, 0]).mean()
    return round(pad_min), round(bounce), round(cx)


def job(args):
    kw, s = args
    rec = sim.simulate(sim.Params(seed=s, **kw))
    ok, score, n = sim.evaluate(rec)
    pm, bo, cx = extra(rec)
    score += min(bo, 400) / 100 - max(cx - 250, 0) / 100
    return (bool(ok), round(float(score), 2), kw, s, n['steps'], n['pegs'], n['t_pad'], pm, bo, cx,
            float(n['rest_speed']), n['end'])


if __name__ == '__main__':
    grid = ast.literal_eval(sys.argv[1]) if len(sys.argv) > 1 else dict(ball_v=[480, 560, 640])
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    jobs = [(dict(zip(grid, vals)), s) for vals in itertools.product(*grid.values()) for s in range(seeds)]
    t0 = time.time()
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    print('runs', len(res), 'time', round(time.time() - t0, 1), 'ok', sum(r[0] for r in res))
    print('(ok, score, params, seed, steps, pegs, t_pad, pad_min, bounce, |x|, rest, end)')
    for r in sorted(res, key=lambda r: (not r[0], -r[1]))[:12]:
        print(r)
