#!/usr/bin/env python3
"""CPU self-play harness for Constellate (headless Chromium).

Plays CPU-vs-CPU games on a build of constellate.html and appends one JSON line per game to a results file.
Resumable: re-running with the same --out skips game numbers already in the file.

  python tools/harness.py --html constellate.html --n 4 --levels 3,3,2,2 --games 40 --out res/h_vs_m.jsonl
  python tools/harness.py --summary res/h_vs_m.jsonl

--levels gives one CPU level per seat (1 Easy, 2 Medium, 3 Hard = planner + step 4 terms, 4 Hard (legacy) = the old greedy Hard, 5 Hard+F = test level, Hard that also plans Fleets). The seat assignment rotates every game
so seat order / first-move advantage averages out. --set LEVEL:KEY=VALUE (repeatable) overrides one value of the CPU parameter table for the run, e.g. --set 4:apCost=1.
--seed0 + game number seeds the CPU's random wobble.

  python tools/harness.py --html constellate.html --check --n 2 --levels 3,2 --games 40
    = scoring self-test: after every turn it compares the fast tally (cpuInc / incPot1 / incPot2) with the slow originals
    (calc / cpuPot / cpuPot2) and the new evaluator incEval with an independent slow rewrite (slowEval, in this file) on the real position and on random multi-step changes, then undoes them. Prints any mismatch.
"""
import argparse, json, os, sys, time
from playwright.sync_api import sync_playwright

# JS injected into the page: switches off drawing/saving, then records every CPU move, turn end and elimination.
HOOK = """() => {
  cpuTimers = false;                                   // no timers: cpuAuto plays straight through
  for (const k of ['render','histSnap','histSave','say','fit','overDlg','roundPop']) window[k] = () => {};
  window.__log = {turns: [], kills: [], rv: []};
  window.__t = {moves: 0, spent: 0, big: 0, bigSpent: 0};   // the current turn so far
  const wrapMove = name => { const f = window[name];
    window[name] = function () { const ap0 = G.ap; const r = f.apply(this, arguments);
      const c = ap0 - G.ap;                            // AP this move cost (0 if it failed)
      if (c > 0) { __t.moves++; __t.spent += c; if (c >= 4) { __t.big++; __t.bigSpent += c; } }
      return r; }; };
  wrapMove('cpuDo'); wrapMove('cpuMultiDo');
  const et = window.endTurn;
  window.endTurn = function () { if (G && !G.over && cpuOf(cur())) {
      if (G.ti == G.order.length - 1) __log.rv.push([G.round, calc().vp.slice()]);
      __log.turns.push([cpuLvl(), G.round, acts(G.round), G.ap, __t.moves, __t.spent, __t.big, __t.bigSpent]); }
    __t = {moves: 0, spent: 0, big: 0, bigSpent: 0}; return et.apply(this, arguments); };
  window.__pc6 = {};                                   // --pc6 KEY=VALUE: planner values (cpuPlanCfg) used only while the Custom level (6) plans
  { const pm = window.cpuPlanMake;
    window.cpuPlanMake = function () { const ov = cpuRaw() == 6 ? __pc6 : null, keep = {};
      if (ov) for (const k in ov) { keep[k] = cpuPlanCfg[k]; cpuPlanCfg[k] = ov[k]; }
      try { return pm.apply(this, arguments); } finally { for (const k in keep) cpuPlanCfg[k] = keep[k]; } }; }
  const k0 = window.kill;
  window.kill = function (c) { __log.kills.push([G.round, c]); return k0.apply(this, arguments); };
  return true; }"""


