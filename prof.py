import sys,os,json,collections
sys.path.insert(0,os.path.dirname(__file__))
import harness as H
from playwright.sync_api import sync_playwright
html=sys.argv[1]; n=int(sys.argv[2]); lv=[int(x) for x in sys.argv[3].split(',')]; games=int(sys.argv[4])
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+os.path.abspath(html)); pg.wait_for_timeout(300); pg.evaluate(H.HOOK)
    c=pg.context.new_cdp_session(pg); c.send('Profiler.enable'); c.send('Profiler.setSamplingInterval',{'interval':200}); c.send('Profiler.start')
    for i in range(games): pg.evaluate(H.PLAY,[n,lv[i%n:]+lv[:i%n],1000+i,7])
    prof=c.send('Profiler.stop')['profile']
nodes={x['id']:x for x in prof['nodes']}; self_t=collections.Counter()
dt=prof['timeDeltas']; 
for sid,d in zip(prof['samples'],dt): self_t[nodes[sid]['callFrame']['functionName'] or '(anon)']+=d
tot=sum(self_t.values())
for k,v in self_t.most_common(14): print(f'{100*v/tot:5.1f}%  {k}')
print('total ms',round(tot/1000))
par={}
for x in prof['nodes']:
    for ch in x.get('children',[]): par[ch]=x['id']
callers=collections.Counter()
for sid,d in zip(prof['samples'],dt):
    nm=nodes[sid]['callFrame']['functionName']
    if nm in ('dseg','clear'):
        q=par.get(sid); chain=[]
        while q and len(chain)<3: chain.append(nodes[q]['callFrame']['functionName'] or '(anon)'); q=par.get(q)
        callers[nm+' <- '+' < '.join(chain)]+=d
print('--- callers of dseg/clear')
for k,v in callers.most_common(8): print(f'{100*v/tot:5.1f}%  {k}')
