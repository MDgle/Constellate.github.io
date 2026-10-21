import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import harness as H, scen
from playwright.sync_api import sync_playwright
name = sys.argv[1]; lv = int(sys.argv[2]); sc = scen.SCEN[name]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto('file://' + os.path.abspath('index.html')); pg.wait_for_timeout(300); pg.evaluate(H.HOOK)
    pg.evaluate('() => { cpuPlanCfg.dbg = true; }')
    r = scen.play(pg, sc, lv, 100)
    print(r['vp0'], '->', r['vp1'], r['mv'])
    rows = pg.evaluate('() => cpuPS.dbg || []')
    for x in rows[:16]: print(x)
    b.close()
