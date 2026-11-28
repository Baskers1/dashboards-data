
(function(){
"use strict";
 var $=function(i){return document.getElementById(i)};
function hf(s){return +s.slice(0,2)+ +s.slice(3,5)/60}
function p2(n){return(n<10?"0":"")+n}
function today(){return iso(nowLondon())}
function lt(ms){return new Date(ms).toLocaleTimeString("en-GB",{timeZone:"Europe/London",hour:"2-digit",minute:"2-digit"})}
function ld(ms){return new Date(ms).toLocaleDateString("en-GB",{timeZone:"Europe/London",weekday:"short",day:"numeric",month:"short"})}
function ldt(ms){return ld(ms)+", "+lt(ms)}
function hrs(n){n=Math.round(n);return n+(n===1?" hour":" hours")}
function ago(ms){var h=(Date.now()-ms)/36e5;return h<1?"less than an hour ago":h<48?hrs(h)+" ago":nOf(Math.round(h/24),"day")+" ago"}
function oldTxt(ms){var h=(Date.now()-ms)/36e5;return h>3?" (reading from "+lt(ms)+(ld(ms)!==ld(Date.now())?" on "+ld(ms):"")+", "+Math.round(h)+" h old)":""}
function snapAge(){var w=(window.HRS&&HRS.when)||"",m=/(\d+) (\w+), (\d\d):(\d\d)/.exec(w);if(!m)return null;var mi=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].indexOf(m[2]);if(mi<0)return null;var n=nowLondon(),d=new Date(n.getFullYear(),mi,+m[1],+m[3],+m[4]);if(d>n)d=new Date(n.getFullYear()-1,mi,+m[1],+m[3],+m[4]);return{h:(n-d)/36e5,w:w}}
function nOf(n,one,many){return n+" "+(n===1?one:many||one+"s")}
function mx(a,f){return a.reduce(function(b,x){return f(x)>f(b)?x:b})}
function slot(id,cls,ref,where){var e=$(id);if(!e&&ref){e=document.createElement("div");e.id=id;e.className=cls||"";ref.insertAdjacentElement(where||"afterend",e)}return e}
function sunT(){var r=TD()[today()],a,b;if(!r)return null;r.forEach(function(x){if(x[0]==="R")a=x[1];if(x[0]==="S")b=x[1]});return a&&b?{rise:hf(a),set:hf(b),rs:a,ss:b}:null}
function curRow(){if(!HRS||HRS.date!==today())return null;var h=nowLondon().getHours();return HRS.rows.filter(function(r){return+r[0].slice(0,2)===h})[0]||null}
function futRows(){if(!HRS||HRS.date!==today())return[];var h=nowLondon().getHours();return HRS.rows.filter(function(r){return+r[0].slice(0,2)>=h})}
function dirDeg(d){var i=CP.indexOf(d);return i<0?null:i*22.5}
function dirWord(d){var i=CP.indexOf(d);return i<0?"":CW[i]}

 var ICONS={
w:'<circle cx="8.5" cy="8.5" r="3.4"/><path d="M8.5 2v1.6M2 8.5h1.6M4 4l1.1 1.1M13 4l-1.1 1.1"/><path d="M8 21h9.5a3.6 3.6 0 0 0 .4-7.2A5.2 5.2 0 0 0 8 14.3 3.4 3.4 0 0 0 8 21z"/>',
f:'<path d="M3 9c2.2-2 3.8-2 6 0s3.8 2 6 0 3.8-2 6 0M3 15c2.2-2 3.8-2 6 0s3.8 2 6 0 3.8-2 6 0"/><path d="M12 3v3M10.5 4.5L12 3l1.5 1.5"/>',
a:'<path d="M3 8h10a3 3 0 1 0-3-3M3 13h15a3 3 0 1 1-3 3M3 18h7"/>',
t:'<path d="M3 16c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/><path d="M12 3v8M9 8l3 3 3-3"/>',
b:'<circle cx="16" cy="6" r="2"/><path d="M3 19c2-2 4-2 6 0s4 2 6 0 4-2 6 0M6 14l5-3 3 2.5 2.5-2.5"/>',
s:'<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
k:'<path d="M3 20l6-11 4 6 3-4 5 9z"/><circle cx="17" cy="6" r="2"/>'};
function story(key,after,html){
  var id="st-"+key,e=$(id);
  if(!e){e=document.createElement("div");e.id=id;e.className="story";
    e.innerHTML='<div class="story-hd"><svg class="story-ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+ICONS[key]+'</svg><span class="story-h">What this tells us</span></div><div class="story-t"></div>';
    after.insertAdjacentElement("afterend",e)}
  e.querySelector(".story-t").innerHTML=html}
function safe(name,f){try{f()}catch(err){if(window.console)console.error("[viz] "+name+": "+(err&&err.stack||err))}}

/* ---------- Weather ---------- */
function cloudWord(c){return c<15?"clear":c<40?"mostly clear":c<65?"partly cloudy":c<90?"mostly cloudy":"overcast"}
function weatherStory(){
  var T=TN(),n=nowLondon(),t=iso(n),cur=curRow(),fut=futRows(),d0=DAILY.filter(function(x){return x.date>=t})[0],s=[];
  if(!cur&&!d0)return"Forecast figures for "+esc(T.n)+" are not available right now.";
  if(!cur){
    return"Hour-by-hour detail is not available for today, but the daily forecast for "+esc(T.n)+" is a high of "+d0.hi+"°C and a low of "+d0.lo+"°C, with a "+d0.pop+"% chance of rain and gusts up to "+d0.gust+" km/h."}
  var fl=cur[9],ph=String(cur[7]||"").toLowerCase();
  s.push((ph?"It's "+esc(ph)+" in "+esc(T.n):"Conditions in "+esc(T.n))+" at "+cur[1]+"°C"+(fl!=null&&Math.abs(fl-cur[1])>=2?", but it feels more like "+fl+"°C":"")+".");
  if(fut.length){
    var pk=mx(fut,function(r){return r[2]}),first=fut.filter(function(r){return r[2]>=50})[0];
    s.push(first?"Rain looks likely "+(first[0]===cur[0]?"now":"from "+first[0])+" ("+first[2]+"% chance).":
      pk[2]>=30?"A shower is possible, with the chance peaking at "+pk[2]+"% around "+pk[0]+".":
      pk[2]>=10?"It should stay mostly dry, with a rain chance of at most "+pk[2]+"% (around "+pk[0]+").":
      "It should stay dry for the rest of today.");
    var gr=mx(fut,function(r){return r[3]}),g=gr[3],wd=cur[5]?dirWord(cur[5]):"";
    s.push("The wind is "+(wd?"from the "+wd+" ":"")+"at "+cur[4]+" km/h, with gusts reaching "+g+" km/h around "+gr[0]+(g>=45?", so it will feel blustery, especially "+(T.c?"by the water":"on open ground")+".":g>=35?", so it will feel breezy.":", so it stays fairly calm."))}
  var sa=snapAge();if(sa&&sa.h>3)s.push("This forecast snapshot is from "+esc(sa.w)+", "+Math.round(sa.h)+" h ago, so it may be out of date.");
  return s.join(" ")}
function emojiCloud(e){return e==="☀️"||e==="🌙"?5:e==="🌤️"||e==="⛅"?35:e==="☁️"||e==="🌫️"?90:e?90:null}
 var STARS=[[22,16],[48,40],[70,12],[96,30],[124,10],[150,44],[178,18],[204,34],[232,8],[258,26],[286,14],[312,40],[336,22],[60,64],[140,70],[268,58]];
 var CPOS=[[200,26,1.1,0],[40,36,1.25,0],[120,52,1.5,1],[270,58,1.15,1],[-6,70,1.4,2],[190,76,1.7,2]];
function sceneSvg(o){
  /* Painted-light scene: sky colour follows the sun's height, clouds are shaded puffs, the Moon shows its real phase, and land fades with distance. */
  var W=360,H=172,HZ=118,LAND=(o.inland?"dartmoor":"plymouth"),m=o.m,sn=o.sun,c=o.cloud==null?60:o.cloud,pop=o.pop||0,w=o.wind||0,rmm=o.rainMm||0,out="",i,j;
  function R(n){var x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x)}
  function hx(h){return[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)]}
  function mix(a,b,t){var A=hx(a),B=hx(b);t=t<0?0:t>1?1:t;return"#"+A.map(function(v,k){var x=Math.round(v+(B[k]-v)*t);return(x<16?"0":"")+x.toString(16)}).join("")}
  function f(v){return(+v).toFixed(1)}
  function ramp(T,x,k){for(var q=1;q<T.length;q++)if(x<=T[q][0]){var a=T[q-1],b=T[q];return mix(a[k],b[k],(x-a[0])/(b[0]-a[0]))}return T[T.length-1][k]}
  /* e: sun height proxy, -1 deep night .. 0 sunset .. .75 midday */
  var e=-1,sx=null,sy=null,mx=null,my=null,dd=typeof dirDeg==="function"?dirDeg(o.dir):null,wx=dd==null?1:(-Math.sin(dd*Math.PI/180)>=0?1:-1);
  if(sn){var r=sn.rise*60,se=sn.set*60;
    if(m>=r&&m<=se){var p=(m-r)/(se-r);e=Math.sin(Math.PI*p)*.75;sx=30+p*(W-60);sy=HZ-3-Math.sin(Math.PI*p)*88}
    else{var nl=1440-(se-r),q=m>se?(m-se)/nl:(m+1440-se)/nl;e=-Math.min(1,Math.sin(Math.PI*q)*1.7+.03);mx=30+q*(W-60);my=HZ-10-Math.sin(Math.PI*q)*80}}
  else e=(m>480&&m<1020)?.5:-1;
  var SK=[[-1,"#02050d","#060e24","#122040"],[-.35,"#050b20","#111c45","#2a3563"],[-.12,"#121a42","#36417c","#9a6c86"],[0,"#283a78","#9a7494","#f59c58"],[.12,"#3a6aae","#9cb6d4","#f6cd94"],[.35,"#2a70c0","#73abde","#c4e0f2"],[1,"#2166b6","#68a4da","#bcdaef"]];
  var ov=Math.min(.93,c/100*(.5+Math.min(pop,90)/180)+(rmm>0?.12:0)),lum=e>0?1-Math.max(0,.08-e)*1.5:Math.max(.07,.88+e*2.8),day=Math.max(0,Math.min(1,(e+.2)/.45));
  var grey=mix("#0b0f15",pop>=60?"#8f979f":"#b5bcc4",day),s0=mix(ramp(SK,e,1),grey,ov),s1=mix(ramp(SK,e,2),grey,ov*.95),s2=mix(ramp(SK,e,3),mix(grey,"#ffffff",.15*day),ov*.85);
  var sunC=mix("#ff8f45","#fff1cc",Math.min(1,Math.max(0,e/.3))),night=1-lum;
  function nt(col,k){return mix(col,"#04070c",night*(k==null?.86:k))}
  function haze(col,d){return mix(nt(col),s2,d)}
  var CT=[[-1,"#384156","#151a26"],[-.12,"#bd8090","#46415f"],[0,"#ffcfa8","#7d6a82"],[.15,"#fff1e2","#97a2b2"],[.4,"#ffffff","#a9b5c3"],[1,"#ffffff","#aab6c4"]];
  var wet=Math.min(1,Math.max(0,(pop-25)/60)+(rmm>0?.25:0)),ctop=mix(ramp(CT,e,1),mix("#9aa3ac","#2b3038",night),wet*.75),cbase=mix(ramp(CT,e,2),mix("#4b535c","#14181e",night),wet*.85);
  out='<svg class="vz-scene vs" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+String(o.label||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/"/g,"&quot;")+'" xmlns="http://www.w3.org/2000/svg"><defs>'+
   '<linearGradient id="vs-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+s0+'"/><stop offset=".62" stop-color="'+s1+'"/><stop offset="1" stop-color="'+s2+'"/></linearGradient>'+
   '<linearGradient id="vs-cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+ctop+'"/><stop offset=".55" stop-color="'+mix(ctop,cbase,.45)+'"/><stop offset="1" stop-color="'+cbase+'"/></linearGradient>'+
   '<linearGradient id="vs-deck" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+mix(cbase,"#000000",.15)+'"/><stop offset="1" stop-color="'+mix(ctop,cbase,.55)+'"/></linearGradient>'+
   '<radialGradient id="vs-sd" cx=".45" cy=".42"><stop offset="0" stop-color="#fffef6"/><stop offset=".7" stop-color="'+mix(sunC,"#ffffff",.5)+'"/><stop offset="1" stop-color="'+sunC+'"/></radialGradient>'+
   '<linearGradient id="vs-rs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+cbase+'" stop-opacity=".75"/><stop offset="1" stop-color="'+cbase+'" stop-opacity="0"/></linearGradient>'+
   '<linearGradient id="vs-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+mix(nt("#2f6f86",.8),s2,.45)+'"/><stop offset=".35" stop-color="'+mix(nt("#1d5468",.85),s1,.18)+'"/><stop offset="1" stop-color="'+nt("#0b2c3a",.8)+'"/></linearGradient>'+
   '<radialGradient id="vs-vig" cx=".5" cy=".45" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="'+(.18+night*.2).toFixed(2)+'"/></radialGradient>'+
   '<filter id="vs-b1" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1"/></filter>'+
   '<filter id="vs-b3" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'+
   '<filter id="vs-b8" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="8"/></filter>'+
   '<filter id="vs-b16" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="16"/></filter>'+
   '<clipPath id="vs-frame"><rect width="'+W+'" height="'+H+'"/></clipPath></defs><g clip-path="url(#vs-frame)">'+
   '<rect width="'+W+'" height="'+H+'" fill="url(#vs-sky)"/>';
  /* stars and a faint Milky Way */
  var sf=(1-ov)*Math.max(0,Math.min(1,(-e-.1)/.35));
  if(sf>.03){out+='<ellipse cx="200" cy="40" rx="190" ry="16" transform="rotate(-24 200 40)" fill="#c9d4ff" opacity="'+(sf*.09).toFixed(3)+'" filter="url(#vs-b8)"/>';
    for(i=0;i<96;i++){var sxs=R(i)*W,sys=Math.pow(R(i+97),1.35)*(HZ-6),srad=.3+Math.pow(R(i+7),4)*1.25;
      out+='<circle'+(i%3===0?' class="vs-tw" style="animation-delay:-'+f(R(i+3)*4)+'s"':'')+' cx="'+f(sxs)+'" cy="'+f(sys)+'" r="'+srad.toFixed(2)+'" fill="'+(i%7===0?"#ffe8c8":i%5===0?"#cfe0ff":"#ffffff")+'" opacity="'+(sf*(.45+R(i+11)*.55)*(1-sys/HZ*.55)).toFixed(2)+'"/>'}}
  /* the Moon, drawn in its real phase */
  if(mx!=null){var age=((Date.now()/864e5-10962.76)%29.530588853+29.530588853)%29.530588853,ph=age/29.530588853,kk=Math.cos(2*Math.PI*ph),RM=8.5,vis=1-ov*.8;
    var lit="M0 "+(-RM)+"A"+RM+" "+RM+" 0 0 1 0 "+RM+"A"+f(Math.abs(kk)*RM)+" "+RM+" 0 0 "+(kk>0?1:0)+" 0 "+(-RM)+"Z",ill=(1-kk)/2;
    out+='<circle cx="'+f(mx)+'" cy="'+f(my)+'" r="30" fill="#dfe6ff" opacity="'+(vis*(.12+ill*.3)).toFixed(2)+'" filter="url(#vs-b16)"/>'+
     '<g transform="translate('+f(mx)+' '+f(my)+') rotate(-18)'+(ph>.5?' scale(-1 1)':'')+'" opacity="'+vis.toFixed(2)+'"><circle r="'+RM+'" fill="'+mix(s0,"#3a4256",.5)+'" opacity=".55"/>'+      '<path d="'+lit+'" fill="#f3efe0"/><g fill="#8b8a80" opacity=".22"><ellipse cx="-2" cy="-3" rx="3" ry="2.2"/><ellipse cx="2.5" cy="1.5" rx="2.4" ry="1.8"/><ellipse cx="-1" cy="4" rx="1.6" ry="1.1"/></g>'+      '<path d="'+lit+'" fill="none" stroke="#ffffff" stroke-width=".5" opacity=".5"/></g>'}   /* the Sun, with a soft corona and a warm band on the horizon when it is low */   if(sx!=null){var dim=1-ov*.85;     if(e<.25)out+='<ellipse cx="'+f(sx)+'" cy="'+HZ+'" rx="170" ry="30" fill="'+sunC+'" opacity="'+((.25-e)*2.4*dim).toFixed(2)+'" filter="url(#vs-b16)"/>';     out+='<circle cx="'+f(sx)+'" cy="'+f(sy)+'" r="46" fill="'+sunC+'" opacity="'+(.32*dim+.06).toFixed(2)+'" filter="url(#vs-b16)"/>'+      '<circle class="vs-pulse" cx="'+f(sx)+'" cy="'+f(sy)+'" r="17" fill="'+mix(sunC,"#ffffff",.3)+'" opacity="'+(.6*dim).toFixed(2)+'" filter="url(#vs-b3)"/>'+      '<circle cx="'+f(sx)+'" cy="'+f(sy)+'" r="'+(e<.1?11:9.5)+'" fill="url(#vs-sd)" opacity="'+(ov>.8?.3:ov>.55?.65:1)+'"/>'}   /* thin high cirrus on part-cloudy days */   if(c>=12&&c<75){var ci=mix(ctop,s0,.3);for(i=0;i<3;i++){var cy0=14+i*13+R(i+40)*6,cx0=R(i+41)*200-20;     out+='<path d="M'+f(cx0)+' '+f(cy0)+'c30 -7 70 -9 120 -3s50 2 80 -4" fill="none" stroke="'+ci+'" stroke-width="'+(2.5+R(i+42)*2).toFixed(1)+'" stroke-linecap="round" opacity="'+(.32*day+.08).toFixed(2)+'" filter="url(#vs-b3)"/>'}}   /* an overcast deck with a lumpy base */   if(c>=62){var dk=(c-58)/42,yb=38+dk*44,d="M0 0H"+W+"V"+f(yb);for(i=12;i>=0;i--){var xx=i*30;d+="Q"+f(xx+15)+" "+f(yb+6+R(i+60)*9)+" "+xx+" "+f(yb+R(i+61)*4)}     out+='<path d="'+d+'Z" fill="url(#vs-deck)" opacity="'+Math.min(.96,dk*1.05).toFixed(2)+'" filter="url(#vs-b3)"/>'}   /* cumulus: each puff lit from above and shaded underneath; far ones small, hazy and low */   function cloud(x,y,s,seed,op,id){var n=5+Math.floor(R(seed)*3),g="",hl="",q,t;     for(q=0;q<n;q++){t=q/(n-1);g+='<circle cx="'+f(x+t*62*s)+'" cy="'+f(y-2*s-R(seed+q)*3*s)+'" r="'+f((6+R(seed+q+20)*4)*s)+'"/>'}     for(q=0;q<4;q++){t=.15+q*.23+R(seed+q+40)*.1;var cx=x+t*62*s,cy=y-(9+Math.sin(Math.PI*t)*9+R(seed+q+50)*4)*s,rr=(7+Math.sin(Math.PI*t)*7+R(seed+q+60)*3)*s;       g+='<circle cx="'+f(cx)+'" cy="'+f(cy)+'" r="'+f(rr)+'"/>';hl+='<circle cx="'+f(cx-rr*.25)+'" cy="'+f(cy-rr*.35)+'" r="'+f(rr*.55)+'"/>'}     return'<g class="vs-drift" style="animation-duration:'+(70-Math.min(w,50)+seed%20)+'s;animation-delay:-'+(seed%31)+'s" opacity="'+op.toFixed(2)+'"><linearGradient id="vs-cg'+id+'" gradientUnits="userSpaceOnUse" x1="0" y1="'+f(y-30*s)+'" x2="0" y2="'+f(y+3*s)+'"><stop offset="0" stop-color="'+ctop+'"/><stop offset=".5" stop-color="'+mix(ctop,cbase,.35)+'"/><stop offset="1" stop-color="'+cbase+'"/></linearGradient><clipPath id="vs-cc'+id+'"><rect x="'+f(x-30*s)+'" y="'+f(y-40*s)+'" width="'+f(124*s)+'" height="'+f(43*s)+'"/></clipPath>'+      '<ellipse cx="'+f(x+31*s)+'" cy="'+f(y+3*s)+'" rx="'+f(36*s)+'" ry="'+f(3.5*s)+'" fill="'+cbase+'" opacity=".45" filter="url(#vs-b3)"/><g filter="url(#vs-b1)"><g clip-path="url(#vs-cc'+id+')"><g fill="url(#vs-cg'+id+')">'+g+'</g><g fill="'+ctop+'" opacity="'+(.35*day+.1).toFixed(2)+'" filter="url(#vs-b3)">'+hl+'</g></g></g></g>'}   var dense=c>=85,nc=c<8?0:c<18?1:c<35?2:c<50?3:c<70?5:dense?3:6,CL=dense?[[20,96,.55],[150,104,.6],[270,92,.5]]:[[210,56,.95],[30,44,1.15],[120,70,.7],[280,80,.55],[-10,84,.5],[160,38,1.3],[300,46,1.05]];   for(i=0;i<nc;i++){var k=CL[i],far=k[1]>66;out+=cloud(k[0],k[1],k[2],i*13+5,dense?.8:far?.8:.97,i)}   /* rain curtains and streaks */   var RI=Math.min(1,Math.max(0,(pop-30)/60)+Math.min(rmm,4)/5);   if(RI>0){var sl=wx*(6+Math.min(w,50)/4);for(i=0;i<3;i++){var rx0=40+i*120+R(i+70)*40;       out+='<path d="M'+f(rx0)+' 58h'+f(36+R(i+71)*30)+'l'+f(sl)+' '+(HZ-58)+'h-'+f(52+R(i+72)*30)+'z" fill="url(#vs-rs)" opacity="'+(.35+RI*.4).toFixed(2)+'" filter="url(#vs-b8)"/>'}}   /* faint haze lying on the horizon */   out+='<rect y="'+(HZ-16)+'" width="'+W+'" height="22" fill="'+s2+'" opacity="'+(.25+ov*.35).toFixed(2)+'" filter="url(#vs-b3)"/>';   function ridge(y0,amp,seed,col,y1){var d="M-5 "+(y1||H)+"L-5 "+f(y0);for(var x=0;x<=W+10;x+=10){var y=y0-amp*(.55*Math.sin(x/53+seed)+.3*Math.sin(x/23+seed*2.1)+.15*Math.sin(x/9+seed*3.7));d+="L"+x+" "+f(y)}return'<path d="'+d+"L"+(W+10)+" "+(y1||H)+'Z" fill="'+col+'"/>'}   function sea(y0){var s='<rect y="'+y0+'" width="'+W+'" height="'+(H-y0)+'" fill="url(#vs-sea)"/>',wl=mix(nt("#9cc6d4",.8),s2,.3);     for(var q=0;q<15;q++){var t=q/14,yy=y0+1.5+Math.pow(t,1.7)*(H-y0-3),dl=2+t*15,d="";       for(var x=-10;x<W+10;x+=dl*2.4+R(q*31+x)*dl)d+="M"+f(x)+" "+f(yy+R(q+x)*1.2)+"h"+f(dl*(.5+R(x+q*7)));       s+='<path class="vs-swell" style="animation-duration:'+(5+q%4)+'s" d="'+d+'" stroke="'+wl+'" stroke-width="'+(.4+t*.9).toFixed(2)+'" stroke-linecap="round" opacity="'+(.18+t*.22).toFixed(2)+'"/>'}     var bx=sx!=null?sx:mx,by=sx!=null?sy:my;     if(bx!=null&&ov<.85){var gc=sx!=null?mix(sunC,"#ffffff",.35):"#eef2ff",ga=(1-ov)*(sx!=null?(e<.2?1:.75):.7);       s+='<ellipse cx="'+f(bx)+'" cy="'+f(y0+(H-y0)/2)+'" rx="'+(10+(H-y0)/3).toFixed(0)+'" ry="'+((H-y0)/2).toFixed(0)+'" fill="'+gc+'" opacity="'+(ga*.22).toFixed(2)+'" filter="url(#vs-b8)"/>';       for(q=0;q<40;q++){var t2=q/39,yy2=y0+1+Math.pow(t2,1.5)*(H-y0-2),gw=1+t2*9*R(q+90)+t2*2;         s+='<rect'+(q%2?' class="vs-glint" style="animation-delay:-'+f(R(q)*3)+'s"':'')+' x="'+f(bx-gw/2+(R(q+91)-.5)*(4+t2*34))+'" y="'+f(yy2)+'" width="'+f(gw)+'" height="'+(.6+t2*1.1).toFixed(2)+'" rx=".5" fill="'+gc+'" opacity="'+(ga*(.9-t2*.45)).toFixed(2)+'"/>'}}     var nwc=w<18?0:Math.min(16,Math.round((w-16)/3));     for(q=0;q<nwc;q++){var t3=.35+R(q+120)*.65,yy3=y0+2+Math.pow(t3,1.7)*(H-y0-4),ww=3+t3*9;       s+='<path d="M'+f(R(q+121)*W)+' '+f(yy3)+'q'+f(ww/2)+' '+f(-1.6*t3-.4)+' '+f(ww)+' 0" fill="none" stroke="'+mix("#ffffff",s2,.25+night*.6)+'" stroke-width="'+(.6+t3).toFixed(1)+'" stroke-linecap="round" opacity=".8"/>'}     return s+'<rect y="'+y0+'" width="'+W+'" height=".7" fill="'+mix(s2,"#ffffff",.3)+'" opacity=".6"/>'}   function tree(x,y,s,col,seed){var a=Math.min(w,60)/60*7*wx;return'<g class="vs-sway" style="--a:'+f(a)+'deg;animation-duration:'+(2.4+R(seed)*1.5).toFixed(1)+'s"><rect x="'+f(x-.9*s)+'" y="'+f(y-6*s)+'" width="'+f(1.8*s)+'" height="'+f(6.5*s)+'" fill="'+mix(col,"#000000",.35)+'"/><g fill="'+col+'"><ellipse cx="'+f(x)+'" cy="'+f(y-12*s)+'" rx="'+f(6.5*s)+'" ry="'+f(8*s)+'"/><ellipse cx="'+f(x-3.5*s)+'" cy="'+f(y-8*s)+'" rx="'+f(4.5*s)+'" ry="'+f(4.8*s)+'"/><ellipse cx="'+f(x+3.8*s)+'" cy="'+f(y-8.5*s)+'" rx="'+f(4.4*s)+'" ry="'+f(5*s)+'"/></g><ellipse cx="'+f(x-2*s)+'" cy="'+f(y-15*s)+'" rx="'+f(3*s)+'" ry="'+f(3.5*s)+'" fill="'+mix(col,"#ffffff",.15*lum)+'" opacity=".6"/></g>'}   function lamp(x,y,r){return night>.35?'<circle cx="'+f(x)+'" cy="'+f(y)+'" r="'+(r*4)+'" fill="#ffc46b" opacity="'+(night*.45).toFixed(2)+'" filter="url(#vs-b3)"/><circle cx="'+f(x)+'" cy="'+f(y)+'" r="'+r+'" fill="#ffd98f"/>':''}   function win(x,y,ww,hh,base){return'<rect x="'+f(x)+'" y="'+f(y)+'" width="'+ww+'" height="'+hh+'" fill="'+(night>.35?"#ffcf7a":mix(base,"#9fb6c8",.5))+'"/>'+(night>.35?'<rect x="'+f(x-2)+'" y="'+f(y-2)+'" width="'+(ww+4)+'" height="'+(hh+4)+'" fill="#ffb84d" opacity="'+(night*.35).toFixed(2)+'" filter="url(#vs-b3)"/>':'')}   function plume(x,y,col,n){var s="";for(var q=0;q<n;q++){s+='<circle cx="'+f(x+wx*q*(4+w/12))+'" cy="'+f(y-q*3.2)+'" r="'+f(2.4+q*1.3)+'" fill="'+col+'" opacity="'+Math.max(0,.6-q*.07).toFixed(2)+'"/>'}return'<g filter="url(#vs-b1)">'+s+'</g>'}   function turbine(x,y,h,col,seed){var sp=w<5?0:Math.max(1.2,9-w/7);return'<rect x="'+f(x-.5)+'" y="'+f(y-h)+'" width="1" height="'+h+'" fill="'+col+'"/><g transform="translate('+f(x)+' '+f(y-h)+')"><g'+(sp?' class="vs-spin" style="animation-duration:'+sp.toFixed(1)+'s;animation-delay:-'+f(R(seed)*3)+'s"':'')+'><circle r="'+(h*.55).toFixed(1)+'" fill="none"/>'+[0,120,240].map(function(a){return'<path transform="rotate('+(a+seed*17)+')" d="M-.5 0L0 -'+(h*.55).toFixed(1)+'L.6 0z" fill="'+col+'"/>'}).join("")+'</g><circle r=".9" fill="'+col+'"/></g>'}   var G=nt("#5d7f52"),G2=nt("#3f5f3a"),GF=haze("#6f8f8a",.62),GM=haze("#557a5a",.33),stone=nt("#8b8578"),dark=nt("#2b3238"),sand=nt("#cdb98e");   if(LAND==="ramsgate"){     out+=sea(HZ);     out+='<rect x="236" y="'+(HZ+20)+'" width="124" height="6" fill="'+nt("#0b2430")+'" opacity=".45" filter="url(#vs-b1)"/><path d="M236 '+(HZ+21)+'V'+(HZ+11)+'H360V'+(HZ+21)+'z" fill="'+nt("#5d6164")+'"/><rect x="236" y="'+(HZ+9)+'" width="124" height="3" fill="'+nt("#9a9c9a")+'"/><path d="M236 '+(HZ+16)+'H360" stroke="'+nt("#4b4f52")+'" stroke-width=".6"/>';     out+='<linearGradient id="vs-chalk" x1="0" x2="1"><stop offset="0" stop-color="'+nt("#ece6d5")+'"/><stop offset=".7" stop-color="'+nt("#cfc7b2")+'"/><stop offset="1" stop-color="'+nt("#a9a18e")+'"/></linearGradient>'+      '<path d="M0 '+H+'V100C24 98 46 100 62 104S88 122 98 '+H+'z" fill="url(#vs-chalk)"/><path d="M0 99C24 96 46 98 62 103L66 107C50 102 26 101 0 103z" fill="'+G+'"/>'+      '<path d="M10 106l3 50M27 104l-2 60M44 105l4 56M62 108l2 40" stroke="'+nt("#a59d89")+'" stroke-width=".8" opacity=".45"/><path d="M0 '+H+'V156C40 157 80 160 112 '+H+'z" fill="'+sand+'"/>';     var lx=330;out+='<path d="M'+(lx-6)+' '+(HZ+10)+'L'+(lx-4.5)+' 86h9L'+(lx+6)+' '+(HZ+10)+'z" fill="'+nt("#d9d2c0")+'"/><path d="M'+(lx-4.5)+' 86h9" stroke="'+dark+'" stroke-width="1.6"/><rect x="'+(lx-3.4)+'" y="77" width="6.8" height="8" fill="'+(night>.35?"#ffe39a":nt("#cfd8de"))+'" stroke="'+dark+'" stroke-width=".8"/><path d="M'+(lx-4.5)+' 77q4.5-6 9 0z" fill="'+dark+'"/>';     if(night>.35)out+='<path class="vs-beam" d="M'+lx+' 81L'+(lx-120)+' 66L'+(lx-120)+' 92z" fill="#ffe7a6" opacity=".18" filter="url(#vs-b3)"/>'+lamp(lx,81,2.2);     out+='<g fill="'+haze("#3a4048",.55)+'"><path d="M140 '+(HZ-4.5)+'h26l-2.5 4h-21.5z"/><rect x="145" y="'+(HZ-7.5)+'" width="8" height="3"/><rect x="147" y="'+(HZ-9.5)+'" width="4" height="2"/><rect x="158" y="'+(HZ-6.5)+'" width="1" height="2"/></g>'+(night>.35?lamp(153,HZ-9,.8):'')}   else if(LAND==="plymouth"){     out+=ridge(HZ-4,6,1.2,GF,HZ+2)+'<path d="M0 '+(HZ+1)+'V'+(HZ-14)+'C30 '+(HZ-24)+' 70 '+(HZ-20)+' 120 '+(HZ-6)+'L140 '+(HZ+1)+'z" fill="'+GM+'"/>'+sea(HZ)+      '<path d="M168 '+HZ+'q10-7 22 0z" fill="'+haze("#556b55",.4)+'"/>'+      '<path d="M226 '+H+'C250 140 300 134 360 132V'+H+'z" fill="'+G+'"/><path d="M226 '+H+'C260 150 310 146 360 146V'+H+'z" fill="'+G2+'"/>';     var tx=306,b="";for(i=0;i<5;i++)b+='<path d="M'+f(tx-6.2+i*.7)+' '+f(134-i*9)+'h'+f(12.4-i*1.4)+'l-.4 -4.5h'+f(-11.6+i*1.4)+'z" fill="'+nt("#b8352e",.8)+'"/>';     out+='<path d="M'+(tx-7)+' 136L'+(tx-3.4)+' 92h6.8L'+(tx+7)+' 136z" fill="'+nt("#efeae0",.8)+'"/>'+b+'<rect x="'+(tx-4.4)+'" y="89" width="8.8" height="3" fill="'+dark+'"/><rect x="'+(tx-2.8)+'" y="81" width="5.6" height="8" fill="'+(night>.35?"#ffe39a":nt("#cfd8de"))+'" stroke="'+dark+'" stroke-width=".7"/><path d="M'+(tx-3.6)+' 81q3.6-6 7.2 0z" fill="'+nt("#b8352e",.8)+'"/>'+(night>.35?lamp(tx,85,1.8):'')}   else if(LAND==="dartmoor"){     out+=ridge(HZ-14,7,.4,GF)+ridge(HZ-2,6,2.2,GM);     out+='<g fill="'+haze("#7d7a72",.3)+'"><rect x="268" y="'+(HZ-15)+'" width="14" height="7" rx="3"/><rect x="271" y="'+(HZ-21)+'" width="9" height="7" rx="3"/><rect x="284" y="'+(HZ-12)+'" width="11" height="6" rx="3"/><rect x="273" y="'+(HZ-26)+'" width="6" height="6" rx="2.5"/></g>';     out+=ridge(HZ+16,5,3.1,nt("#7b7a4c"))+(function(){var s='';for(var q=0;q<90;q++){var tq=q/89;s+='<rect x="'+f(tq*362-2)+'" y="'+f(HZ+29-Math.sin(tq*3.2)*4+R(q+530)*.8)+'" width="4.2" height="2.6" rx="1.1" fill="'+nt(q%3?"#77736a":"#8b867b")+'"/>'}return s})()+ridge(HZ+40,3,4.4,nt("#8a6a3a"))+tree(70,H-14,1.6,G2,3)+tree(40,H-6,1.1,G2,4)}   else if(LAND==="dundee"){     out+=ridge(HZ-3,5,.9,GF,HZ+1)+sea(HZ);     var bz=HZ+4,pts="";for(i=0;i<=26;i++){var bxp=60+i*12;pts+='<rect x="'+f(bxp-.8)+'" y="'+f(bz)+'" width="1.6" height="'+f(5+i*.15)+'" fill="'+haze("#3c4248",.25)+'"/>'}     out+='<path d="M60 '+bz+'H372" stroke="'+haze("#3c4248",.25)+'" stroke-width="2"/><path d="M60 '+(bz-2)+'H372" stroke="'+haze("#3c4248",.3)+'" stroke-width=".6"/>'+pts;     if(night>.35)for(i=0;i<9;i++)out+='<circle cx="'+(66+i*36)+'" cy="'+(bz-1)+'" r=".8" fill="#ffcf7a"/>';     out+='<path d="M0 '+H+'V112C14 106 26 96 40 95S62 104 80 112L96 '+H+'z" fill="'+G2+'"/><rect x="38.6" y="90" width="2.6" height="6" fill="'+dark+'"/>';     var bld="",hs=[[0,14],[9,20],[16,12],[26,26],[33,16],[44,22],[52,11],[60,18],[70,14],[80,24],[88,13],[98,17],[108,10],[116,15]];     hs.forEach(function(h,q){bld+='<rect x="'+h[0]+'" y="'+(H-22-h[1])+'" width="'+(q===3?7:9)+'" height="'+(h[1]+22)+'"/>'});     out+='<g fill="'+nt("#3f474e",.9)+'">'+bld+'<path d="M124 '+H+'V'+(H-24)+'l10-6 14 3 8 6V'+H+'z"/></g>';     for(i=0;i<(night>.35?28:0);i++)out+='<rect x="'+f(2+R(i+200)*150)+'" y="'+f(H-40+R(i+201)*32)+'" width="1.4" height="1.4" fill="#ffcf7a" opacity=".9"/>';     out+='<rect y="'+(H-6)+'" width="160" height="6" fill="'+nt("#2a3036")+'"/>'}   else if(LAND==="carnoustie"){     out+=sea(HZ);     out+=ridge(H-32,8,1.7,nt("#cdb987"))+ridge(H-20,7,2.9,nt("#7c9558"))+ridge(H-8,4,4.2,nt("#5d7a45"));     var fa=Math.min(w,50)/50,fx=250;     for(i=0;i<22;i++){var gx=R(i+300)*W,gy=H-12-R(i+301)*22;out+='<path class="vs-sway" style="--a:'+f(fa*12*wx)+'deg;animation-duration:'+(1.6+R(i)*1.2).toFixed(1)+'s" d="M'+f(gx)+' '+f(gy)+'q'+f(wx*2)+' -5 '+f(wx*(3+fa*4))+' -8M'+f(gx+1)+' '+f(gy)+'q0 -5 '+f(-wx*1.5)+' -9" fill="none" stroke="'+nt("#a59a5e")+'" stroke-width=".7"/>'}     out+='<rect x="'+fx+'" y="'+(H-52)+'" width="1" height="34" fill="'+nt("#e8e4d8")+'"/><path class="vs-flap" d="M'+(fx+(wx>0?1:0))+' '+(H-52)+'l'+f(wx*(9+fa*3))+' '+f(2.5+(1-fa)*2)+'l'+f(-wx*(9+fa*3))+' '+f(3.5-fa)+'z" fill="'+nt("#d4382f",.8)+'"/><ellipse cx="'+(fx+.5)+'" cy="'+(H-18)+'" rx="4" ry="1.2" fill="'+nt("#2c3a24")+'"/>'}   else if(LAND==="npt"){     out+='<path d="M0 '+(HZ+1)+'V'+(HZ-30)+'C40 '+(HZ-44)+' 80 '+(HZ-40)+' 130 '+(HZ-22)+'S190 '+(HZ-6)+' 214 '+(HZ+1)+'z" fill="'+GF+'"/>';     for(i=0;i<3;i++)out+=turbine(36+i*26,HZ-37+i*4,12,haze("#e8ecef",.35),i+1);     out+='<path d="M0 '+(HZ+1)+'V'+(HZ-14)+'C30 '+(HZ-22)+' 60 '+(HZ-18)+' 96 '+(HZ-6)+'L120 '+(HZ+1)+'z" fill="'+GM+'"/>'+sea(HZ);     var sw=haze("#4a4f55",.2);out+='<g fill="'+sw+'"><rect x="246" y="'+(HZ-18)+'" width="14" height="22"/><rect x="262" y="'+(HZ-26)+'" width="9" height="30"/><rect x="274" y="'+(HZ-12)+'" width="34" height="16"/><rect x="292" y="'+(HZ-44)+'" width="3.2" height="34"/><rect x="300" y="'+(HZ-38)+'" width="2.6" height="28"/><rect x="312" y="'+(HZ-16)+'" width="40" height="20"/><path d="M264 '+(HZ-26)+'l2.5-6 2.5 6z"/></g>';     out+=plume(293.6,HZ-46,mix("#e9edf0",s2,.4),8)+plume(301.3,HZ-40,mix("#e9edf0",s2,.4),6);     if(night>.35){out+=lamp(293.6,HZ-44,.8)+lamp(266,HZ-30,.8);for(i=0;i<10;i++)out+='<circle cx="'+f(248+R(i+400)*100)+'" cy="'+f(HZ-14+R(i+401)*14)+'" r=".7" fill="#ffcf7a"/>'}     out+='<path d="M0 '+H+'V'+(H-9)+'C100 '+(H-14)+' 240 '+(H-6)+' 360 '+(H-11)+'V'+H+'z" fill="'+sand+'"/>'}   else if(LAND==="chilterns"){     out+=ridge(HZ-16,6,.3,GF)+ridge(HZ-4,7,1.9,GM);     for(i=0;i<5;i++){var hx1=20+i*70+R(i+500)*24,hy1=HZ-9+R(i+501)*5,nb=5+Math.floor(R(i+502)*5);for(j=0;j<nb;j++)out+='<circle cx="'+f(hx1+j*3.4)+'" cy="'+f(hy1-Math.sin(Math.PI*j/(nb-1))*3-R(i*9+j)*1.5)+'" r="'+f(3+R(i*7+j)*1.6)+'" fill="'+haze("#3d5a3a",.36)+'"/>'}     out+=ridge(HZ+14,6,2.7,nt("#7ea05e"))+(function(){var s='';for(var q=0;q<110;q++){var tq=q/109,hx2=tq*360,hy2=HZ+20+Math.sin(tq*5+1)*4-tq*2;s+='<circle cx="'+f(hx2)+'" cy="'+f(hy2)+'" r="'+f(2.1+R(q+520)*1.1)+'" fill="'+G2+'"/>'}for(q=0;q<30;q++){var tq2=q/29;s+='<circle cx="'+f(118+tq2*30)+'" cy="'+f(HZ+14+tq2*(H-HZ-14))+'" r="'+f(1.8+tq2*2)+'" fill="'+G2+'"/>'}return s})()+ridge(H-14,4,3.9,G);     out+='<rect x="210" y="'+(HZ+5)+'" width="20" height="11" fill="'+nt("#d9cbb0")+'"/><path d="M207 '+(HZ+6)+'l13-9 13 9z" fill="'+nt("#7a4b38")+'"/><rect x="225" y="'+(HZ-5)+'" width="3" height="6" fill="'+nt("#7a4b38")+'"/>'+win(214,HZ+8,4,4,"#d9cbb0")+win(222,HZ+8,4,4,"#d9cbb0")+plume(226.5,HZ-7,mix("#dfe4e8",s2,.35),5);     out+=tree(40,H-6,1.9,G2,1)+tree(300,H-4,2.2,G2,2)+tree(330,H-10,1.3,G2,6)+tree(170,HZ+12,.8,GM,7)}   else{/* amman: Black Mountain scarp, the valley, a terrace of houses */     out+='<path d="M-5 '+(HZ+1)+'V'+(HZ-26)+'L60 '+(HZ-34)+'L150 '+(HZ-36)+'L190 '+(HZ-30)+'C220 '+(HZ-16)+' 250 '+(HZ-12)+' 365 '+(HZ-10)+'V'+(HZ+1)+'z" fill="'+GF+'"/>'+ridge(HZ+2,8,1.3,GM)+ridge(HZ+20,7,2.6,nt("#6f9058"));     for(i=0;i<9;i++){var hx0=170+i*15,hy=HZ+18-i*1.7,wall=nt(i%3===1?"#cfc6b4":i%3===2?"#b8b2a4":"#e1dccf");       out+='<rect x="'+f(hx0)+'" y="'+f(hy)+'" width="15" height="11" fill="'+wall+'"/><path d="M'+f(hx0-.5)+' '+f(hy)+'l8-5.5 8 5.5z" fill="'+nt("#4a5058")+'"/><rect x="'+f(hx0+9)+'" y="'+f(hy-7)+'" width="2" height="4" fill="'+nt("#4a5058")+'"/>'+win(hx0+3,hy+3,3,3,"#e1dccf")+win(hx0+9,hy+3,3,3,"#e1dccf")}     out+=ridge(H-12,4,4.1,G)+tree(40,H-6,1.8,G2,1)+tree(330,H-5,1.5,G2,2)+tree(120,HZ+22,.8,G2,5)}   /* falling rain over everything, then gust streaks and a gentle vignette */   if(RI>0){var nr=Math.round(18+RI*55),ddx=f(wx*(3+Math.min(w,50)/6));     for(i=0;i<nr;i++){var rx=R(i+600)*W,ry=50+R(i+601)*(H-60),ln=6+R(i+602)*6;       out+='<line class="vs-rain" x1="'+f(rx)+'" y1="'+f(ry)+'" x2="'+f(rx+wx*ln*.3)+'" y2="'+f(ry+ln)+'" stroke="'+mix("#d7e1ec",s2,.3)+'" stroke-width=".7" stroke-linecap="round" opacity="'+(.35+R(i+603)*.35).toFixed(2)+'" style="--dx:'+ddx+'px;animation-delay:-'+f(R(i+604)*.9)+'s"/>'}}   if(w>=30){for(i=0;i<Math.min(6,Math.round((w-24)/6));i++){var gy2=24+R(i+700)*70,gx2=R(i+701)*260;     out+='<path class="vs-gust" style="--wx:'+wx+';animation-duration:'+(2.4+R(i)*1.6).toFixed(1)+'s;animation-delay:-'+f(R(i+702)*3)+'s" d="M'+f(gx2)+' '+f(gy2)+'c20 -2 40 2 70 -1" fill="none" stroke="#ffffff" stroke-width=".7" stroke-linecap="round" opacity=".28"/>'}}   return out+'<rect width="'+W+'" height="'+H+'" fill="url(#vs-vig)"/></g></svg>'}
