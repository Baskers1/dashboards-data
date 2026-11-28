/* Tayside (coastal): tides and bathing water, plus Tayside's own versions of four shared
   functions. Declared after the shared ones, so these are the versions the page uses:
   renderAir (Scottish Air Quality site pages give one reading, not 24 hours of history),
   drawWalks and wtile (walks filtered by starting area), renderGlance (next tide tile),
   setTab (tides, bathing water and SEPA floods). */
var TIDES={{BLOCK:TIDES}};
var TIDEST={{BLOCK:TIDEST}};
var BATHING={{BLOCK:BATHING}};
var AQL={{BLOCK:AQL}};
var TD;
function renderTideChart(){
 var el=$("tidechart"),n=nowLondon(),k0=iso(n),pts=[];
 function tm(t){return +t.slice(0,2)*60+ +t.slice(3,5)}
 [-1,0,1].forEach(function(dd){var r=TD[iso(new Date(n.getFullYear(),n.getMonth(),n.getDate()+dd))];if(!r)return;r.forEach(function(x){if(x[0]==="H"||x[0]==="L")pts.push([dd*1440+tm(x[1]),x[2],x[0],x[1]])})});
 if(pts.length<3||!TD[k0]){el.hidden=true;return}
 pts.sort(function(a,b){return a[0]-b[0]});
 var W=480,M=30,R=10,T=28,B=150,hm=Math.max(5,Math.ceil(Math.max.apply(0,pts.map(function(p){return p[1]}))));
 function X(m){return M+m/1440*(W-M-R)} function Y(h){return B-h/hm*(B-T)}
 function ht(m){for(var i=0;i<pts.length-1;i++)if(m>=pts[i][0]&&m<=pts[i+1][0]){var t=(m-pts[i][0])/(pts[i+1][0]-pts[i][0]);return pts[i][1]+(pts[i+1][1]-pts[i][1])*(1-Math.cos(Math.PI*t))/2}return null}
 var d="",m,v,on=0;for(m=0;m<=1440;m+=10){v=ht(m);if(v==null){on=0;continue}d+=(on?"L":"M")+X(m).toFixed(1)+" "+Y(v).toFixed(1)+" ";on=1}
 var o='<svg viewBox="0 0 '+W+' 200" xmlns="http://www.w3.org/2000/svg">',rs=TD[k0].filter(function(x){return x[0]==="R"||x[0]==="S"}).map(function(x){return tm(x[1])});
 if(rs.length===2)o+='<rect x="'+X(0)+'" y="'+T+'" width="'+(X(rs[0])-X(0))+'" height="'+(B-T)+'" fill="var(--line)" opacity=".45"/><rect x="'+X(rs[1])+'" y="'+T+'" width="'+(X(1440)-X(rs[1]))+'" height="'+(B-T)+'" fill="var(--line)" opacity=".45"/>';
 [0,2,4].forEach(function(h){o+='<line x1="'+M+'" x2="'+(W-R)+'" y1="'+Y(h)+'" y2="'+Y(h)+'" stroke="var(--line)" stroke-width=".6"/><text class="m" x="'+(M-4)+'" y="'+(Y(h)+3)+'" text-anchor="end">'+h+' m</text>'});
 for(var h=0;h<=24;h+=3)o+='<text class="m" x="'+X(h*60)+'" y="192" text-anchor="middle">'+(h<10?"0":"")+h%24+':00</text>';
 o+='<path d="'+d+' L'+X(1440)+' '+B+' L'+X(0)+' '+B+' Z" fill="var(--rain)" opacity=".18" stroke="none"/><path d="'+d+'" fill="none" stroke="var(--rain)" stroke-width="2.5" stroke-linejoin="round"/>';
 pts.forEach(function(p){if(p[0]<0||p[0]>1440)return;var hi=p[2]==="H",ax=X(p[0])>W-50?"end":X(p[0])<M+30?"start":"middle";o+='<circle cx="'+X(p[0])+'" cy="'+Y(p[1])+'" r="3.5" fill="var(--rain)"/><text x="'+X(p[0])+'" y="'+(hi?Y(p[1])-16:Y(p[1])+22)+'" text-anchor="'+ax+'" style="font-weight:700">'+(hi?"High ":"Low ")+p[3]+'</text><text class="m" x="'+X(p[0])+'" y="'+(hi?Y(p[1])-6:Y(p[1])+32)+'" text-anchor="'+ax+'">'+p[1].toFixed(1)+' m</text>'});
 var nm=n.getHours()*60+n.getMinutes();o+='<line x1="'+X(nm)+'" x2="'+X(nm)+'" y1="'+T+'" y2="'+B+'" stroke="var(--fg)" stroke-width="1.2" stroke-dasharray="2 2"/><text x="'+X(nm)+'" y="'+(B+12)+'" text-anchor="middle" style="font-weight:700">now</text>';
 el.innerHTML=o+'</svg>';el.hidden=false}