# JS for --check: __checkInc() runs after every turn. It compares the fast tally with the slow originals on the real position
# (some runs with random players marked eliminated) and on random chains of 1-6 changes (a star appears / a star changes owner),
# then undoes the chain and demands the tally be bit-for-bit back to where it started.
CHECK = """() => {
  window.__chk = {pos: 0, chains: 0, evals: 0, bad: [], maxd: 0};
  const rnd = n => Math.floor(Math.random() * n), N = () => NSYS(G);
  const copyS = S => ({...S, stars: S.stars.map(q => ({...q})), alive: {...S.alive}});
  const note = (what, extra) => { if (__chk.bad.length < 20) __chk.bad.push(what + ' ' + JSON.stringify(extra)); };
  const same = (T, S, tag) => {                        // tally T versus the slow functions on board S
    const f = calc(S);
    for (const c of [0, 1, 2, 3]) if (incVp(T, c) !== f.vp[c]) note('vp ' + tag, {c, fast: incVp(T, c), slow: f.vp[c]});
    for (let y = 0; y < T.Z; y++) for (let x = 0; x < T.Z; x++) if (T.ctl[y * T.Z + x] !== f.ctl[y][x]) note('ctl ' + tag, {x, y});
    const sets = [cpuDefP(1), cpuDefP(2), cpuDefP(3), cpuDefP(4), randP(), randP()];
    for (const me of S.pl) for (const dg of [false, true]) {
      for (const P of sets) { const a = incEval(T, me, P, dg), b = slowEval(S, me, P, dg), d = Math.abs(a - b); __chk.evals++;
        if (!(d < 1e-9 * Math.max(1, Math.abs(b)))) note('eval ' + tag, {me, dg, fast: a, slow: b, P}); __chk.maxd = Math.max(__chk.maxd, d / Math.max(1, Math.abs(b))); }
      const a = incPot2(T, me, dg), b = cpuPot2(S, me, dg), d = Math.abs(a - b); __chk.evals++;
      if (!(d < 1e-9)) note('pot2 ' + tag, {me, dg, fast: a, slow: b}); __chk.maxd = Math.max(__chk.maxd, d);
      const a1 = incPot1(T, me), b1 = cpuPot(S, me), d1 = Math.abs(a1 - b1); __chk.evals++;
      if (!(d1 < 1e-9)) note('pot1 ' + tag, {me, fast: a1, slow: b1}); __chk.maxd = Math.max(__chk.maxd, d1);
    } };
  // slowEval = from-scratch rewrite of incEval (step 4) using only calc(S), for any parameter set P.
  const slowEval = (S, me, P, danger) => {
    const f = calc(S), Z = S.sz || 7, mid = (Z - 1) / 2, pl = S.pl.filter(c => S.alive[c]), vp = f.vp;
    const cnt = (x, y) => { const a = [0, 0, 0, 0]; S.stars.forEach(q => { if (Math.floor(q.x / 3) == x && Math.floor(q.y / 3) == y) a[q.o]++; }); return a; };
    const marg = (a, k) => { let o = 0; a.forEach((v, c) => { if (c != k && v > o) o = v; }); return Math.max(-2, Math.min(2, a[k] - o)); };
    const nc = cpuFeat.center && P.centerCut > 0 && !danger, secs = [];
    for (let y = 0; y < Z; y++) for (let x = 0; x < Z; x++) secs.push([x, y, cnt(x, y)]);
    const mg = k => { let t = 0; secs.forEach(([x, y, a]) => { if (!(nc && x == mid && y == mid)) t += marg(a, k); }); return t; };
    const eff = c => vp[c] - (nc && f.ctl[mid][mid] == c ? P.centerCut : 0);
    let v = eff(me) * P.ownVp + P.marginOwn * mg(me);
    for (let i = 0; i < Z; i++) [f.ctl[i], f.ctl.map(r => r[i])].forEach(L => {
      const mn = L.filter(c => c == me).length, others = new Set(L.filter(c => c >= 0 && c != me));
      if (!others.size) v += P.lineOwn * Math.pow(mn / Z, 2);
      else if (others.size == 1 && mn == 0) { const o = [...others][0]; if (S.alive[o]) v -= P.lineBlock * Math.pow(L.filter(c => c == o).length / Z, 2); } });
    const opp = pl.filter(c => c != me), lo = Math.min(vp[me], ...opp.map(c => vp[c]));
    opp.forEach(c => { const m = 1 + P.leaderBoost * Math.max(0, Math.min(1, (vp[c] - vp[me]) / P.leaderSpan)); v -= P.oppVp * m * eff(c) + P.marginOpp * m * mg(c); });
    const up = opp.map(c => vp[c]).filter(x => x > lo);
    if (P.elimPen > 0 && vp[me] == lo && up.length) { const g = Math.min(...up) - lo + P.elimBuffer; if (g > P.elimFrom) v -= P.elimPen * (g - P.elimFrom) / (4 - P.elimFrom); }
    return v; };
  const randP = () => Object.fromEntries(CPU_PARAMS.map(p => [p.k, +(p.min + p.step * rnd(Math.floor((p.max - p.min) / p.step + 1e-9) + 1)).toFixed(4)]));
  const snap = T => JSON.stringify([Array.from(T.n), Array.from(T.ctl), T.vp, Array.from(T.lc), T.mg]);
  window.__checkInc = () => {
    // step 5 part 1: the cached geometry (clearBB) must equal the game's clear, and the buffer table must equal cpuBuffer
    { const St = G.stars, me0 = cur(), sc = cpuSec(G), bt = cpuBufTab(me0, sc);
      for (let t = 0; t < 80; t++) { const a = St[rnd(St.length)], b = St[rnd(St.length)]; if (a === b) continue; __chk.evals++;
        if (clear(a, b) !== clearBB(a, b)) note('clearBB', {a: a.id, b: b.id}); }
      for (let t = 0; t < 40; t++) { const Np = {x: Math.random() * N(), y: Math.random() * N()}; __chk.evals++;
        const d = Math.abs(cpuBuffer(Np, me0, sc) - cpuBufFast(Np, bt)); if (d > 1e-12) note('buffer', {Np, d}); } }
    for (const killSome of [false, true]) {
      const S0 = copyS(G);
      if (killSome) { const c = S0.pl[rnd(S0.pl.length)]; S0.alive[c] = false; }
      const T = cpuInc(S0), s0 = snap(T); same(T, S0, 'base'); __chk.pos++;
      for (let t = 0; t < 12; t++) {
        const S = copyS(S0), log = [], len = 1 + rnd(6);
        for (let k = 0; k < len; k++) {
          if (rnd(2) || !S.stars.length) {             // a new star appears in a random empty system
            const x = rnd(N()), y = rnd(N()), c = S.pl[rnd(S.pl.length)];
            if (S.stars.some(q => Math.floor(q.x) == x && Math.floor(q.y) == y)) continue;
            S.stars.push({id: 9000 + k, x: x + .5, y: y + .5, o: c}); incStar(T, {x, y}, c, 1); log.push([{x, y}, c]);
          } else {                                     // a random star changes owner
            const q = S.stars[rnd(S.stars.length)], c = S.pl[rnd(S.pl.length)]; if (q.o == c) continue;
            incStar(T, q, q.o, -1); incStar(T, q, c, 1); log.push([q, q.o, c]); q.o = c;
          } }
        same(T, S, 'chain'); __chk.chains++;
        for (let k = log.length - 1; k >= 0; k--) { const l = log[k];   // undo in reverse
          if (l.length == 2) incStar(T, l[0], l[1], -1); else { incStar(T, l[0], l[2], -1); incStar(T, l[0], l[1], 1); } }
        if (snap(T) !== s0) { note('undo', {len: log.length}); return false; }
      } }
    return true; };
  const et = window.endTurn;                           // run the check at the end of every CPU turn
  window.endTurn = function () { if (G && !G.over) __checkInc(); return et.apply(this, arguments); };
  return true; }"""