function sceneInfo(){
  var n=nowLondon(),cur=curRow(),d0=DAILY.filter(function(x){return x.date>=iso(n)})[0]||null,o={m:n.getHours()*60+n.getMinutes(),sun:sunT(),cloud:null,pop:null,wind:null,dir:"",rainMm:0,fromHour:!!cur,inland:!TN().c},txt;
  if(cur){o.cloud=cur[12];o.pop=cur[2];o.wind=cur[4];o.dir=cur[5];o.rainMm=cur[8]||0;txt=cloudWord(o.cloud)+" ("+o.cloud+"% cloud cover), "+cur[1]+"°C, "+o.pop+"% chance of rain, "+(o.dir?"wind from the "+dirWord(o.dir)+" ":"wind ")+o.wind+" km/h"}
  else if(d0){o.cloud=emojiCloud(d0.e);o.pop=d0.pop;o.wind=d0.wind;txt=(d0.txt||"daily forecast").toLowerCase()+", "+d0.pop+"% chance of rain, wind up to "+d0.wind+" km/h (daily forecast; hourly detail is not available)"}
  else txt="no forecast figures available";
  var sn=o.sun;
  o.label="Illustration of the sky over "+(o.inland?"the countryside":"Plymouth Sound")+" at "+p2(n.getHours())+":"+p2(n.getMinutes())+": "+txt+". "+(sn?(o.m>=sn.rise*60&&o.m<=sn.set*60?"The sun is up (sunrise "+sn.rs+", sunset "+sn.ss+").":"The sun is down (sunrise "+sn.rs+", sunset "+sn.ss+")."):"Sunrise and sunset times are not available.");
  return o}