function renderTides(){
 var n=nowLondon(),o="",i,k,d,r,row;
 for(i=0;i<5;i++){d=new Date(n.getFullYear(),n.getMonth(),n.getDate()+i);k=iso(d);r=TD[k];
  if(!r){if(i===0)o="No tide times are loaded for today.";continue}
  row=r.filter(function(x){return x[0]==="H"||x[0]==="L"}).map(function(x){return '<span style="white-space:nowrap"><b>'+(x[0]==="H"?'▲ High':'▼ Low')+'</b> '+x[1]+' <span class="small">'+x[2].toFixed(2)+'m</span></span>'}).join(" &nbsp; ");
  var rs=r.filter(function(x){return x[0]==="R"||x[0]==="S"}).map(function(x){return x[1]});
  o+='<div style="padding:6px 0;border-top:'+(i?'1px solid var(--line)':'0')+'"><b>'+(i===0?"Today":fmt(k))+'</b> &nbsp;'+row+'<div class="small">Sunrise '+rs[0]+' · Sunset '+rs[1]+'</div></div>'}
 $("tides").innerHTML=o;renderTideChart()}
function renderBathing(){var B=BATHING[LOC.bw],el=$("bathing");
 var lv={Poor:1,Sufficient:2,Good:3,Excellent:4}[B.cls]||0,bars="";for(var i=1;i<=4;i++)bars+='<i'+(i<=lv?' class="on"':'')+'></i>';
 var o='<ul class="sans wq" style="list-style:none;margin:0;padding:0"><li><span><b>'+B.n+'</b><span class="small"> · grid ref '+B.grid+'</span></span><span class="r"><span class="rs" aria-hidden="true">'+bars+'</span><span class="tag Good">'+B.cls+'</span></span></li></ul>';
 o+='<p class="small" style="margin:6px 0 10px">SEPA classification awarded in '+B.yr+', worked out from four years of samples. Four bars = the official scale: Poor, Sufficient, Good, Excellent. This is a yearly classification, not a current reading.</p>';
 o+='<table class="tbl"><thead><tr><th>Sample date</th><th>E. coli (cfu/100ml)</th><th>Intestinal enterococci (cfu/100ml)</th></tr></thead><tbody>'+B.s.map(function(r){var hi=(+r[1].replace("<","")>500&&r[1].charAt(0)!=="<")||(+r[2].replace("<","")>200&&r[2].charAt(0)!=="<");return '<tr><td>'+r[0]+'</td><td>'+r[1]+'</td><td>'+r[2]+(hi?' <span class="flag" title="Above the single-sample marker SEPA uses">▲</span>':'')+'</td></tr>'}).join("")+'</tbody></table>';
 o+='<p class="small" style="margin:8px 0 0">Latest six samples listed by SEPA. ▲ = above the single-sample marker SEPA describes (over 500 E. coli or over 200 intestinal enterococci), which SEPA says indicates low quality at the time of sampling. Earlier classifications: '+B.h.map(function(h){return h[0]+" "+h[1]}).join(", ")+'. SEPA samples during the bathing season only, so no new results appear from autumn until the next season. Source: <a href="https://bathingwaters.sepa.org.uk/locations-and-results/results/?location='+B.id+'" target="_blank" rel="noopener">SEPA bathing waters, '+B.n+'</a> (UKAS-accredited laboratory results).</p>';
 el.innerHTML=o}
