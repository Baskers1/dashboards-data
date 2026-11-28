/* ---------- Neath Port Talbot specifics ---------- */
 var CFG={rng:"usual",land:"sea",exposed:"on the coast and the high ground",sceneOf:"the Neath Port Talbot coast and hills"};

/* Flood warnings: FLOODS.items = [{sev:1 severe|2 warning|3 alert, lvl, area, text, raised}] */
function vizFlood(){
  var h2=$("fl"),F=window.FLOODS,T=TN();if(!h2)return;
  var html,lv,lab,age=F?(Date.now()-F.asofMs)/36e5:0,box=slot("vz-ladder","",$("st-f")||h2);
  if(!F||!floodKnown()){html="Flood warning data is not available at the moment, so nothing can be said about "+esc(T.n)+". Check Natural Resources Wales.";lv=-1}
  else if(age>3){html="The flood data is "+hrs(age)+" old, so this page cannot say whether anything is in force. Please check Natural Resources Wales.";lv=-1}
  else{var act=floodActive();
    if(!act.length){lv=0;html="Nothing is in force: Natural Resources Wales has no flood alerts or warnings for Neath Port Talbot, checked "+lt(F.asofMs)+"."}
    else{lv=Math.max.apply(0,act.map(function(x){return 4-x.sev}));
      html="There "+(act.length===1?"is":"are")+" "+nOf(act.length,"flood notice")+" in force in Neath Port Talbot, the most serious being a "+SEVNAME[lv]+" ("+SEVMEAN[lv]+"): "+act.slice(0,3).map(function(x){return esc(x.area||x.lvl||"")}).join("; ")+(act.length>3?"; and "+(act.length-3)+" more":"")+"."}}
  story("f",h2,html);
  lab=lv===-1?"Flood data is out of date or missing, so no level can be shown":"Flood level ladder: none, alert, warning, severe. Current level for Neath Port Talbot: "+["none","alert","warning","severe"][lv];
  box.innerHTML=ladderSvg(lv,lab);
  vizOutlook(h2)}

/* Wales flood outlook: OUTLOOK = {issued, summary} */
 var OLV=["very low","low","medium","high"];
function vizOutlook(h2){
  var O=window.OUTLOOK,box=$("vz-olk");
  if(!O||!O.summary){var s=$("st-o");if(s)s.remove();if(box)box.innerHTML="";return}
  var m=/\bis\s+(very low|low|medium|high)\b/i.exec(O.summary),lv=m?OLV.indexOf(m[1].toLowerCase()):-1,iss=Date.parse(O.issued),h=isFinite(iss)?(Date.now()-iss)/36e5:null,html;
  html="Natural Resources Wales' flood outlook"+(isFinite(iss)?", issued "+ldt(iss)+(h>36?" ("+ago(iss)+", so it may be out of date)":"")+",":"")+" says: &ldquo;<span lang=\"en\" data-notx>"+esc(O.summary)+"</span>&rdquo; "+(lv>=0?"That is <strong>"+OLV[lv]+"</strong> on NRW's four-step scale (very low, low, medium, high). ":"This page could not read a level from that wording, so no step is highlighted. ")+"It covers Wales as a whole, not Neath Port Talbot alone.";
  var anchor=$("vz-ladder")||h2;
  story("o",anchor,html,"What the Wales outlook tells us");
  box=slot("vz-olk","",$("st-o"));
  box.innerHTML=ladderSvg(lv,lv<0?"Wales flood outlook: level not stated in the text":"Wales flood outlook scale: very low, low, medium, high. Current outlook: "+OLV[lv],["Very low","Low","Medium","High"]).replace('class="vz-ladder"','class="vz-ladder vz-olk"')}

/* Rivers: s = {r,n,lo,hi,v,vt,t,tr,trend} */
function nptItems(){
  return RIVERS.st.map(function(s){var v=s.v||[],now=v[v.length-1];if(now==null)return null;var tr=/^(rising|falling|steady)$/.test(s.trend||"")?s.trend:null;
    return{t:s.r,p:s.n,km:dist(LAT,LON,s.lat,s.lon),now:now,lo:s.lo,hi:s.hi,min:Math.min.apply(0,v),max:Math.max.apply(0,v),tr:tr,trTxt:tr?rvTrWord(tr)+", according to NRW's trend":"",tidal:/tidal/i.test(s.n),at:s.t}
  }).filter(Boolean).sort(function(a,b){return a.km-b.km})}
function vizRivers(){
  var h2=$("rl");if(!h2)return;var it=window.RIVERS&&RIVERS.st?nptItems():[];
  story("r",h2,rvStory(it,TN()));
  rvBlock(it,"Each bar is that gauge's own scale: the shaded middle is its usual range (where NRW data gives one), and the dot is the latest reading. The thin line shows readings collected over the last 24 hours. Tidal gauges move with the tide and have no usual range. Bars cannot be compared between gauges.")}

function vizAll(){safe("flood",vizFlood);safe("air",vizAir);safe("rivers",vizRivers);safe("weather",vizWeather)}
 var setTab0=window.setTab;
window.setTab=function(){setTab0.apply(this,arguments);vizAll()};
vizAll();
})();
