# fleetab.py - same-position A/B for step 6. Plays games, snapshots the start of every Hard+ turn (Fleets still in the pool), then plans each snapshot twice:
#   A = old way: Fleets placed and moved by cpuPlace/cpuFleetMove, then the plan   B = Fleets placed and moved inside the plan.
# Prints the average plan value (the planner's own score of the finished turn) for A and B and their paired difference.
# usage: python3 tools/fleetab.py --games 12 --reps 2 [--pc fMove=0] [--minround 3]
import argparse, json, os, statistics as st
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser(); ap.add_argument('--html', default='constellate.html'); ap.add_argument('--games', type=int, default=12)
ap.add_argument('--reps', type=int, default=2); ap.add_argument('--every', type=int, default=2); ap.add_argument('--minround', type=int, default=3)
ap.add_argument('--pc', action='append', default=[]); ap.add_argument('--seed0', type=int, default=3000); ap.add_argument('--levels', default='5,4')
a = ap.parse_args()
SNAP = """() => { window.__snaps = []; window.__st = ''; window.__k = 0; const o = window.cpuStep;
  window.cpuStep = function () { const tid = G.round + ':' + G.ti + ':' + cur();
    if (tid != window.__st) { window.__st = tid; if (G.pool > 0 && cpuLvl() >= 4 && G.round >= %d && (window.__k++ %% %d) == 0) window.__snaps.push(JSON.stringify(G)); }
    return o.apply(this, arguments); }; }""" % (a.minround, a.every)
EVAL = """([snap, mode]) => { G = JSON.parse(snap); const me = cur(); cpuTurn = ''; const tid = G.round + ':' + G.ti + ':' + me;
  cpuTurn = tid; cpuBad = new Set(); cpuStall = 0; cpuNew = []; cpuGeo.g = null; cpuDanger = cpuLvl() > 1 && cpuDangerCheck(me);
  cpuPlan = { tid: tid, q: [], made: 0 };
  if (mode == 'A') { const keep = new Set(cpuFleetLv); cpuFleetLv.clear(); let n = 0; while (G.pool > 0 && placeable().length && n++ < 20) cpuPlace(); n = 0; while (cpuFleetMove() && n++ < 20); cpuPlan.q = cpuPlanMake(); const v = cpuPlan.pred ? cpuPlan.pred.val : null; keep.forEach(x => cpuFleetLv.add(x)); return v; }
  cpuFleetLv.add(cpuLvl()); cpuPlan.q = cpuPlanMake(); return cpuPlan.pred ? cpuPlan.pred.val : null; }"""
base = [int(x) for x in a.levels.split(',')]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto('file://' + os.path.abspath(a.html)); pg.wait_for_timeout(300)
    for x in a.pc:
        k, v = x.split('='); pg.evaluate('([k,v]) => { cpuPlanCfg[k] = v }', [k, float(v)])
    pg.evaluate('() => { cpuPlanCfg.pred = true; cpuMs = 0; }')
    pg.evaluate(SNAP)
    PLAYG = """([n, levels, seed]) => { cpuSeed = seed; cpuErr = null; cpuPlan = null; const pl = n == 2 ? [0, 2] : [0, 2, 3, 1], cpu = {}; pl.forEach((c, i) => cpu[c] = levels[i]); start(n, 7, null, cpu); cpuAuto(300000); return G.round; }"""
    A, B, D, snaps = [], [], [], 0
    for g in range(a.games):
        lv = base[g % len(base):] + base[:g % len(base)]
        pg.evaluate('() => { window.__snaps = []; window.__k = 0; window.__st = ""; }')
        pg.evaluate(PLAYG, [2, lv, a.seed0 + g])
        snap = pg.evaluate('() => window.__snaps')
        snaps += len(snap)
        for sn in snap:
            va = [pg.evaluate(EVAL, [sn, 'A']) for _ in range(a.reps)]
            vb = [pg.evaluate(EVAL, [sn, 'B']) for _ in range(a.reps)]
            if None in va or None in vb: continue
            ma, mb = sum(va) / len(va), sum(vb) / len(vb); A.append(ma); B.append(mb); D.append(mb - ma)
    n = len(D); m = st.mean(D); se = st.stdev(D) / n ** .5 if n > 1 else 0
    print(f'{n} positions | plan value A (old fleets) {st.mean(A):.2f}  B (fleets in plan) {st.mean(B):.2f} | B-A {m:+.3f} (+-{1.96*se:.3f}) | B better in {sum(d>0.01 for d in D)}, worse in {sum(d<-0.01 for d in D)}, same {sum(abs(d)<=0.01 for d in D)}')
    big = sorted(D); print('quartiles of B-A:', [round(big[int(n*q)],2) for q in (0.05,.25,.5,.75,.95)])