function smooth(pts){var d="M"+pts[0][0].toFixed(1)+" "+pts[0][1].toFixed(1);for(var i=1;i<pts.length;i++){var a=pts[i-1],b=pts[i],mx_=(a[0]+b[0])/2;d+="C"+mx_.toFixed(1)+" "+a[1].toFixed(1)+" "+mx_.toFixed(1)+" "+b[1].toFixed(1)+" "+b[0].toFixed(1)+" "+b[1].toFixed(1)}return d}
function hourlyBlock(rows,sn){
  var W=720,M=34,R=10,cw=(W-M-R)/24,H=[],X=function(h){return M+h*cw},C=function(h){return X(h)+cw/2},K=[];
  rows.forEach(function(r){H[+r[0].slice(0,2)]=r});
  var ts=rows.map(function(r){return r[1]}),tmin=Math.floor(Math.min.apply(0,ts))-1,tmax=Math.ceil(Math.max.apply(0,ts))+1;if(tmax-tmin<6)tmax=tmin+6;
  var TY=[84,176],RY=[238,298],WYc=372,BOT=420,TH=446;
  var yT=function(v){return TY[1]-(v-tmin)/(tmax-tmin)*(TY[1]-TY[0])},yR=function(v){return RY[1]-v/100*(RY[1]-RY[0])};
  var n=nowLondon(),nx=HRS.date===iso(n)?X(n.getHours()+n.getMinutes()/60):null;
  /* text helper: also records an approximate box so the "now" line can stop short of it */
  function tx(x,y,t,an,cls,bold){t=String(t);var w=t.length*(bold?8.8:8.2)+4,l=an==="end"?x-w:an==="start"?x:x-w/2;K.push([l,l+w,y-15,y+4]);return'<text'+(cls?' class="'+cls+'"':'')+' x="'+(+x).toFixed(1)+'" y="'+y+'" text-anchor="'+an+'"'+(bold?' style="font-weight:700"':'')+'>'+t+'</text>'}
  var o='<svg viewBox="0 0 '+W+' '+TH+'" role="img" aria-label="LABEL" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="vz-tg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--sun);stop-opacity:.55"/><stop offset="1" style="stop-color:var(--sun);stop-opacity:.03"/></linearGradient><linearGradient id="vz-rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--rain);stop-opacity:.95"/><stop offset="1" style="stop-color:var(--rain);stop-opacity:.45"/></linearGradient></defs>';
  if(sn)o+='<rect x="'+X(0)+'" y="30" width="'+(X(sn.rise)-X(0))+'" height="'+(BOT-30)+'" fill="var(--nightshade)"/><rect x="'+X(sn.set)+'" y="30" width="'+(X(24)-X(sn.set))+'" height="'+(BOT-30)+'" fill="var(--nightshade)"/>';
  for(var h=0;h<24;h++)if(h%3===0){o+='<line x1="'+X(h)+'" x2="'+X(h)+'" y1="30" y2="'+BOT+'" stroke="var(--line)" stroke-width=".6"/>';if(nx==null||Math.abs(X(h)-nx)>30)o+=tx(X(h),TH-6,p2(h),"middle","m")}
  [tmin,Math.round((tmin+tmax)/2),tmax].forEach(function(v){o+='<line x1="'+M+'" x2="'+(W-R)+'" y1="'+yT(v).toFixed(1)+'" y2="'+yT(v).toFixed(1)+'" stroke="var(--line)" stroke-width=".5"/>'+tx(M-4,+(yT(v)+4).toFixed(1),v,"end","m")});
  [0,50,100].forEach(function(v){o+=tx(M-4,yR(v)+4,v,"end","m")});
  o+=tx(M+4,50,"Temperature °C","start","m")+tx(M+4,RY[0]-16,"Chance of rain %","start","m")+tx(M+4,WYc-40,"Wind km/h","start","m");
  var pts=[];for(h=0;h<24;h++)if(H[h])pts.push([C(h),yT(H[h][1])]);
  if(pts.length>1){var d=smooth(pts);o+='<path d="'+d+'L'+pts[pts.length-1][0].toFixed(1)+' '+(TY[1]+10)+'L'+pts[0][0].toFixed(1)+' '+(TY[1]+10)+'Z" fill="url(#vz-tg)"/><path d="'+d+'" fill="none" stroke="var(--sun)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'}
  for(h=0;h<24;h++){var r=H[h];if(!r)continue;
    if(h%3===0)o+='<circle cx="'+C(h)+'" cy="'+yT(r[1]).toFixed(1)+'" r="3.4" fill="var(--sun)" stroke="var(--card)" stroke-width="1.5"/>'+tx(C(h),+(yT(r[1])-12).toFixed(1),r[1]+"°","middle","",1)+tx(C(h),22,r[6],"middle","");
    var bh=Math.max(r[2]?2:0,r[2]/100*(RY[1]-RY[0]));
    o+='<rect x="'+(X(h)+4)+'" y="'+(RY[1]-bh)+'" width="'+(cw-8)+'" height="'+bh+'" rx="3" fill="url(#vz-rg)"/>';
    if(h%2===0)o+=tx(C(h),RY[1]+18,r[2],"middle","m");
    var wc=r[3]>=45?"var(--poor)":r[3]>=35?"var(--fair)":"var(--accent)",dg=r[5]?dirDeg(r[5]):null,L=5+Math.min(r[4],50)/50*9;
    if(dg!=null)o+='<g transform="translate('+C(h)+' '+WYc+') rotate('+(dg+180)+')" stroke="'+wc+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"><path d="M0 '+L+'V'+(-L)+'M-4.5 '+(-L+6)+'L0 '+(-L)+'L4.5 '+(-L+6)+'"/></g>';
    else o+='<circle cx="'+C(h)+'" cy="'+WYc+'" r="3" fill="'+wc+'"/>';
    if(h%3===0)o+=tx(C(h),WYc+36,r[4],"middle","",1)}
  if(nx!=null){var segs=[[30,BOT]];K.forEach(function(k){if(nx<k[0]-4||nx>k[1]+4)return;var ns=[];segs.forEach(function(g){if(k[3]+2<=g[0]||k[2]-2>=g[1]){ns.push(g);return}if(k[2]-2>g[0])ns.push([g[0],k[2]-2]);if(k[3]+2<g[1])ns.push([k[3]+2,g[1]])});segs=ns});
    segs.forEach(function(g){o+='<line x1="'+nx.toFixed(1)+'" x2="'+nx.toFixed(1)+'" y1="'+g[0]+'" y2="'+g[1]+'" stroke="var(--fg)" stroke-width="1.3" stroke-dasharray="3 3"/>'});
    o+='<text x="'+nx.toFixed(1)+'" y="'+(TH-6)+'" text-anchor="middle" style="font-weight:700">now</text>'}
  return{svg:o+'</svg>',nx:nx,W:W}}