function renderAir(){var el=$("air"),A=AIR,o="";
 var sts=A.st.filter(function(s){return !s.tabs||s.tabs.indexOf(LOCK)>=0}).map(function(s){return{s:s,d:dist(LAT,LON,s.lat,s.lon)}}).sort(function(a,b){return a.d-b.d});
 var pick=function(s,re){for(var i=0;i<s.p.length;i++)if(re.test(s.p[i][0]))return s.p[i];return null};
 var cell=function(p){return p?p[2]+'<span class="u dq'+aqBand(p[1])+'">'+(p[1]?AQL[p[1]]+' '+p[1]:'No index')+'</span>':'-'};
 o+='<div class="small" style="margin-bottom:8px">Latest readings (Scottish Air Quality network and Defra UK-AIR): '+A.when+' UK time. Values are in µg/m³, nearest station first.</div><div class="tg"><table class="tbl aqt"><thead><tr><th scope="col">Station and overall index</th><th scope="col">PM2.5</th><th scope="col">PM10</th><th scope="col">NO₂</th></tr></thead><tbody>';
 sts.forEach(function(x){var s=x.s,mx=0;s.p.forEach(function(p){mx=Math.max(mx,p[1]||0)});
  o+='<tr><th scope="row" title="station '+s.id+', updated '+s.upd+'"><b>'+s.n+'</b><span class="small">'+s.type.toLowerCase()+', '+x.d.toFixed(1)+' km</span><span class="dq dq'+aqBand(mx)+'" style="margin-top:4px">'+(mx?'<i class="cd"></i>'+AQL[mx]+' '+mx:'n/a')+'</span></th><td>'+cell(pick(s,/PM2\.5/))+'</td><td>'+cell(pick(s,/PM10/))+'</td><td>'+cell(pick(s,/Nitrogen/))+'</td></tr>'});
 el.innerHTML=o+'</tbody></table></div>';
 $("airnote").innerHTML='<details class="about"><summary>About this data</summary><div class="small">Readings from the Scottish Air Quality website (<a href="https://www.scottishairquality.scot/latest/summary" target="_blank" rel="noopener">scottishairquality.scot</a>; data are provisional). When Defra UK-AIR (<a href="https://uk-air.defra.gov.uk" target="_blank" rel="noopener">uk-air.defra.gov.uk</a>) has a newer hourly reading for Dundee Mains Loan, that station shows nitrogen dioxide from Defra only. A station shows n/a and dashes when its newest reading is more than 3 hours old, for example while the Scottish Air Quality website is offline. There is no monitoring station in Carnoustie itself. The Carnoustie tab lists the nearest stations: the Dundee ones and Forfar, the closest in Angus. Distances are straight-line. Index is the UK Daily Air Quality Index as published by the network: 1-3 Low, 4-6 Moderate, 7-9 High, 10 Very High. Particle values are 24-hour means and nitrogen dioxide is the latest hourly mean.</div></details>'}
