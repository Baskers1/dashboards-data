function rvSpark(v,lo,hi){if(!v||v.length<2)return "";var hasR=lo!=null&&hi!=null,mn=Math.min.apply(0,v),mx=Math.max.apply(0,v);if(hasR){mn=Math.min(lo,mn);mx=Math.max(hi,mx)}if(mx-mn<0.02){mn-=0.01;mx+=0.01}var pad=(mx-mn)*.06,a=mn-pad,b=mx+pad,W=260,H=40,Y=function(x){return H-2-(x-a)/(b-a)*(H-4)},d="";
 v.forEach(function(x,i){d+=(i?"L":"M")+(i*W/(v.length-1)).toFixed(1)+" "+Y(x).toFixed(1)+" "});
 return '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" role="img" aria-label="Level readings collected over the last 24 hours'+(hasR?' against the usual range':'')+'">'+(hasR?'<rect x="0" y="'+Y(hi).toFixed(1)+'" width="'+W+'" height="'+(Y(lo)-Y(hi)).toFixed(1)+'" fill="var(--chip)"/>':'')+'<path d="'+d+'" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>'}
var escH=function(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")};
function floodOk(x){return x&&typeof x==="object"&&!Array.isArray(x)&&x.sev>=1&&x.sev<=3}
function floodActive(){var it=FLOODS&&FLOODS.items;return Array.isArray(it)?it.filter(floodOk).sort(function(a,b){return a.sev-b.sev}):[]}
function floodKnown(){var it=FLOODS&&FLOODS.items;return Array.isArray(it)&&it.every(floodOk)}
function fmRaised(ms){var p={};new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",weekday:"short",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date(ms)).forEach(function(x){p[x.type]=x.value});return "raised "+p.hour+":"+p.minute+" "+p.weekday}
function floodList(FA){var ul=document.createElement("ul");ul.style.cssText="list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:8px";
 FA.forEach(function(x){var li=document.createElement("li"),l=document.createElement("b"),m=document.createElement("span"),t;l.className=x.sev===3?"Fair":"Poor";l.textContent=x.lvl||(x.sev===1?"Severe Flood Warning":x.sev===2?"Flood Warning":"Flood Alert");
  m.textContent=" "+(x.area||"")+(typeof x.raised==="number"&&isFinite(x.raised)?" · "+fmRaised(x.raised):"");m.style.fontWeight="600";li.appendChild(l);li.appendChild(m);
  if(x.text){t=document.createElement("div");t.className="small";t.textContent=x.text;li.appendChild(t)}ul.appendChild(li)});return ul}
function renderFloodTop(){var el=$("floodtop");if(!el)return;var FA=floodActive();
 if(!FA.length){el.hidden=true;el.innerHTML="";return}
 var warn=FA.some(function(x){return x.sev<3}),
  h=FA.length>1?"Natural Resources Wales flood alerts and warnings in force ("+FA.length+")":warn?"Natural Resources Wales flood warning in force":"Natural Resources Wales flood alert in force";
 el.innerHTML='<h2 id="fth">'+h+'</h2><div id="ftl"></div><p class="small">Covers Neath Port Talbot. NRW data checked '+fmMs(FLOODS.asofMs)+(Date.now()-FLOODS.asofMs>108e5?' <b>and now out of date, so check NRW</b>':'')+'. <a href="https://flood-warning.naturalresources.wales/?culture=en-GB" target="_blank" rel="noopener">NRW flood warnings and alerts</a> has the full detail and area maps. <a class="jl" href="#fl">Flood Warnings section on this page</a>.</p>';
 $("ftl").appendChild(floodList(FA));
 el.hidden=false;
 el.querySelectorAll(".jl").forEach(function(a){a.onclick=function(e){var t=$(a.getAttribute("href").slice(1));if(!t)return;e.preventDefault();t.scrollIntoView()}})}
function rvTrend(s){var t=String(s.trend||s.tr||"").toLowerCase(),a={rising:"\u2191",falling:"\u2193",steady:"\u2192"}[t];return a?'<div class="small"><span aria-hidden="true">'+a+'</span> Level '+t+'</div>':''}
function renderRivers(){var R=RIVERS,el=$("rivers");if(!el)return;
 var o="",st=R.st.filter(function(s){return s.v&&s.v.length}).sort(function(a,b){return dist(LAT,LON,a.lat,a.lon)-dist(LAT,LON,b.lat,b.lon)});
 st.forEach(function(s,ix){if(ix===3)o+='<details class="more"><summary>Show the other '+(st.length-3)+' stations</summary>';var v=s.v,now=v[v.length-1],mn=Math.min.apply(0,v),mx=Math.max.apply(0,v),hasR=s.lo!=null&&s.hi!=null,d=dist(LAT,LON,s.lat,s.lon),
  tag=hasR?(now<s.lo?"Below usual range":now>s.hi?"Above usual range":"Within usual range"):"";
  o+='<div class="rv"><div class="top"><div><b>'+escH(s.r)+', '+escH(s.n)+'</b><div class="small">'+d.toFixed(1)+' km from '+LOC.name+' · <a href="https://rivers-and-seas.naturalresources.wales/Station/'+s.id+'?parameterType=1" target="_blank" rel="noopener">NRW station '+s.id+'</a></div></div><div style="text-align:right"><span class="lv">'+now.toFixed(2)+' m</span><br>'+(tag?'<span class="tag '+(tag.charAt(0)==="W"?"Within":"Outside")+'">'+tag+'</span>':'')+rvTrend(s)+'</div></div>'+rvSpark(v,s.lo,s.hi)+'<div class="small">'+(hasR?'Usual range '+s.lo+'–'+s.hi+' m · ':'Usual range not published · ')+(v.length>1?'readings collected in the last 24 hours '+mn.toFixed(2)+'–'+mx.toFixed(2)+' m · ':'')+'reading at '+fmMs(s.t)+'</div></div>'});
 if(st.length>3)o+='</details>';el.innerHTML=o;
 var F=FLOODS,f=$("floods"),FA=floodActive(),p,n,O=typeof OUTLOOK==="object"&&OUTLOOK;f.textContent="";
 p=document.createElement("p");p.style.margin="0";
 if(FA.length){n=document.createElement("b");n.textContent="Flood alerts and warnings in force in Neath Port Talbot:";p.appendChild(n);f.appendChild(p);f.appendChild(floodList(FA))}
 else if(floodKnown()){n=document.createElement("b");n.textContent="No flood warnings or alerts in force in Neath Port Talbot.";p.appendChild(n);f.appendChild(p)}
 else{p.textContent="Flood warning data is not available at the moment. Check Natural Resources Wales.";f.appendChild(p)}
 p=document.createElement("p");p.className="small";p.style.margin="6px 0 0";p.textContent="Natural Resources Wales, checked "+fmMs(F.asofMs)+(Date.now()-F.asofMs>108e5?" and now out of date, so check NRW":"")+".";f.appendChild(p);
 if(O&&O.summary){p=document.createElement("p");p.style.cssText="margin:8px 0 0;font-size:.9rem";n=Date.parse(O.issued);p.textContent="Flood outlook (NRW, issued "+(isFinite(n)?fmMs(n):"date unknown")+"): ";var oq=document.createElement("span");oq.lang="en";oq.setAttribute("data-notx","");oq.textContent=O.summary;p.appendChild(oq);f.appendChild(p)}}