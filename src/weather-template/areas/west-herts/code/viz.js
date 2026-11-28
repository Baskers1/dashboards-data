/* ---------- West Herts specifics ---------- */
 var CFG={rng:"typical",land:"hills",exposed:"on open ground and the Chiltern ridges",sceneOf:"the Chilterns"};

/* Flood warnings: FLOODS.items = [[severity text, description]] */
function whFloodAct(){return(window.FLOODS&&FLOODS.items||[]).filter(function(x){return!/no longer in force/i.test(x[0])})}
function vizFlood(){
  var h2=$("fl"),F=window.FLOODS,T=TN();if(!h2)return;
  var html,lv,lab,age=F?(Date.now()-F.asofMs)/36e5:0,box=slot("vz-ladder","",$("st-f")||h2);
  if(!F||!Array.isArray(F.items)){html="Flood data is not in this copy of the page, so nothing can be said about the area. Use the GOV.UK Check for flooding link.";lv=-1}
  else if(age>3){html="The flood data is "+hrs(age)+" old, so this page cannot say whether anything is in force. Please check GOV.UK Check for flooding.";lv=-1}
  else{var act=whFloodAct();
    if(!act.length){lv=0;html="Nothing is in force: the Environment Agency has no flood alerts or warnings for the area this page covers (Tring to Watford and the Chilterns, not only "+esc(T.n)+"), checked "+lt(F.asofMs)+"."}
    else{lv=Math.max.apply(0,act.map(function(x){return sevLevel(x[0])}));
      html="There "+(act.length===1?"is":"are")+" "+nOf(act.length,"flood notice")+" in force across the area this page covers (Tring to Watford and the Chilterns, not only "+esc(T.n)+"), the most serious being a "+SEVNAME[lv]+" ("+SEVMEAN[lv]+"): "+act.slice(0,3).map(function(x){return esc(x[1])}).join("; ")+(act.length>3?"; and "+(act.length-3)+" more":"")+"."}}
  story("f",h2,html);
  lab=lv===-1?"Flood data is out of date or missing, so no level can be shown":"Flood level ladder: none, alert, warning, severe. Current level for the area: "+["none","alert","warning","severe"][lv];
  box.innerHTML=ladderSvg(lv,lab)}

/* Rivers */
function whItems(){
  return RIVERS.st.map(function(s){var v=s.v||[],now=v[v.length-1];if(now==null)return null;
    var w=s.hi-s.lo,thr=Math.max(.02,.03*(w>0?w:0)),d6=v.length>24?now-v[v.length-25]:null,d1=v.length>4?now-v[v.length-5]:null,tr=null,why="";
    if(d6!=null&&Math.abs(d6)>=thr){tr=d6>0?"rising":"falling";why=" over the last 6 hours"}
    else if(d1!=null&&Math.abs(d1)>=thr){tr=d1>0?"rising":"falling";why=" over the last hour"}
    else if(d6!=null){tr="steady";why=" over the last 6 hours"}
    return{t:s.r,p:s.n,km:dist(LAT,LON,s.lat,s.lon),now:now,lo:s.lo,hi:s.hi,min:Math.min.apply(0,v),max:Math.max.apply(0,v),tr:tr,trTxt:tr?rvTrWord(tr)+why:"",tidal:false,at:s.t}
  }).filter(Boolean).sort(function(a,b){return a.km-b.km})}
function vizRivers(){
  var h2=$("rl");if(!h2)return;var it=window.RIVERS&&RIVERS.st?whItems():[];
  story("r",h2,rvStory(it,TN()));
  rvBlock(it,"Each bar is that gauge's own scale: the shaded middle is its typical range, and the dot is the latest reading. The thin line shows where the level has been over the last 24 hours. Bars cannot be compared between gauges.")}

