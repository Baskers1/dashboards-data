"""Welsh gap finder for the Welsh weather boards (Ammanford, Neath Port Talbot).

    python3 tools/cy_gaps.py out/ammanford/index.html=A out/neath-port-talbot/index.html=N
    AT=2026-11-26T18:20:00Z python3 tools/cy_gaps.py ...   # browser clock at the data's own time

For every town tab it collects every text (and aria-label, alt, title) in English, presses
Cymraeg, collects again, and lists the texts that came out the same: the English the switch
leaves behind. Each is reported as the dictionary key(s) still missing (window.__cyKeys), with an
example. Walk descriptions are skipped (they stay English for now). Writes cy-gaps.json.
Needs playwright and Chrome (/usr/bin/google-chrome): run it in the cloud container, not the Mac.
Run it twice, once with AT set: a stale page hides the "right now" sentences.
Exit 1 if any page has a script error or any gap is left.
"""
import asyncio,json,os,re,sys
from playwright.async_api import async_playwright
COLLECT="""(WK)=>{const out=[];const A=['aria-label','alt','title'];
 const add=v=>{v=(v||'').replace(/\\s+/g,' ').trim();if(!v||!/[A-Za-z]{2}/.test(v))return;if(WK.indexOf(v.slice(0,40))>=0)return;out.push(v)};
 const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
 while(n=tw.nextNode()){const p=n.parentNode;if(!p||p.nodeName=='SCRIPT'||p.nodeName=='STYLE'||(p.closest&&p.closest('[data-notx]')))continue;add(n.nodeValue)}
 document.querySelectorAll('[aria-label],[alt],[title]').forEach(e=>{if(e.closest('[data-notx]'))return;A.forEach(a=>{const v=e.getAttribute(a);if(v)add(v)})});
 add(document.title);return out}"""
async def run(b,f):
    h=open(f,encoding="utf-8").read();i=h.index("var WALKS=");WK=h[i:h.index("\n",i)]
    p=await b.new_page(viewport={"width":390,"height":844});errs=[]
    p.on("pageerror",lambda e:errs.append(str(e)))
    await p.route(lambda u:u.startswith("http"),lambda r:r.abort())
    import os
    if os.environ.get("AT"): await p.clock.set_fixed_time(os.environ["AT"])
    await p.goto("file://"+os.path.abspath(f));await p.wait_for_timeout(400)
    tabs=await p.evaluate("TABS.map(function(t){return t[0]})");same={}
    for t in tabs:
        await p.evaluate("(k)=>{document.querySelector('[data-lang=en]').click();setTab(k)}",t);await p.wait_for_timeout(150)
        await p.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)")
        en=set(await p.evaluate(COLLECT,WK))
        await p.evaluate("()=>document.querySelector('[data-lang=cy]').click()");await p.wait_for_timeout(150)
        await p.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)")
        cy=await p.evaluate(COLLECT,WK)
        for s in cy:
            if s in en:
                for k in await p.evaluate("(s)=>window.__cyKeys(s)",s): same.setdefault(k,s)
    lang=await p.evaluate("document.documentElement.lang")
    await p.close();return same,errs,len(tabs),lang
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--allow-file-access-from-files"])
        allk={};any_err=[False]
        for f,tag in [a.split("=") for a in sys.argv[1:]]:
            K,errs,nt,lang=await run(b,f);any_err[0]=any_err[0] or bool(errs);print(tag,"tabs",nt,"errors",errs[:3],"lang at end",lang,"untranslated keys",len(K))
            for k,s in K.items(): allk.setdefault(k,{"b":"","ex":s});allk[k]["b"]+=tag
        json.dump(allk,open("cy-gaps.json","w"),ensure_ascii=False,indent=0)
        print("distinct",len(allk))
        for k,v in allk.items(): print(" ",v["b"],repr(k),"| e.g.",repr(v["ex"])[:120])
        bad=bool(allk) or any_err[0]
        await b.close()
        return 1 if bad else 0
sys.exit(asyncio.run(main()))
