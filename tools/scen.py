#!/usr/bin/env python3
"""scen.py - scenario tests for the CPU (step 9): hand-made positions, one CPU turn played, what it chose.
A scenario = {n, round, order, cpu:{color:level}, stars:{name:[color,sysx,sysy,fleets]}, conns:[[a,b],..], pool}. Capitals are named C<color>.
usage: python3 tools/scen.py show NAME | run NAME [--levels 3,4] [--seeds 10] [--set LV:KEY=VAL] [--pc KEY=VAL]"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
import harness as H
from playwright.sync_api import sync_playwright
from scen_defs import SCEN

BUILD = """([sc, lv, seed]) => {
  cpuSeed = seed; cpuErr = null; cpuPlan = null; __log.turns = []; __log.kills = [];
  cpuPS = {plans: 0, rolls: 0, ms: 0, exec: 0, stale: 0, failed: 0, empty: 0, pl: 0, fm: 0, xp: 0, xf: 0};
  const cpu = {}; sc.order.forEach(c => cpu[c] = (sc.cpu && sc.cpu[c] != null) ? sc.cpu[c] : lv);
  start(sc.n, 7, null, cpu);
  const byName = {}; G.stars.forEach(s => { if (s.cap) byName['C' + s.co] = s; });
  Object.entries(sc.stars).forEach(([nm, v]) => { const [c, x, y, f] = v; const s = {id: G.nid++, x: x + .5, y: y + .5, o: c, f: f || 0, fm: 0}; G.stars.push(s); byName[nm] = s; });
  (sc.moveCap || []).forEach(([c, x, y]) => { const s = byName['C' + c]; s.x = x + .5; s.y = y + .5; });
  G.conns = sc.conns.map(([a, b]) => [byName[a].id, byName[b].id]);
  G.round = sc.round; G.order = sc.order.slice(); G.ti = sc.ti || 0; G.first = G.order[0];
  (sc.dead || []).forEach(c => { G.alive[c] = false; });
  G.score = calc().vp.slice(); if (sc.score) sc.score.forEach((v, i) => { if (v != null) G.score[i] = v; });
  G.rank = rankSnap(G.score); G.over = null; undo = []; beginTurn(); if (sc.pool != null) G.pool = sc.pool; if (sc.ap != null) G.ap = sc.ap;
  window.__byName = byName; return true; }"""
PLAYT = """() => {
  const me = cur(), tid = G.round + ':' + G.ti, v0 = calc().vp.slice(), mv = [], f = window.cpuDo0 || (window.cpuDo0 = window.cpuDo);
  window.cpuDo = function (m) { const ap0 = G.ap, ok = f.apply(this, arguments); if (ap0 - G.ap > 0) { const nm = s => Object.keys(__byName).find(k => __byName[k] === s) || ('#' + s.id);
      mv.push((m.t == 'claim' ? 'claim from ' + nm(m.a) + ' to sys(' + m.cx + ',' + m.cy + ')' : m.t + ' ' + nm(m.a) + '->' + (m.b ? nm(m.b) : '?') + (m.y ? '+' + nm(m.y) : '')) + ' cost ' + (ap0 - G.ap)); } return ok; };
  const ap0 = G.ap, t0 = performance.now(); let n = 0;
  while (n++ < 400) { const r = cpuStep(); if (G.round + ':' + G.ti != tid || r == 'idle' || r == 'wait') break; }
  const ms = performance.now() - t0, v1 = calc().vp.slice(), t = __log.turns[__log.turns.length - 1] || [];
  return {me, ap: ap0, left: t[3], vp0: v0, vp1: v1, mv, ms, err: cpuErr}; }"""

def play(pg, sc, lv, seed):
    pg.evaluate(BUILD, [sc, lv, seed]); return pg.evaluate(PLAYT)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('name'); ap.add_argument('--levels', default='3'); ap.add_argument('--seeds', type=int, default=8)
    ap.add_argument('--set', action='append', default=[]); ap.add_argument('--pc', action='append', default=[]); ap.add_argument('--html', default='index.html'); ap.add_argument('-v', action='store_true')
    a = ap.parse_args(); sc = SCEN[a.name]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.goto('file://' + os.path.abspath(a.html)); pg.wait_for_timeout(300); pg.evaluate(H.HOOK)
        for x in a.pc: k, v = x.split('='); pg.evaluate('([k,v]) => { cpuPlanCfg[k] = v }', [k, float(v)])
        for x in a.set: lv, kv = x.split(':'); k, v = kv.split('='); pg.evaluate('([lv,k,v]) => cpuSet(lv, k, v)', [int(lv), k, float(v)])
        for lv in [int(x) for x in a.levels.split(',')]:
            R = [play(pg, sc, lv, 100 + s) for s in range(a.seeds)] if a.cmd == 'run' else [play(pg, sc, lv, 100)]
            me = R[0]['me']; sw = [r['vp1'][me] - r['vp0'][me] for r in R]; opp = sc.get('opp', [c for c in sc['order'] if c != me][0])
            gap = [(r['vp1'][me] - r['vp0'][me]) - (r['vp1'][opp] - r['vp0'][opp]) for r in R]
            print(f"level {lv}: AP {R[0]['ap']} | VP before {R[0]['vp0']} | own VP change avg {sum(sw)/len(sw):+.2f} | swing vs {opp} avg {sum(gap)/len(gap):+.2f} | AP left avg {sum((r['left'] or 0) for r in R)/len(R):.1f} | moves avg {sum(len(r['mv']) for r in R)/len(R):.1f} | ms/turn avg {sum(r['ms'] for r in R)/len(R):.0f} max {max(r['ms'] for r in R):.0f}")
            if a.cmd == 'show' or a.v:
                for r in R[:3 if a.v else 1]: print('   VP after', r['vp1'], '|', '; '.join(r['mv']), '| err', r['err'])
        b.close()