PLANCHK = """() => {
  cpuPlanCfg.pred = true; window.__pc = {plans: 0, ok: 0, nbad: 0, apbad: 0, skipped: 0};
  const f = window.cpuPlanStep;
  window.cpuPlanStep = function () {
    const before = cpuPlan && cpuPlan.tid == cpuTurn ? cpuPlan : null, sf = cpuPS.stale + cpuPS.failed, made0 = cpuPS.plans;
    const r = f.apply(this, arguments);
    if (cpuPS.plans != made0) { window.__cur = {pred: cpuPlan.pred, sf: cpuPS.stale + cpuPS.failed}; }
    else if (!window.__cur) { }
    if (window.__cur && cpuPlan && cpuPlan.q.length == 0 && cpuPlan.pred === window.__cur.pred) {
      const c = window.__cur; window.__cur = null; __pc.plans++;
      if (cpuPS.stale + cpuPS.failed != c.sf) { __pc.skipped++; return r; }
      const T = cpuInc(G), a = Array.from(T.n), p = c.pred.n; let bad = 0; for (let i = 0; i < a.length; i++) if (a[i] != p[i]) bad++;
      if (bad) __pc.nbad++; if (G.ap != c.pred.ap) __pc.apbad++; if (!bad && G.ap == c.pred.ap) __pc.ok++;
    }
    return r; };
  return true; }"""

