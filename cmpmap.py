# cmpmap.py REF NEW "4:3,3:4" : like cmp.py, but first renames the CPU levels of REF (old:new) so runs from builds whose level numbers differ can be compared game by game (used at step 7, where Hard and Hard (legacy) swapped numbers).
import json,sys
mp={int(a):int(b) for a,b in (p.split(':') for p in sys.argv[3].split(','))} if len(sys.argv)>3 else {}
a=[json.loads(l) for l in open(sys.argv[1])]; b=[json.loads(l) for l in open(sys.argv[2])]
A={g['i']:g for g in a}; B={g['i']:g for g in b}; bad=0
def fix(g):
    t=[[mp.get(r[0],r[0])]+r[1:] for r in g['turns']]
    s=g['seats']; s=[mp.get(v,v) for v in s] if isinstance(s,list) else {k:mp.get(v,v) for k,v in s.items()}
    return t,s
for i in sorted(A):
    if i not in B: continue
    x,y=A[i],B[i]; tx,sx=fix(x)
    ok=all(x[k]==y[k] for k in ('vp','rounds','over','kills')) and tx==y['turns'] and sx==y['seats']
    if not ok: bad+=1; print('DIFF game',i)
print(f'{sys.argv[2]}: compared {len(set(A)&set(B))} games, {bad} different')