var WF="All",SF="All",KMAX=12,SA=["All","Dundee","Broughty Ferry","Fife","Angus"],WN=4,WALL=false;
function wtile(w){var a='fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"',wv='<path d="M10 56q6-6 12 0t12 0t12 0t12 0" '+a+'/>',b;
if(w.s=="Dundee"&&w.w)b=wv+'<path d="M10 42q6-6 12 0t12 0t12 0t12 0" '+a+'/>';
else if(w.s=="Dundee")b='<path d="M8 56L30 26 42 42 50 34 64 56Z" fill="var(--accent)" fill-opacity=".28" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round"/>';
else if(w.s=="Broughty Ferry")b='<circle cx="52" cy="22" r="7" fill="var(--sun)"/>'+wv+'<path d="M10 44q6-6 12 0t12 0t12 0t12 0" '+a+'/>';
else if(w.s=="Fife")b='<path d="M8 34H64M16 34V54M28 34V54M40 34V54M52 34V54" '+a+'/>'+'<path d="M10 62q6-5 12 0t12 0t12 0t12 0" '+a+'/>';
else if(w.s=="Angus")b='<path d="M8 46Q24 28 38 40T64 34" '+a+'/>'+wv;
else return "";
return '<div class="wt" aria-hidden="true"><svg viewBox="0 0 72 72" focusable="false">'+b+'</svg></div>'}
function drawWalks(){var fl=["All","Waterside","Easy","Medium"],set=WSETS[LOCK].map(function(k){return WALKS[k]});
 $("filters").innerHTML='<div class="small" style="width:100%">Starting from</div>'+SA.map(function(x){return '<button aria-pressed="'+(SF===x)+'" data-s="'+x+'">'+(x==="Fife"?"Fife (over the Tay Road Bridge)":x==="Angus"?"Angus coast":x)+'</button>'}).join("")+'<div class="small" style="width:100%">Type</div>'+fl.map(function(x){return '<button aria-pressed="'+(WF===x)+'" data-f="'+x+'">'+x+'</button>'}).join("");
 var vis=set.filter(function(w){return (SF==="All"||w.s===SF)&&(WF==="All"||(WF==="Waterside"&&w.w)||(WF==="Easy"&&w.d==="Easy")||(WF==="Medium"&&w.d==="Medium"))}),shown=WALL?vis:vis.slice(0,WN);
 $("walks").innerHTML=vis.length?shown.map(function(w){
  return '<article class="card walk">'+wtile(w)+'<div class="wbody"><h3>'+w.n+'</h3><div class="meta"><span>Starts: '+w.s+'</span><span>'+w.d+'</span><span>'+w.km+' km</span><span>'+w.h+'</span><span>'+(w.w?"Waterside":"Hill & parkland")+'</span></div><p>'+w.t+'</p><details class="more"><summary>Getting there and route notes</summary><p class="small"><b>Getting there:</b> '+w.get+'</p><p class="small"><b>Underfoot:</b> '+w.under+'</p>'+(w.u?'<p class="small"><b>More detail:</b> <a href="'+w.u[1]+'" target="_blank" rel="noopener">'+w.u[0]+'</a></p>':'')+'</details></div></article>'}).join("")+(vis.length>WN?'<button type="button" class="more" id="wmore" aria-expanded="'+WALL+'">'+(WALL?'Show fewer walks':'Show all '+vis.length+' walks')+'</button>':''):'<p class="small">No walks match these filters for '+LOC.name+'.</p>';
 document.querySelectorAll("[data-f]").forEach(function(b){b.onclick=function(){WF=b.dataset.f;WALL=false;drawWalks()}});
 document.querySelectorAll("[data-s]").forEach(function(b){b.onclick=function(){SF=b.dataset.s;WALL=false;drawWalks()}});
 var wm=$("wmore");if(wm)wm.onclick=function(){WALL=!WALL;drawWalks();if(!WALL)$("k").scrollIntoView()}}