# JS that plays one game and returns its result.
PLAY = """([n, levels, seed, size]) => {
  cpuSeed = seed; __log.turns = []; __log.kills = []; __log.rv = []; __t = {moves: 0, spent: 0, big: 0, bigSpent: 0};
  const pl = n == 2 ? [0, 2] : [0, 2, 3, 1], cpu = {}; pl.forEach((c, i) => cpu[c] = levels[i]);
  cpuErr = null; cpuPlan = null; cpuPS = {plans: 0, rolls: 0, ms: 0, exec: 0, stale: 0, failed: 0, empty: 0, pl: 0, fm: 0, xp: 0, xf: 0}; start(n, size, null, cpu);
  const steps = cpuAuto(300000), vp = calc().vp;
  return {steps, over: G.over, rounds: G.round, vp, seats: cpu, kills: __log.kills, turns: __log.turns, err: cpuErr, ps: {...cpuPS}, rv: __log.rv, fails: (window.__fails||[]).splice(0)}; }"""

def run(a):
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            try: done.add(json.loads(line)['i'])
            except Exception: pass
    base = [int(x) for x in a.levels.split(',')]
    assert len(base) == a.n, 'need one level per seat'
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto('file://' + os.path.abspath(a.html)); pg.wait_for_timeout(300)
        pg.evaluate(HOOK)
        if a.check: pg.evaluate(CHECK)
        if a.planchk: pg.evaluate(PLANCHK)
        for x in a.plan: pg.evaluate('(lv) => cpuPlanLv.add(lv)', int(x))
        for x in a.fleet: pg.evaluate('(lv) => cpuFleetLv.add(lv)', int(x))   # --fleet 4 = let level 4 plan its Fleets too
        for x in a.pc:
            k, v = x.split('='); pg.evaluate('([k,v]) => { cpuPlanCfg[k] = v }', [k, float(v)])
        for x in a.pc6:                                   # --pc6 look=1 : planner value for the Custom level only
            k, v = x.split('='); pg.evaluate('([k,v]) => { __pc6[k] = v }', [k, float(v)])
        for x in a.set:                                   # --set 4:apCost=1  changes one CPU value (level:key=value) for this run
            lv, kv = x.split(':'); k, v = kv.split('=')
            pg.evaluate('([lv,k,v]) => cpuSet(lv, k, v)', [int(lv), k, float(v)])
        t0 = time.time(); k = 0; tot = dict(pos=0, chains=0, evals=0, bad=0, maxd=0.0)
        for i in range(a.games):
            if i in done: continue
            r = (i % a.n)                                 # rotate seats each game
            lv = base[r:] + base[:r]
            res = pg.evaluate(PLAY, [a.n, lv, a.seed0 + i, a.size])
            res.update(i=i, seed=a.seed0 + i, n=a.n)
            if a.check:
                c = pg.evaluate('() => { const r = __chk; window.__chk = {pos: 0, chains: 0, evals: 0, bad: [], maxd: 0}; return r }')
                res['chk'] = c; tot['pos'] += c['pos']; tot['chains'] += c['chains']; tot['evals'] += c['evals']; tot['bad'] += len(c['bad']); tot['maxd'] = max(tot['maxd'], c['maxd'])
                for m in c['bad'][:3]: print('MISMATCH', m, flush=True)
            with open(a.out, 'a') as f: f.write(json.dumps(res) + '\n')
            k += 1
            if a.verbose: print(f'game {i} rounds {res["rounds"]} over {res["over"]} {time.time()-t0:.0f}s', flush=True)
        if a.check: print(f"CHECK: {tot['pos']} positions, {tot['chains']} change chains, {tot['evals']} value comparisons, {tot['bad']} mismatches, worst difference {tot['maxd']:.2e}")
        if a.planchk: print('PLANCHK', pg.evaluate('() => __pc'))
        b.close()