function weekBlock(){
  var t=today(),list=DAILY.filter(function(x){return x.date>=t}).slice(0,7);if(!list.length)return"";
  var mn=Math.min.apply(0,list.map(function(x){return x.lo}))-1,mxv=Math.max.apply(0,list.map(function(x){return x.hi}))+1,span=mxv-mn,o="",wm=mx(list,function(x){return x.hi}),wet=mx(list,function(x){return x.pop});
  o+='<li class="ax" aria-hidden="true"><span></span><span></span><span class="lo">'+mn+'°</span><span style="display:flex;justify-content:space-between"><span>colder</span><span>warmer</span></span><span class="hi" style="color:var(--mute)">'+mxv+'°</span><span class="rn">rain</span></li>';
  list.forEach(function(x){var l=(x.lo-mn)/span*100,w=Math.max((x.hi-x.lo)/span*100,3);
    o+='<li><span class="d">'+(x.date===t?"Today":fmt(x.date))+'</span><span aria-hidden="true">'+x.e+'</span><span class="lo">'+x.lo+'°</span><span class="vz-trk" aria-hidden="true"><i style="left:'+l.toFixed(1)+'%;width:'+w.toFixed(1)+'%;background-size:'+(10000/w).toFixed(0)+'% 100%;background-position:'+(w>=100?0:l/(100-w)*100).toFixed(1)+'% 0"></i></span><span class="hi">'+x.hi+'°</span><span class="rn">'+x.pop+'%</span></li>'});
  return'<h3 class="vz-h3">The week at a glance</h3><div class="small">Low to high temperature for each day on one shared scale ('+mn+'° to '+mxv+'°). Warmest day: '+(wm.date===t?"today":fmt(wm.date))+' ('+wm.hi+'°). Highest rain chance: '+(wet.date===t?"today":fmt(wet.date))+' ('+wet.pop+'%).</div><ul class="vz-wk" aria-label="Seven-day temperature ranges">'+o+'</ul>'}
