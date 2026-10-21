#!/usr/bin/env python3
"""ab.py FILE... : Custom(6) vs baseline (3) head-to-head summary: final VP margin, VP margin after rounds 6-10, win share, per file."""
import sys, json
def stat(x):
    n = len(x); mu = sum(x) / n; sd = (sum((v - mu) ** 2 for v in x) / max(1, n - 1)) ** .5; return mu, 1.96 * sd / n ** .5, n
for fn in sys.argv[1:]:
    G = [json.loads(l) for l in open(fn) if l.strip()]; G = [g for g in G if g.get('over') is not None and g.get('rounds')]
    fin, mid, win, el, hfin = [], [], [], 0, []
    for g in G:
        for c, lv in g['seats'].items():
            oth = [d for d in g['seats'] if d != c]
            if lv == 3: hfin.append(g['vp'][int(c)] - max(g['vp'][int(d)] for d in oth))
            if lv != 6: continue
            fin.append(g['vp'][int(c)] - max(g['vp'][int(d)] for d in oth))
            win.append((1 / len(g['over'])) if int(c) in g['over'] else 0)
            snap = {r: v for r, v in g.get('rv', [])}; m = [snap[r][int(c)] - max(snap[r][int(d)] for d in oth) for r in (6, 8, 10) if r in snap]
            if m: mid.append(sum(m) / len(m))
            if any(k[1] == int(c) for k in g['kills']): el += 1
    f, m, w = stat(fin), (stat(mid) if mid else (0, 0, 0)), sum(win) / len(win)
    d4 = f' | 4p diff vs Hard seats {f[0]-sum(hfin)/len(hfin):+.2f}' if len(G[0]['seats']) > 2 and hfin else ''
    print(f"{fn.split('/')[-1][:-6]:22} n={len(G):3} | Custom final margin {f[0]:+6.2f} (+-{f[1]:.2f}) | r6-10 margin {m[0]:+5.2f} (+-{m[1]:.2f}) | win {100*w:4.1f}% | eliminated {100*el/len(fin):.0f}%{d4}")
