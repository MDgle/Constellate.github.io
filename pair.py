#!/usr/bin/env python3
"""pair.py CONTROL VARIANT... : paired per-game comparison (same seeds). Per game: mean over Custom(6) seats of (VP - best other VP) minus the same for Hard(3) seats.
Prints the variant-minus-control mean and 95% CI of that per-game difference, plus win-share and elimination change."""
import sys, json
def load(fn):
    d = {}
    for l in open(fn):
        if not l.strip(): continue
        g = json.loads(l)
        if g.get('over') is None or not g.get('rounds'): continue
        def m(lv):
            x = [g['vp'][int(c)] - max(g['vp'][int(o)] for o in g['seats'] if o != c) for c, v in g['seats'].items() if v == lv]
            return sum(x) / len(x)
        w = sum((1 / len(g['over'])) if int(c) in g['over'] else 0 for c, v in g['seats'].items() if v == 6) / 2
        e = sum(1 for k in g['kills'] if g['seats'].get(str(k[1])) == 6) / 2
        d[g['i']] = (m(6) - m(3), m(6), w, e)
    return d
C = load(sys.argv[1])
for fn in sys.argv[2:]:
    V = load(fn); ks = sorted(set(C) & set(V)); n = len(ks)
    for idx, name in ((0, 'seat diff'), (1, 'Custom margin'), (2, 'win share'), (3, 'elim/seat')):
        D = [V[k][idx] - C[k][idx] for k in ks]; mu = sum(D) / n; sd = (sum((x - mu) ** 2 for x in D) / (n - 1)) ** .5
        print(f"{fn.split('/')[-1][:-6]:8} n={n} {name:13} variant-control {mu:+.3f} (+-{1.96*sd/n**.5:.3f})", end=' | ' if idx < 3 else '\n')