function vizWeather(){
  var h2=$("w");if(!h2)return;
  safe("weather story",function(){story("w",h2,weatherStory())});
  safe("scene",function(){var sc=slot("vz-scene-w","",$("wstamp"));var o=sceneInfo();sc.innerHTML=sceneSvg(o)+'<div class="small vz-cap" style="text-align:center">'+(o.sun?'Sunrise '+o.sun.rs+' · sunset '+o.sun.ss+'. The sun or moon is drawn where it is now; clouds, rain and wind follow the forecast for this hour; the Moon shows its real phase.':'Sunrise and sunset times are not available, so no sun or moon is drawn. Clouds, rain and wind follow the forecast.')+'</div>'});
  safe("hourly",function(){
    var old=$("hchart"),hs=$("hsum"),box=$("vz-hourly");
    if(!box){box=document.createElement("div");box.id="vz-hourly";hs.insertAdjacentElement("beforebegin",box);
      var det=document.createElement("details");det.className="more";det.id="vz-olddet";det.innerHTML='<summary>Detailed chart: humidity, cloud cover and feels-like</summary>';box.insertAdjacentElement("afterend",det);det.appendChild(hs);det.appendChild(old)}
    var t=today();
    if(!HRS||HRS.date!==t||!HRS.rows||HRS.rows.length<2){box.innerHTML="";return}
    var rows=HRS.rows,sn=sunT(),b=hourlyBlock(rows,sn),pk=mx(rows,function(r){return r[2]}),g=mx(rows,function(r){return r[3]}),hi=mx(rows,function(r){return r[1]}),lo=rows.reduce(function(a,r){return r[1]<a[1]?r:a});
    var sum="Today: high "+hi[1]+"°C at "+hi[0]+", low "+lo[1]+"°C at "+lo[0]+"; rain chance peaks at "+pk[2]+"% at "+pk[0]+"; strongest gusts "+g[3]+" km/h at "+g[0]+".";
    box.innerHTML='<h3 class="vz-h3">Hour by hour</h3><div class="small">'+esc(sum)+' Swipe sideways for the whole day; the grey bands are night.</div><div class="vz-scroll" id="vz-hs" tabindex="0" role="group" aria-label="Hour-by-hour chart, scrolls sideways">'+b.svg.replace("LABEL",esc("Hour-by-hour chart for today. "+sum))+'</div><div class="small vz-cap">Arrows point where the wind is blowing to; colour shows gusts: blue-green under 35 km/h, amber 35 to 44, red 45 or more. Figures are Open-Meteo model values.</div>';
    var sc=$("vz-hs"),sv=sc.querySelector("svg");
    if(b.nx!=null&&sv.clientWidth)sc.scrollLeft=Math.max(0,b.nx/b.W*sv.clientWidth-sc.clientWidth/3)});
  safe("week",function(){var e=slot("vz-week","",$("days"));e.innerHTML=weekBlock()});
  safe("walks",walksBadge)}
