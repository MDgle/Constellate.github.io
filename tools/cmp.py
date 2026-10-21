import json,sys
a=[json.loads(l) for l in open(sys.argv[1])]; b=[json.loads(l) for l in open(sys.argv[2])]
A={g['i']:g for g in a}; B={g['i']:g for g in b}
bad=0
for i in sorted(A):
    if i not in B: continue
    x,y=A[i],B[i]
    for k in ('vp','rounds','over','kills','turns','seats'):
        if x[k]!=y[k]: bad+=1; print('DIFF game',i,k); break
print(f'{sys.argv[2]}: compared {len(set(A)&set(B))} games, {bad} different')
