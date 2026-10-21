import sys,os
sys.path.insert(0,os.path.dirname(__file__))
import harness as H
from playwright.sync_api import sync_playwright
lv=int(sys.argv[1]); seed=int(sys.argv[2]); R=int(sys.argv[3])
JS="""([lv,seed,R]) => { cpuSeed=seed; const out=[]; const f=window.cpuDo;
 window.cpuDo=function(m){const ap0=G.ap,r=cur(),rd=G.round; const ok=f.apply(this,arguments); if(rd<=R&&r==0) out.push(`r${rd} ${m.t} a=${m.a.id}(${Math.floor(m.a.x)},${Math.floor(m.a.y)}) `+(m.t=='claim'?`->(${m.cx},${m.cy})`:`b=${m.b.id}`)+` cost ${ap0-G.ap}`); return ok;};
 cpuErr=null; cpuPlan=null; start(2,7,null,{0:lv,2:lv}); cpuAuto(300000); const vp=[]; return {out,rv:__log.rv.slice(0,R)} }"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+os.path.abspath('index.html')); pg.wait_for_timeout(300); pg.evaluate(H.HOOK)
    if lv==4: pg.evaluate("cpuPlanCfg.K=14")
    r=pg.evaluate(JS,[lv,seed,R]); print('\n'.join(r['out'])); print(r['rv'])