function walksBadge(){
  var h2=$("k");if(!h2)return;var t=today(),d0=DAILY.filter(function(x){return x.date>=t})[0],nx;
  if(!d0){story("k",h2,"Walking-weather figures are not available right now.");return}
  var r=rate(d0.pop,d0.gust),fu=futRows(),gu=d0.gust,pp=d0.pop,note="";
  if(d0.date===t&&fu.length){gu=mx(fu,function(x){return x[3]})[3];pp=mx(fu,function(x){return x[2]})[2];if(gu!==d0.gust||pp!==d0.pop)note=" The rating uses the whole day's peaks (rain chance "+d0.pop+"%, gusts "+d0.gust+" km/h)."}
  nx=DAILY.filter(function(x){return x.date>t&&rate(x.pop,x.gust)==="Good"})[0];
  story("k",h2,'Walking weather today in '+esc(TN().n)+': <span class="tag '+r+'">'+r+'</span> (from now to midnight: rain chance up to '+pp+'%, gusts up to '+gu+' km/h).'+note+' '+(r==="Good"?"Good news for a long one.":nx?"The next day rated Good is "+fmt(nx.date)+".":"No day in the forecast is rated Good yet."))}

/* ---------- Flood ---------- */
function floodState(){var F=window.FLOOD,T=TN();if(!F)return null;var age=(Date.now()-F.asofMs)/36e5,act=F.items.filter(function(r){return T.fa.indexOf(r[0])>=0&&r[2]<4}),top=act.reduce(function(a,r){return Math.min(a,r[2])},9);return{F:F,age:age,old:age>3,act:act,top:top}}
function ladderSvg(st){
  var lv=st.old?-1:st.act.length?(st.top===3?1:st.top===2?2:3):0,names=["None","Alert","Warning","Severe"],cols=["--good","--fair","--poor","--vh"],hs=[34,58,82,106],o="";
  for(var i=0;i<4;i++){var x=12+i*82,y=132-hs[i],on=i===lv;
    o+='<rect x="'+x+'" y="'+y+'" width="74" height="'+hs[i]+'" rx="8" fill="'+(on?"var("+cols[i]+")":"var(--chip)")+'" fill-opacity="'+(on?1:.9)+'" stroke="'+(on?"var("+cols[i]+")":"var(--line)")+'" stroke-width="'+(on?3:1.5)+'" '+(on?'class="vz-lit"':'')+(lv===-1?' stroke-dasharray="4 4"':'')+'/>'+
      '<text x="'+(x+37)+'" y="'+(y-6)+'" text-anchor="middle" '+(on?'style="font-weight:700"':'class="m"')+'>'+(on?"▶ ":"")+names[i]+'</text>'+(on?'<text x="'+(x+37)+'" y="'+(y+hs[i]/2+5)+'" text-anchor="middle" style="fill:var(--card);font-weight:700">NOW</text>':'')}
  var lab=lv===-1?"Flood data is out of date, so no level can be shown":"Flood level ladder: none, alert, warning, severe. Current level for "+TN().n+": "+names[lv].toLowerCase();
  return'<svg class="vz-ladder" viewBox="0 0 340 148" role="img" aria-label="'+esc(lab)+'" xmlns="http://www.w3.org/2000/svg">'+o+'</svg>'}
function gaugeSentence(){var T=TN(),F=window.FLOOD;if(!F||!T.g.length)return"";
  var out=T.g.map(function(ref){var g=GAUGES[ref],v=F.g&&F.g[ref];if(!v)return null;var pos=g.tidal?"on a tidal gauge, so it moves with the tide (gauge datum differs from tide-table heights)":v[1]<g.lo?"below its usual range":v[1]>g.hi?"above its usual range":"within its usual range";return esc(g.n)+" reads "+v[1].toFixed(2)+" m"+oldTxt(v[0])+", "+pos}).filter(Boolean);
  return out.length?" "+out.join("; ")+".":""}
function vizFlood(){
  var h2=$("fl"),T=TN(),st=floodState();if(!h2)return;
  var html;
  if(!st)html="Flood data is not in this copy of the page, so nothing can be said about "+esc(T.n)+". Use the Environment Agency link below.";
  else if(st.old)html="The flood data is "+hrs(st.age)+" old, so this page cannot say whether anything is in force for "+esc(T.n)+". Please check the Environment Agency link below.";
  else if(!st.act.length)html="Nothing is in force for "+esc(T.n)+": the Environment Agency has no flood alerts or warnings for "+esc(T.fc)+" (checked "+lt(st.F.asofMs)+")."+gaugeSentence();
  else{var s=SEV[st.top],means=st.top===1?"danger to life":st.top===2?"flooding is expected, so act now":"flooding is possible, so be prepared";
    html="There "+(st.act.length===1?"is":"are")+" "+nOf(st.act.length,"flood notice")+" in force for "+esc(T.n)+", the most serious being a "+esc(s[0].toLowerCase())+" ("+means+"): "+st.act.map(function(r){return esc(r[1])}).join("; ")+"."+gaugeSentence()}
  story("f",h2,html);
  var lad=slot("vz-ladder","",$("st-f"));lad.innerHTML=st?ladderSvg(st):"";
  var rv=slot("vz-rivers","",lad);rv.innerHTML=st?riverBlock():""}
function riverBlock(){
  var T=TN(),F=window.FLOOD;if(!F||!T.g.length||!F.g)return"";
  var rows=T.g.map(function(ref){var g=GAUGES[ref],v=F.g[ref];if(!g)return"";
    if(!v)return'<div class="vz-rv"><div class="vz-rh"><span class="vz-rn">'+esc(g.n)+'</span></div><div class="small">No reading in this copy of the page.</div></div>';
    var val=v[1],a=(Date.now()-v[0])/36e5,pct=Math.max(0,Math.min(100,val/g.max*100)),cls,word,band="";
    if(g.tidal){cls="t";word="Tidal gauge, so the level rises and falls with the tide"}
    else{var l=g.lo/g.max*100,w=(g.hi-g.lo)/g.max*100;band='<i class="bd" style="left:'+l.toFixed(1)+'%;width:'+w.toFixed(1)+'%"></i>';
      if(val<g.lo){cls="lo";word="Below its usual range"}else if(val>g.hi){cls="hi";word="Above its usual range"}else{cls="ok";word="Within its usual range"}}
    var rng=g.tidal?"":" Usual range "+g.lo+" to "+g.hi+" m.",lab=g.n+": "+val.toFixed(2)+" m. "+word+"."+rng+(g.tidal?" Gauge datum differs from tide-table heights.":"")+" Highest on record "+g.max+" m.";
    return'<div class="vz-rv"><div class="vz-rh"><span class="vz-rn">'+esc(g.n)+'</span><span class="vz-rval">'+val.toFixed(2)+' m</span></div><div class="vz-rt" role="img" aria-label="'+esc(lab)+'">'+band+'<i class="pin '+cls+'" style="left:'+pct.toFixed(1)+'%"></i></div><div class="vz-ra small" aria-hidden="true"><span>0 m</span><span>record '+g.max+' m</span></div><div class="small">'+word+(g.tidal?" (gauge datum differs from tide-table heights)":" ("+g.lo+" to "+g.hi+" m)")+'. Reading at '+lt(v[0])+(a>3?" <b>("+hrs(a)+" ago)</b>":"")+'.</div></div>'}).join("");
  return'<h3 class="vz-h3">How high are the rivers?</h3><div class="vz-rvs">'+rows+'</div><div class="small vz-cap">Each bar runs from 0 m to the highest level on record for that gauge. The shaded band is its usual range and the pin is the latest reading. This is one reading per gauge, so the page cannot say whether a level is rising or falling.</div>'}

/* ---------- Air ---------- */
 var ADV=[null,["Enjoy your usual outdoor activities.","Enjoy your usual outdoor activities."],["Enjoy your usual outdoor activities.","Adults and children with lung problems, and adults with heart problems, who experience symptoms, should consider reducing strenuous physical activity, particularly outdoors."],["Anyone experiencing discomfort such as sore eyes, cough or sore throat should consider reducing activity, particularly outdoors.","Adults and children with lung problems, and adults with heart problems, should reduce strenuous physical exertion, particularly outdoors, and particularly if they experience symptoms. People with asthma may find they need to use their reliever inhaler more often. Older people should also reduce physical exertion."],["Reduce physical exertion, particularly outdoors, especially if you experience symptoms such as cough or sore throat.","Adults and children with lung problems, adults with heart problems, and older people, should avoid strenuous physical activity. People with asthma may find they need to use their reliever inhaler more often."]];
 var PNAME={no2:"nitrogen dioxide",o3:"ozone",pm25:"fine particles (PM2.5)",pm10:"particles (PM10)"};