def summary(path):
    G = [json.loads(l) for l in open(path)]
    ok = [g for g in G if g['over'] and not g['err']]
    print(f'{len(G)} games, {len(ok)} finished cleanly, {len(G)-len(ok)} problems')
    if not ok: return
    wins, seats = {}, {}                                  # win share and seat count per level
    for g in ok:
        for c, lv in g['seats'].items():
            seats[lv] = seats.get(lv, 0) + 1
            if int(c) in g['over']: wins[lv] = wins.get(lv, 0) + 1 / len(g['over'])
    names = {1: 'Easy', 2: 'Medium', 3: 'Hard', 4: 'HardLeg', 5: 'Hard+F', 6: 'Custom'}
    print('level   seats  win share')
    for lv in sorted(seats):
        w = wins.get(lv, 0); s = seats[lv]
        print(f'{names.get(int(lv), lv):7} {s:5}  {100*w/s:5.1f}%   (+-{100*1.96*(w/s*(1-w/s)/s)**.5:.1f}%)')
    # Mean final VP per level and mean VP margin over the best opponent: less noisy than win/loss, so small improvements show earlier.
    vps, mar = {}, {}
    for g in ok:
        for c, lv in g['seats'].items():
            mine = g['vp'][int(c)]; oth = max(g['vp'][int(d)] for d in g['seats'] if d != c)
            vps.setdefault(lv, []).append(mine); mar.setdefault(lv, []).append(mine - oth)
    for lv in sorted(vps):
        m = mar[lv]; mu = sum(m) / len(m); sd = (sum((x - mu) ** 2 for x in m) / max(1, len(m) - 1)) ** .5
        print(f'{names.get(int(lv), lv):7} avg VP {sum(vps[lv])/len(vps[lv]):.2f} | avg VP margin vs best opponent {mu:+.2f} (+-{1.96*sd/len(m)**.5:.2f})')
    print('rounds per game avg', round(sum(g['rounds'] for g in ok) / len(ok), 1))
    # Style metrics per level, over turns where AP >= 6 (enough budget for a real choice).
    for lv in sorted(seats):
        T = [t for g in ok for t in g['turns'] if t[0] == int(lv) and t[2] >= 6]
        if not T: continue
        ap = sum(t[2] for t in T)
        few = sum(1 for t in T if t[4] <= 2) / len(T)
        print(f'{names.get(int(lv), lv):7} turns(AP>=6) {len(T):4} | moves/turn {sum(t[4] for t in T)/len(T):.2f} | AP/move {sum(t[5] for t in T)/max(1,sum(t[4] for t in T)):.2f}'
              f' | AP in 4+ cost moves {100*sum(t[7] for t in T)/ap:.0f}% | turns with <=2 moves {100*few:.0f}% | AP unspent {100*sum(t[3] for t in T)/ap:.0f}%')
    P = [g['ps'] for g in ok if g.get('ps') and g['ps']['plans']]
    if P:
        t = {k: sum(p[k] for p in P) for k in P[0]}
        print(f"planner: {t['plans']/len(P):.0f} plans/game, {t['ms']/max(1,t['plans']):.0f} ms/plan, {t['rolls']/max(1,t['plans']):.1f} rollouts/plan, moves {t['exec']/len(P):.0f}/game, stale {t['stale']/len(P):.1f}, failed {t['failed']/len(P):.1f}, empty {t['empty']/len(P):.1f}, placed {t.get('pl',0)/len(P):.1f}/game, fleet moves {t.get('fm',0)/len(P):.1f}/game, place fails {t.get('xp',0)/len(P):.2f}, fleet-move fails {t.get('xf',0)/len(P):.2f}")
    for rd in (4, 6, 8, 10, 12):
        row = []
        for lv in sorted(seats):
            m = []
            for g in ok:
                snap = {r: v for r, v in g.get('rv', [])}
                if rd not in snap: continue
                for c, l in g['seats'].items():
                    if l == lv: m.append(snap[rd][int(c)] - max(snap[rd][int(d)] for d in g['seats'] if d != c))
            if len(m) > 5:
                mu = sum(m) / len(m); sd = (sum((x - mu) ** 2 for x in m) / (len(m) - 1)) ** .5
                row.append(f'{names.get(int(lv), lv)} {mu:+.2f} (+-{1.96*sd/len(m)**.5:.2f}, n={len(m)})')
        if row: print(f'VP margin after round {rd:2}: ' + ' | '.join(row))
    ks = [k for g in ok for k in g['kills']]
    print('eliminations/game', round(len(ks) / len(ok), 2), '| by round (avg):', round(sum(k[0] for k in ks) / max(1, len(ks)), 1))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default='constellate.html'); ap.add_argument('--n', type=int, default=4)
    ap.add_argument('--levels', default='3,3,3,3'); ap.add_argument('--games', type=int, default=20)
    ap.add_argument('--size', type=int, default=7); ap.add_argument('--seed0', type=int, default=1000)
    ap.add_argument('--out', default='res/run.jsonl'); ap.add_argument('--summary'); ap.add_argument('--check', action='store_true'); ap.add_argument('--set', action='append', default=[]); ap.add_argument('--verbose', action='store_true'); ap.add_argument('--planchk', action='store_true'); ap.add_argument('--plan', action='append', default=[]); ap.add_argument('--pc', action='append', default=[]); ap.add_argument('--fleet', action='append', default=[]); ap.add_argument('--pc6', action='append', default=[])
    a = ap.parse_args()
    if a.summary: summary(a.summary)
    else: run(a)