function renderGlance(){var n=nowLondon(),h=n.getHours(),t=iso(n),nm=h*60+n.getMinutes(),T=[];
 var rows=(HOURLY&&HOURLY.date===t?HOURLY.rows:[]).filter(function(r){return +r[0].slice(0,2)>=h}),d0=DAILY.filter(function(x){return x.date>=t})[0]||{pop:0,gust:0};
 var pr=rows.length?rows.reduce(function(a,r){return r[2]>a[2]?r:a}):null,gr=rows.length?rows.reduce(function(a,r){return r[3]>a[3]?r:a}):null;
 T.push(["Now",BAKED_NOW.t+"°C",BAKED_NOW.phrase,""]);
 T.push(["Rain chance",(pr?pr[2]:d0.pop)+"%",pr?"highest left today, at "+pr[0]:"forecast for today",""]);
 T.push(["Strongest gusts",(gr?gr[3]:d0.gust)+" km/h",gr?"highest left today, at "+gr[0]:"forecast for today",""]);
 var nt=null,tm=function(x){return +x.slice(0,2)*60+ +x.slice(3,5)};
 [0,1].forEach(function(dd){var r=TD[iso(new Date(n.getFullYear(),n.getMonth(),n.getDate()+dd))];if(!r)return;r.forEach(function(x){if(!nt&&(x[0]==="H"||x[0]==="L")&&dd*1440+tm(x[1])>nm)nt=[x,dd]})});
 T.push(["Next tide",nt?(nt[0][0]==="H"?"High ":"Low ")+nt[0][1]:"n/a",nt?nt[0][2].toFixed(2)+" m"+(nt[1]?", tomorrow":""):"",""]);
 var st=AIR.st.filter(function(s){return !s.tabs||s.tabs.indexOf(LOCK)>=0}).map(function(s){return{s:s,d:dist(LAT,LON,s.lat,s.lon)}}).sort(function(a,b){return a.d-b.d})[0];
 if(st){var mx=0;st.s.p.forEach(function(p){mx=Math.max(mx,p[1]||0)});T.push(["Air quality",mx?AQL[mx]+" "+mx:"n/a","index at "+st.s.n,mx?"dq"+aqBand(mx):""])}
 $("glance").innerHTML='<h2 id="gh" class="vh">Right now</h2>'+T.map(function(x){return '<div class="g"><div class="gl">'+x[0]+'</div><div class="gv '+x[3]+'">'+x[1]+'</div><div class="gs">'+x[2]+'</div></div>'}).join("")}
function setTab(k){LOCK=k;LOC=LOCS[k];LAT=LOC.lat;LON=LOC.lon;BAKED_NOW=LOC.now;HOURLY=LOC.hourly;TD=TIDES[LOC.tide];var NOWX=!LOC.now||!LOC.baked.length;if(NOWX){BAKED_NOW={t:"–",e:"☁️",phrase:"Forecast loading",wind:"–",gust:"–",hum:"–",when:"not yet fetched"};HOURLY={date:"",rows:[]}}
 DAILY=LOC.baked.map(function(r){return{date:r[0],hi:r[1],lo:r[2],txt:r[3],pop:r[4],wind:r[5],gust:r[6],e:r[7]}});
 renderTabs();if(NOWX){DAILY=[];$("today").textContent=LOC.name+", "+COUNTY[LOCK];$("days").innerHTML="<p class=\"small\">The forecast for "+LOC.name+" has not been fetched yet. Air quality, rivers, flood warnings and walks below are already filled in.</p>";$("chart").innerHTML=""}else renderDays();renderNow({t:BAKED_NOW.t,e:BAKED_NOW.e,phrase:BAKED_NOW.phrase,wind:BAKED_NOW.wind,gust:BAKED_NOW.gust,hum:BAKED_NOW.hum},(LOC.live?"Live Open-Meteo conditions for ":"Open-Meteo conditions for ")+LOC.name+" at "+BAKED_NOW.when+".");
 var ts=TIDEST[LOC.tide],td=dist(LAT,LON,ts.lat,ts.lon);
 $("tidenote").innerHTML="High (H) and low (L) water for "+ts.name+(td>3?", the nearest location on the tide table site, about "+td.toFixed(0)+" km from "+LOC.name:"")+", with heights in metres and times adjusted for BST. Sunrise and sunset are shown for planning daylight. Tables: <a href=\"https://www.tidetimes.org.uk/"+ts.name.toLowerCase()+"-tide-times\" target=\"_blank\" rel=\"noopener\">tidetimes.org.uk</a> (not to be used for navigation). The curve is a smooth estimate drawn between the listed high and low waters, and shaded areas are night. Weather and wind can shift tide times and heights a little.";
 renderHero();renderHours();renderAir();renderTides();renderBathing();renderRivers();renderFloods();renderSpills();drawWalks();renderGlance();liveTown(k)}