function sector(cx,cy,r0,r1,a0,a1){var P=function(r,a){var q=a*Math.PI/180;return(cx+r*Math.cos(q)).toFixed(1)+" "+(cy-r*Math.sin(q)).toFixed(1)};return"M"+P(r1,a0)+"A"+r1+" "+r1+" 0 0 1 "+P(r1,a1)+"L"+P(r0,a1)+"A"+r0+" "+r0+" 0 0 0 "+P(r0,a0)+"Z"}
function gaugeSvg(ov,label){
  var cx=150,cy=146,o="",cols=["","--good","--fair","--poor","--vh"];
  for(var i=1;i<=10;i++){var b=aqBand(i);o+='<path d="'+sector(cx,cy,98,132,180-(i-1)*18-.8,180-i*18+.8)+'" fill="var('+cols[b]+')" opacity="'+(ov&&i<=ov?1:.22)+'"/>'}
  if(ov){var a=(180-(ov-.5)*18)*Math.PI/180;o+='<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+86*Math.cos(a)).toFixed(1)+'" y2="'+(cy-86*Math.sin(a)).toFixed(1)+'" stroke="var(--fg)" stroke-width="3.5" stroke-linecap="round"/><circle cx="'+cx+'" cy="'+cy+'" r="7" fill="var(--fg)"/>'}
  o+='<text class="m" x="'+(cx-115)+'" y="'+(cy+16)+'" text-anchor="middle">1</text><text class="m" x="'+(cx+115)+'" y="'+(cy+16)+'" text-anchor="middle">10</text>';
  return'<svg class="vz-gauge" viewBox="0 0 300 166" role="img" aria-label="'+esc(label)+'" xmlns="http://www.w3.org/2000/svg">'+o+'</svg>'}
function vizAir(){
  var h2=$("aq"),A=window.AIR;if(!h2)return;
  var sts=airSt(),s0=sts[0],T=TN();
  if(!A||!s0){story("a",h2,"Air-quality readings are not available in this copy of the page.");var g0=$("vz-air");if(g0)g0.innerHTML="";return}
  var c=airCalc(s0),ov=airOv(c),age=(Date.now()-A.last)/36e5,html,gl;
  if(!ov){html="No usable air-quality reading is available from "+esc(s0.n)+" right now, so no index is shown.";gl="Air quality index not available"}
  else{
    var top=AQN.filter(function(p){return c[p[0]]&&c[p[0]].i===ov}).map(function(p){return PNAME[p[0]]}),band=aqBand(ov),miss=AQN.filter(function(p){return!s0[p[0]]}).map(function(p){return PNAME[p[0]]}),alt=sts.filter(function(x){return x!==s0&&AQN.every(function(p){return x[p[0]]})})[0],altOv=alt?airOv(airCalc(alt)):0;if(!altOv)alt=null;
    html="The air-quality index is <strong>"+ov+" out of 10 ("+AQLAB[ov]+")</strong> at "+esc(s0.n.replace(/ \(.*\)/,""))+(age>3?", though that reading is from "+lt(A.last)+" ("+Math.round(age)+" h old)":"")+(ov<=2?", and all pollutants are low. ":", and "+top.join(" and ")+" "+(top.length>1?"are":"is")+" setting the score. ")+(miss.length?"This station doesn't measure "+miss.join(" or ")+", so the index covers "+AQN.filter(function(p){return c[p[0]]}).map(function(p){return PNAME[p[0]]}).join(" and ")+" only"+(alt?"; "+esc(alt.n)+", "+alt.km+" km "+esc(alt.dir)+" of "+esc(T.n)+", measures all four and is at index "+altOv+" ("+AQLAB[altOv]+")":"")+". ":"")+(s0.km<1?"That station is in "+esc(T.n)+" itself.":"That station is about "+s0.km+" km "+esc(s0.dir)+" of "+esc(T.n)+", so treat this as a regional picture rather than "+esc(T.n)+" itself.")+
      '<div class="adv"><strong>Most people:</strong> '+ADV[band][0]+'</div><div class="adv"><strong>If you have asthma, or a heart or lung condition:</strong> '+ADV[band][1]+'</div><span class="cr">Health advice: Defra Daily Air Quality Index</span>';
    gl="Air quality index "+ov+" out of 10, "+AQLAB[ov]+", at "+s0.n.replace(/ \(.*\)/,"")+". "+AQN.map(function(p){var x=c[p[0]];return PNAME[p[0]]+": "+(x&&x.v!=null?"index "+x.i:x?"no reading":"not measured here")}).join("; ")}
  story("a",h2,html);
  var box=slot("vz-air","",$("st-a"));
  var pol=AQN.map(function(p){var x=c[p[0]],lab={no2:"NO₂",o3:"Ozone",pm25:"PM2.5",pm10:"PM10"}[p[0]];
    return x&&x.v!=null?'<li><span class="n">'+lab+'</span><span class="t" aria-hidden="true"><i class="b'+aqBand(x.i)+'" style="width:'+x.i*10+'%"></i></span><span class="v"><b>'+x.i+'</b> · '+Math.round(x.v)+' µg/m³</span></li>':'<li><span class="n">'+lab+'</span><span class="t" aria-hidden="true"></span><span class="v small">'+(x?"no reading":"not measured here")+'</span></li>'}).join("");
  box.innerHTML='<div class="vz-gwrap">'+gaugeSvg(ov,gl)+'<div class="vz-gv" aria-hidden="true"><b>'+(ov||"–")+'</b><span>'+(ov?AQLAB[ov]:"no reading")+'</span></div></div><div class="small vz-cap" style="text-align:center">Index 1 to 10 at '+esc(s0.n)+'. Bars below show each pollutant on the same 1 to 10 scale (ozone is an 8-hour mean, particles a 24-hour mean).</div><ul class="vz-pol" aria-label="Index for each pollutant">'+pol+'</ul>'}

/* ---------- Tides ---------- */
function tm(t){return+t.slice(0,2)*60+ +t.slice(3,5)}
function tidePts(){var n=nowLondon(),pts=[];[-1,0,1].forEach(function(dd){var r=TD()[iso(new Date(n.getFullYear(),n.getMonth(),n.getDate()+dd))];if(!r)return;r.forEach(function(x){if(x[0]==="H"||x[0]==="L")pts.push([dd*1440+tm(x[1]),x[2],x[0],x[1]])})});pts.sort(function(a,b){return a[0]-b[0]});return pts}
function untilTxt(m){return m<60?"in "+m+" min":"in "+Math.floor(m/60)+" h "+(m%60?m%60+" min":"")}
function vizTides(){
  var h2=$("t"),T=TN();if(!h2)return;
  if(!T.c){story("t",h2,esc(T.n)+" is inland, so there is no tide table of its own. Choose Plymouth or Plymstock above to follow the tide at Devonport.");return}
  var n=nowLondon(),nm=n.getHours()*60+n.getMinutes(),pts=tidePts();
  if(pts.length<3||!TD()[iso(n)]){story("t",h2,"Tide times for today are not available in this page's tables (they cover 2026 and 2027 only).");return}
  var nx=pts.filter(function(p){return p[0]>nm}),nH=nx.filter(function(p){return p[2]==="H"})[0],nL=nx.filter(function(p){return p[2]==="L"})[0],nxt=nx[0];
  var rising=nxt&&nxt[2]==="H",dayTxt=function(p){return p[0]>=1440?" tomorrow":""};
  var html="The tide is <strong>"+(nxt?(rising?"rising":"falling"):"changing")+"</strong> in "+esc(T.n)+" right now"+(nxt?", heading for "+(rising?"high":"low")+" water at "+nxt[3]+dayTxt(nxt)+" ("+nxt[1].toFixed(1)+" m), "+untilTxt(nxt[0]-nm)+".":".");
  var after=nx[1];if(after)html+=" "+(after[2]==="H"?"High":"Low")+" water follows at "+after[3]+dayTxt(after)+" ("+after[1].toFixed(1)+" m).";
  if(T.id!=="plymouth")html+=" These are Devonport's times and heights, so treat them as a guide for "+esc(T.n)+".";
  story("t",h2,html);
  var el=$("tidechart");if(!el)return;
  var W=360,M=30,R=10,TT=52,B=176,hm=Math.max(5,Math.ceil(Math.max.apply(0,pts.map(function(p){return p[1]})))),X=function(m){return M+m/1440*(W-M-R)},Y=function(h){return B-h/hm*(B-TT)};
  var ht=function(m){for(var i=0;i<pts.length-1;i++)if(m>=pts[i][0]&&m<=pts[i+1][0]){var t=(m-pts[i][0])/(pts[i+1][0]-pts[i][0]);return pts[i][1]+(pts[i+1][1]-pts[i][1])*(1-Math.cos(Math.PI*t))/2}return null};
  var d="",m,v,on=0;for(m=0;m<=1440;m+=10){v=ht(m);if(v==null){on=0;continue}d+=(on?"L":"M")+X(m).toFixed(1)+" "+Y(v).toFixed(1)+" ";on=1}
  var o='<svg viewBox="0 0 '+W+' 252" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="vz-wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--water-a);stop-opacity:.85"/><stop offset="1" style="stop-color:var(--water-b);stop-opacity:.5"/></linearGradient></defs>',sn=sunT();
  if(sn)o+='<rect x="'+X(0)+'" y="'+TT+'" width="'+(X(sn.rise*60)-X(0))+'" height="'+(B-TT)+'" fill="var(--nightshade)"/><rect x="'+X(sn.set*60)+'" y="'+TT+'" width="'+(X(1440)-X(sn.set*60))+'" height="'+(B-TT)+'" fill="var(--nightshade)"/>';
  [0,2,4].forEach(function(h){o+='<line x1="'+M+'" x2="'+(W-R)+'" y1="'+Y(h)+'" y2="'+Y(h)+'" stroke="var(--line)" stroke-width=".6"/><text class="m" x="'+(M-4)+'" y="'+(Y(h)+4)+'" text-anchor="end">'+h+' m</text>'});
  for(var h=0;h<24;h+=6)if(Math.abs(X(h*60)-X(nm))>30)o+='<text class="m" x="'+X(h*60)+'" y="246" text-anchor="middle">'+p2(h%24)+':00</text>';
  o+='<path d="'+d+'L'+X(1440)+' '+B+'L'+X(0)+' '+B+'Z" fill="url(#vz-wg)"/><path d="'+d+'" transform="translate(0 -4)" fill="none" stroke="var(--cl1)" stroke-width="1.4" opacity=".6" class="vz-shim"/><path d="'+d+'" fill="none" stroke="var(--rain)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>';
  var nxp=X(nm),taken=[],K=[],nz=[nxp-9,nxp+9];
  pts.forEach(function(p){if(p[0]<0||p[0]>1440)return;var hi=p[2]==="H",px=X(p[0]),py=Y(p[1]),w=((hi?"High ":"Low ").length+p[3].length)*8.8+4,best=null,cs=[["middle",px,px-w/2,px+w/2],["end",px-8,px-8-w,px-8],["start",px+8,px+8,px+8+w],["end",px-30,px-30-w,px-30],["start",px+30,px+30,px+30+w]];
    [1,0].forEach(function(strict){cs.forEach(function(c){if(best||c[2]<M+4||c[3]>W-R)return;if(taken.some(function(t){return c[2]<t[1]&&c[3]>t[0]}))return;if(strict&&c[2]<nz[1]&&c[3]>nz[0])return;best=c})});
    if(!best)best=cs[0];taken.push([best[2]-3,best[3]+3]);var ty=hi?py-24:py+24;K.push([best[2],best[3],ty-15,(hi?py-9:py+40)+4]);
    o+='<circle cx="'+px+'" cy="'+py+'" r="4" fill="var(--card)" stroke="var(--rain)" stroke-width="2.4"/><text x="'+best[1]+'" y="'+ty+'" text-anchor="'+best[0]+'" style="font-weight:700">'+(hi?"High ":"Low ")+p[3]+'</text><text class="m" x="'+best[1]+'" y="'+(hi?py-9:py+40)+'" text-anchor="'+best[0]+'">'+p[1].toFixed(1)+' m</text>'});
  var nv=ht(nm),segs=[[TT,B]];K.forEach(function(k){if(nxp<k[0]-3||nxp>k[1]+3)return;var ns=[];segs.forEach(function(g){if(k[3]+2<=g[0]||k[2]-2>=g[1]){ns.push(g);return}if(k[2]-2>g[0])ns.push([g[0],k[2]-2]);if(k[3]+2<g[1])ns.push([k[3]+2,g[1]])});segs=ns});
  segs.forEach(function(g){o+='<line x1="'+nxp+'" x2="'+nxp+'" y1="'+g[0]+'" y2="'+g[1]+'" stroke="var(--fg)" stroke-width="1.2" stroke-dasharray="2 3"/>'});o+='<text x="'+X(nm)+'" y="246" text-anchor="middle" style="font-weight:700">now</text>';
  if(nv!=null)o+='<circle class="vz-ring" cx="'+X(nm)+'" cy="'+Y(nv)+'" r="6" fill="none" stroke="var(--fg)" stroke-width="1.6"/><circle cx="'+X(nm)+'" cy="'+Y(nv)+'" r="5" fill="var(--fg)" stroke="var(--card)" stroke-width="2"/>';
  el.innerHTML=o+'</svg>';el.hidden=false;
  el.setAttribute("aria-label","Today's tide height curve for "+T.n+". "+(nxt?"The tide is "+(rising?"rising":"falling")+", next "+(rising?"high":"low")+" water at "+nxt[3]+" ("+nxt[1].toFixed(1)+" m). ":"")+pts.filter(function(p){return p[0]>=0&&p[0]<=1440}).map(function(p){return(p[2]==="H"?"High ":"Low ")+p[3]+" "+p[1].toFixed(1)+" m"}).join(", ")+".")}

/* ---------- Bathing and sewage ---------- */
function inSeason(){var n=nowLondon(),mo=n.getMonth()+1,d=n.getDate();return!(mo<5||mo>9||(mo===5&&d<15))}
function tidalW(r){return/SOUND|CHANNEL|BAY|HAMOAZE|ESTUAR|TIDAL|\((E|EST|C)\)/i.test(r[6])}
function seaSpills(){return spillsFor().filter(tidalW)}
function rainRecent(){if(!HRS||HRS.date!==today())return null;var h=nowLondon().getHours(),rs=HRS.rows.filter(function(r){return+r[0].slice(0,2)<=h&&r[8]!=null}),sum=0,mxh=0;rs.forEach(function(r){sum+=r[8];mxh=Math.max(mxh,r[8])});return{sum:sum,mxh:mxh,heavy:mxh>=4||sum>=10}}
function normName(s){return String(s).toLowerCase().replace(/[^a-z]/g,"")}
function beachTokens(b){var t=(b[0]+" "+(b[1]||"")).toLowerCase().split(/[^a-z]+/);return t.filter(function(w){return w.length>=4&&["beach","rated","nearest","estuary","coastguards","north","south","east","west","mouth","with","bay","firestone"].indexOf(w)<0})}
function verdicts(){
  var T=TN(),now=Date.now(),H48=1728e5,S=SPILLS,sea=seaSpills(),rr=rainRecent(),sage=(now-S.asofMs)/36e5,res=[];
  T.bw.forEach(function(b){
    var cls=BWD[b[0]],lab=["","Poor","Sufficient","Good","Excellent"][cls]||"",tk=beachTokens(b),lv=0,why=[],notes=[];
    var own=beachTokens([b[0]]),near=SPILLS.f.filter(function(r){var a=((AREAS[r[0]]||"")+" "+r[6]).toLowerCase();return own.some(function(w){return a.indexOf(w)>=0})||(tidalW(r)&&tk.some(function(w){return a.indexOf(w)>=0}))}),other=T.c?sea.filter(function(r){return near.indexOf(r)<0}):[];
    var nm=function(r){return"the “"+esc(AREAS[r[0]]||tcase(r[6]))+"” overflow"};
    var raise=function(l,t){if(l>lv)lv=l;why.push([l,t])};
    var on=near.filter(function(r){return r[1]===1}),rec=near.filter(function(r){return r[1]===0&&r[3]>now-H48}),off=near.filter(function(r){return r[1]===-1});
    if(on.length)raise(2,nm(on[0])+" has been discharging since "+lt(on[0][2])+(ld(on[0][2])!==ld(now)?" on "+ld(on[0][2]):"")+", "+hv(T.lat,T.lon,on[0][4],on[0][5]).toFixed(1)+" km from the "+esc(T.n)+" centre");
    if(cls===1)raise(2,"it is classed Poor for 2025");
    if(rec.length)raise(1,nm(rec[0])+" finished discharging on "+ldt(rec[0][3])+", within the last 48 hours");
    if(off.length)raise(1,nm(off[0])+" is offline, so its status is unknown");
    var ooff=other.filter(function(r){return r[1]===-1});if(ooff.length)raise(1,nOf(ooff.length,"tidal-water overflow")+" near "+esc(T.n)+" "+(ooff.length>1?"are":"is")+" offline, so "+(ooff.length>1?"their":"its")+" status is unknown");
    var oon=other.filter(function(r){return r[1]===1}),orc=other.filter(function(r){return r[1]===0&&r[3]>now-H48});
    if(oon.length)raise(1,nOf(oon.length,"other tidal-water overflow")+" near "+esc(T.n)+" "+(oon.length>1?"are":"is")+" discharging now (beach coordinates are not in the data, so I cannot say how close)");
    else if(orc.length)raise(1,nOf(orc.length,"other tidal-water overflow")+" near "+esc(T.n)+" discharged within the last 48 hours (beach coordinates are not in the data, so I cannot say how close)");
    if(rr&&rr.heavy)raise(1,"heavy rain in today's data ("+rr.sum.toFixed(1)+" mm so far)");
    if(cls===2)raise(1,"it is classed Sufficient for 2025, the lowest passing grade");
    if(sage>3)raise(1,"the overflow data is "+(sage>168?nOf(Math.round(sage/24),"day"):hrs(sage))+" old");
    var top=why.filter(function(w){return w[0]===lv}).map(function(w){return w[1]});
    var reason=lv===0?(near.length?"Rated "+lab+" for 2025, with no discharge in the last 48 hours from the "+nOf(near.length,"overflow")+" the data names for this beach's water (matched by name, not distance), and no heavy rain in today's data.":"Rated "+lab+" for 2025, with no heavy rain in today's data, but no overflow in the data names this beach's water, so no overflow could be checked."):(function(x){return x.charAt(0).toUpperCase()+x.slice(1)})(top.slice(0,2).join("; and "))+".";
    res.push({name:b[0],lv:lv,reason:reason})});
  return res}
function vizBathing(){
  var h2=$("bw"),T=TN();if(!h2)return;
  if(!T.bw.length){story("b",h2,esc(T.n)+" is inland and has no designated bathing waters of its own. Choose Plymouth, Plymstock, Saltash, Plympton or Ivybridge above to see the beaches nearest them.");return}
  var vs=verdicts(),c=[0,0,0],n=vs.length;vs.forEach(function(v){c[v.lv]++});
  var lis=$("bwl").children,lab=["Looks fine","Take care","Best avoided today"],ic=["✓","!","✕"];
  vs.forEach(function(v,i){var li=lis[i];if(!li)return;var d=document.createElement("div");d.className="vz-vrow";d.innerHTML='<span class="vz-vd vz-v'+v.lv+'"><span aria-hidden="true">'+ic[v.lv]+'</span>'+lab[v.lv]+'</span><span class="vz-vr">'+v.reason+'</span>';li.appendChild(d)});
  var html="Out of "+nOf(n,"beach","beaches")+" near "+esc(T.n)+": "+c[0]+" look"+(c[0]===1?"s":"")+" fine, "+c[1]+" need"+(c[1]===1?"s":"")+" care and "+c[2]+" "+(c[2]===1?"is":"are")+" best avoided today"+(inSeason()?"":" (outside the bathing season, so there are no daily samples)")+". Surfers Against Sewage and the Environment Agency advise staying out for about 48 hours after a discharge or heavy rain, and overflow data can lag.";
  var fn=slot("vz-bwnote","small",$("bwl"));fn.style.margin="8px 0 0";fn.textContent="Not checked for any beach: pollution incidents (not in this page's data) and rain before today (the hourly data covers today only). Where an overflow's water is not named for a beach, its distance from that beach is not known."+(((Date.now()-SPILLS.asofMs)/864e5)>7?" The overflow history is more than 7 days old, so no beach can show as looking fine.":"")+"";
  story("b",h2,html)}
function vizSewage(){
  var h2=$("sw"),T=TN();if(!h2)return;
  var S=SPILLS,f=spillsFor(),now=Date.now(),age=(now-S.asofMs)/36e5,on=f.filter(function(r){return r[1]===1}),ok=f.filter(function(r){return r[1]===0}).sort(function(a,b){return b[3]-a[3]}),off=f.filter(function(r){return r[1]===-1});
  var html;
  if(!f.length)html="South West Water has no storm overflow within 6 km of the "+esc(T.n)+" centre in this data, so there is nothing to report here.";
  else{
    html=(on.length?"<strong>"+nOf(on.length,"overflow")+" near "+esc(T.n)+" "+(on.length===1?"is":"are")+" discharging</strong> as of "+lt(S.asofMs)+".":"<strong>"+(f.length===1?"The one storm overflow near "+esc(T.n)+" is not discharging":"None of the "+f.length+" storm overflows near "+esc(T.n)+" is discharging")+"</strong> as of "+lt(S.asofMs)+".");
    if(ok.length){var e=ok[0][3];html+=" The most recent finished discharge ended "+ldt(e)+" ("+ago(e)+")"+(now<e+1728e5?(T.c?", so a Surfers Against Sewage alert may stay active until about "+ldt(e+1728e5)+".":". If you are heading to the coast, Surfers Against Sewage alerts stay active for 48 hours after a discharge."):", which is more than 48 hours ago.")}
    if(off.length)html+=" "+nOf(off.length,"overflow")+" "+(off.length>1?"are":"is")+" offline, so "+(off.length>1?"their":"its")+" status is unknown.";
    html+=" Overflow data can lag behind real events"+(age>3?" and this copy is "+(age>48?nOf(Math.round(age/24),"day"):hrs(age))+" old":"")+"."}
  story("s",h2,html);
  var box=slot("vz-tl","",$("st-s"));
  var D30=2592e6,w0=now-D30,rows=[];
  f.forEach(function(r){var end=r[1]===1?now:r[3];if(r[1]!==-1&&end>w0)rows.push({n:AREAS[r[0]]||spillName(r),s:Math.max(r[2],w0),e:end,on:r[1]===1})});
  rows.sort(function(a,b){return b.e-a.e});var more=Math.max(0,rows.length-10);rows=rows.slice(0,10);
  if(!f.length&&!rows.length){box.innerHTML="";return}
  var lab=rows.length?"Timeline of the last 30 days. "+nOf(rows.length+more,"overflow")+" with a recent event"+" shown; latest ended "+ldt(rows[0].e)+".":"Timeline of the last 30 days: no discharges recorded.";
  var o='<h3 class="vz-h3">Discharges in the last 30 days</h3><div class="vz-tl" role="img" aria-label="'+esc(lab)+'">';
  if(!rows.length)o+='<div class="small">No overflow discharges are recorded near '+esc(T.n)+' in the last 30 days.</div>';
  else{o+='<div class="vz-tr ax small" aria-hidden="true"><span></span><span class="vz-tt"><span>30 days ago</span><span>15</span><span>now</span></span></div>';
    rows.forEach(function(r){var l=(r.s-w0)/D30*100,w=Math.max((r.e-r.s)/D30*100,1);o+='<div class="vz-tr"><span class="vz-tn small">'+esc(r.n)+'</span><span class="vz-tt"><span class="z" style="width:'+(1728e5/D30*100).toFixed(1)+'%"></span><i class="'+(r.on?"on":r.e>now-1728e5?"r48":"old")+'" style="left:'+Math.min(l,99).toFixed(1)+'%;width:'+Math.min(w,100-Math.min(l,99)).toFixed(1)+'%"></i></span></div>'});
    o+='<div class="small" style="margin-top:6px">Red bar: discharging now. Amber: ended in the last 48 hours. Grey: older. The tinted end is the 48-hour window. Each overflow shows its latest event only, so earlier ones may be missing'+(more?'; '+more+' more not shown':'')+'.</div>'}
  box.innerHTML=o+'</div>'}
function tcase(x){return String(x).toLowerCase().replace(/\b\w/g,function(c){return c.toUpperCase()})}

function vizAll(){
  safe("flood",vizFlood);safe("air",vizAir);safe("tides",vizTides);safe("bathing",vizBathing);safe("sewage",vizSewage)}
 var rAll=window.renderAll,rDays=window.renderDays;
window.renderAll=function(){rAll.apply(this,arguments);vizAll()};
window.renderDays=function(){rDays.apply(this,arguments);safe("weather",vizWeather)};
vizAll();safe("weather",vizWeather);
})();