/* Sewage overflows: SPILLS.f = [Id, Status, start, end, lat, lon, watercourse] */
function spName(r){return(window.AREAS&&AREAS[r[0]])||"Overflow near "+r[4].toFixed(3)+", "+r[5].toFixed(3)}
function vizSewage(){
  var h2=$("sw"),T=TN();if(!h2||!window.SPILLS)return;
  var S=SPILLS,f=S.f||[],now=Date.now(),age=(now-S.asofMs)/36e5,km=function(r){return dist(LAT,LON,r[4],r[5])},
   on=f.filter(function(r){return r[1]===1}).sort(function(a,b){return km(a)-km(b)}),ok=f.filter(function(r){return r[1]===0&&r[3]}).sort(function(a,b){return b[3]-a[3]}),off=f.filter(function(r){return r[1]===-1}),html;
  if(!f.length)html="No storm overflows are listed in this data, so there is nothing to report here.";
  else{
    html=on.length?"<strong>"+nOf(on.length,"overflow")+" "+(on.length===1?"is":"are")+" discharging</strong> as of "+lt(S.asofMs)+", the nearest being "+esc(spName(on[0]))+" ("+km(on[0]).toFixed(1)+" km from "+esc(T.n)+"), since "+ldt(on[0][2])+".":"<strong>None of the "+f.length+" storm overflows in this data is discharging</strong> as of "+lt(S.asofMs)+".";
    if(ok.length){var r=ok[0];html+=" The most recent finished discharge ended "+ldt(r[3])+" ("+ago(r[3])+") at "+esc(spName(r))+", "+km(r).toFixed(1)+" km from "+esc(T.n)+"."}
    if(off.length)html+=" "+nOf(off.length,"overflow")+" "+(off.length>1?"are":"is")+" offline, so "+(off.length>1?"their":"its")+" status is unknown.";
    html+=" Thames Water says its monitors are sensitive and can be set off by things such as a weed moving in front of the sensor, so a reading indicates a discharge rather than confirming one"+(age>3?"; this copy of the data is "+hrs(age)+" old":"")+"."}
  story("s",h2,html);
  var box=slot("vz-tl","",$("st-s")),D30=2592e6,w0=now-D30,rows=[];
  f.forEach(function(r){if(r[1]===-1||!r[2])return;var end=r[1]===1?now:r[3];if(end&&end>w0)rows.push({n:spName(r),s:Math.max(r[2],w0),e:end,on:r[1]===1})});
  rows.sort(function(a,b){return b.e-a.e});var more=Math.max(0,rows.length-10);rows=rows.slice(0,10);
  if(!f.length){box.innerHTML="";return}
  var lab=rows.length?"Timeline of the last 30 days. "+nOf(rows.length+more,"overflow event")+" shown; latest ended "+ldt(rows[0].e)+".":"Timeline of the last 30 days: no discharges recorded.";
  var o='<h3 class="vz-h3">Discharges in the last 30 days</h3><div class="vz-tl" role="img" aria-label="'+esc(lab)+'">';
  if(!rows.length)o+='<div class="small">No overflow discharges are recorded in this data for the last 30 days.</div>';
  else{o+='<div class="vz-tr ax small" aria-hidden="true"><span></span><span class="vz-tt"><span>30 days ago</span><span>15</span><span>now</span></span></div>';
    rows.forEach(function(r){var l=(r.s-w0)/D30*100,w=Math.max((r.e-r.s)/D30*100,1);o+='<div class="vz-tr"><span class="vz-tn small">'+esc(r.n)+'</span><span class="vz-tt"><span class="z" style="width:'+(1728e5/D30*100).toFixed(1)+'%"></span><i class="'+(r.on?"on":r.e>now-1728e5?"r48":"old")+'" style="left:'+Math.min(l,99).toFixed(1)+'%;width:'+Math.min(w,100-Math.min(l,99)).toFixed(1)+'%"></i></span></div>'});
    o+='<div class="small" style="margin-top:6px">Red bar: discharging now. Amber: ended in the last 48 hours. Grey: older. The tinted end is the 48-hour window. Each overflow shows its latest event only, so earlier ones may be missing'+(more?'; '+more+' more not shown':'')+'.</div>'}
  box.innerHTML=o+'</div>'}

function vizAll(){safe("flood",vizFlood);safe("air",vizAir);safe("rivers",vizRivers);safe("sewage",vizSewage);safe("weather",vizWeather)}
 var setTab0=window.setTab;
window.setTab=function(){setTab0.apply(this,arguments);vizAll()};
vizAll();
})();
