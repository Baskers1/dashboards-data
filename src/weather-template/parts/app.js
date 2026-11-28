
var $=function(i){return document.getElementById(i)};

var days=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],mons=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmt(s){var d=new Date(s+"T12:00:00");return days[d.getDay()]+" "+d.getDate()+" "+mons[d.getMonth()]}

function nowLondon(){var p={};new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",hourCycle:"h23",year:"numeric",month:"numeric",day:"numeric",hour:"numeric",minute:"numeric"}).formatToParts(new Date()).forEach(function(x){p[x.type]=+x.value});return new Date(p.year,p.month-1,p.day,p.hour,p.minute)}

function iso(d){return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")}

function rate(p,g){return(p>=50||g>=45)?"Poor":(p>=30||g>=35)?"Fair":"Good"}

function emoji(c){return c===0?"☀️":c<3?"🌤️":c===3?"☁️":c<50?"🌫️":c<70?"🌧️":c<80?"🌨️":c<95?"🌦️":"⛈️"}

function icon(e,z){var sun='<circle cx="24" cy="24" r="8" fill="var(--sun)"/>'+[0,45,90,135,180,225,270,315].map(function(a){return '<line x1="24" y1="7" x2="24" y2="11" stroke="var(--sun)" stroke-width="3" stroke-linecap="round" transform="rotate('+a+' 24 24)"/>'}).join("");
 var cl=function(y){return '<path transform="translate(0 '+y+')" d="M14 34h20a8 8 0 0 0 0-16 11 11 0 0 0-21 3 6.5 6.5 0 0 0 1 13z" fill="var(--cloud)"/>'};
 var sm='<circle cx="17" cy="16" r="7" fill="var(--sun)"/>';
 var dr=function(n){return[15,24,33].slice(0,n).map(function(x){return '<line x1="'+x+'" y1="38" x2="'+(x-3)+'" y2="45" stroke="var(--rain)" stroke-width="3" stroke-linecap="round"/>'}).join("")};
 var g=e==="☀️"?sun:e==="🌤️"||e==="⛅"?sm+cl(0):e==="🌦️"?sm+cl(-4)+dr(2):e==="🌧️"?cl(-6)+dr(3):e==="⛈️"?cl(-6)+'<polygon points="26,34 19,44 24,44 22,50 31,39 26,39" fill="var(--sun)"/>':cl(0);
 return '<svg class="ic" width="'+(z||44)+'" height="'+(z||44)+'" viewBox="0 0 48 52" role="img" aria-label="weather icon">'+g+'</svg>'}

function chart(list){var n=list.length,W=320,H=196,x0=30,dx=(W-2*x0)/Math.max(n-1,1),hi=Math.max.apply(0,list.map(function(x){return x.hi})),lo=Math.min.apply(0,list.map(function(x){return x.lo})),top=22,bot=100,
 y=function(t){return top+(hi+1-t)/(hi-lo+2)*(bot-top)},px=function(i){return x0+i*dx},o="";
 list.forEach(function(x,i){var h=x.pop/100*44;o+='<rect x="'+(px(i)-11)+'" y="'+(H-22-h)+'" width="22" height="'+h+'" rx="3" fill="var(--rain)" opacity=".75"/><text class="m" x="'+px(i)+'" y="'+(H-25-h)+'" text-anchor="middle">'+(x.pop>0?x.pop+"%":"")+'</text><text x="'+px(i)+'" y="'+(H-6)+'" text-anchor="middle">'+fmt(x.date).slice(0,3)+'</text>'});
 ["hi","lo"].forEach(function(k,j){o+='<polyline fill="none" stroke="'+(j?"var(--rain)":"var(--sun)")+'" stroke-width="2.5" points="'+list.map(function(x,i){return px(i)+","+y(x[k])}).join(" ")+'"/>'+list.map(function(x,i){return '<circle cx="'+px(i)+'" cy="'+y(x[k])+'" r="3.5" fill="'+(j?"var(--rain)":"var(--sun)")+'"/><text x="'+px(i)+'" y="'+(y(x[k])+(j?16:-8))+'" text-anchor="middle">'+x[k]+'°</text>'}).join("")});
 return '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Daily high and low temperature with chance of rain">'+o+'</svg><div class="small">Lines: daily high (amber) and low (blue) °C. Bars: chance of rain.</div>'}

function renderDays(){
 var t=iso(nowLondon()),list=DAILY.filter(function(x){return x.date>=t}).slice(0,5);
 $("today").textContent=fmt(t)+" · "+LOC.name+", "+COUNTY[LOCK];
 var mn=Math.min.apply(0,list.map(function(x){return x.lo}))-1,mx=Math.max.apply(0,list.map(function(x){return x.hi}))+1;
 $("days").innerHTML=list.map(function(x,i){var r=rate(x.pop,x.gust);
  return '<div class="day"><b>'+(x.date===t?"Today":fmt(x.date))+'</b>'+icon(x.e)+'<b>'+x.hi+'° / '+x.lo+'°</b><div class="bar" title="temperature range"><i style="left:'+((x.lo-mn)/(mx-mn)*100)+'%;width:'+((x.hi-x.lo)/(mx-mn)*100)+'%"></i></div>'+x.txt+'<div class="rbar" title="chance of rain"><i style="width:'+x.pop+'%"></i></div>Rain '+x.pop+'% · gusts '+x.gust+' km/h<br><span class="tag '+r+'">'+r+'</span></div>'}).join("");
 $("chart").innerHTML=chart(list)}

function renderNow(n,stamp){
 $("now").innerHTML=icon(n.e||"☁️",64)+'<span class="big">'+n.t+'°C</span><div><b>'+n.phrase+'</b><div class="small">Wind '+n.wind+' (gusts '+n.gust+' km/h)'+(n.noHum?'':' · humidity '+n.hum+'%')+'</div></div>';
 $("wstamp").textContent=stamp}

function hoursHtml(rows,src){
 var row=function(r){var k=rate(r[2],r[3]);
  return '<div class="hr"><b>'+r[0]+'</b>'+icon(r[6],28)+'<span>'+r[1]+'°</span><span>'+r[2]+'%'+(r[8]?' <span class="small">'+r[8]+'mm</span>':'')+'</span><span>'+(r[5]?r[5]+' ':'')+r[4]+', gusts <b class="'+k+'">'+r[3]+'</b></span>'+(r[9]==null?'':'<span class="small hd">Feels '+r[9]+'° · humidity '+r[11]+'% · dew point '+r[10]+'° · cloud '+r[12]+'% · '+(r[13]==null?'':'UV '+r[13]+' · ')+'visibility '+r[14]+' km'+(r[15]?' · thunder '+r[15]+'%':'')+'</span>')+'</div>'};
 var head='<div class="hr h"><span>Time</span><span></span><span>Temp</span><span>Rain</span><span>Wind km/h</span></div>',a=rows.length>9?rows.slice(0,8):rows,b=rows.length>9?rows.slice(8):[];
 return '<h3>Next hours</h3><button type="button" class="hdtog" id="hdtog" aria-pressed="false">Show feels-like, humidity and UV</button>'+head+a.map(row).join("")+(b.length?'<details class="more"><summary>Show the other '+b.length+' hours</summary>'+head+b.map(row).join("")+'</details>':'')+'<div class="small" style="margin-top:4px">'+src+' Feels like is the Open-Meteo apparent temperature. Gusts: bold amber or red means 35 km/h or more.</div>'}

function renderHourChart(rows){
 var el=$("hchart"),sm=$("hsum");
 if(!rows||rows.length<2){el.hidden=true;sm.textContent="";return}
 var W=760,M=34,R=8,cw=(W-M-R)/24,H=[];rows.forEach(function(r){H[+r[0].slice(0,2)]=r});
 function X(h){return M+h*cw}
 function C(h){return X(h)+cw/2}
 var ts=rows.map(function(r){return r[1]}),tmin=Math.floor(Math.min.apply(0,ts.concat(rows.map(function(r){return r[9]==null?r[1]:r[9]}))))-1,tmax=Math.ceil(Math.max.apply(0,ts))+1;if(tmax-tmin<6)tmax=tmin+6;
 var gm=Math.max(50,Math.ceil((Math.max.apply(0,rows.map(function(r){return r[3]}))+4)/10)*10);
 var TY=[34,124],RY=[146,200],WY=[222,286],HY=[308,362],BOT=HY[1];
 function yT(v){return TY[1]-(v-tmin)/(tmax-tmin)*(TY[1]-TY[0])}
 function yR(v){return RY[1]-v/100*(RY[1]-RY[0])}
 function yH(v){return HY[1]-v/100*(HY[1]-HY[0])}
 function yW(v){return WY[1]-v/gm*(WY[1]-WY[0])}
 var d=$("hchart"),o='<svg viewBox="0 0 '+W+' 392" xmlns="http://www.w3.org/2000/svg">';
 var rs=sunTimes(nowLondon(),LAT,LON);
 function hf(s){return +s.slice(0,2)+ +s.slice(3,5)/60}
 if(rs.length===2){var a=hf(rs[0]),b=hf(rs[1]);
  o+='<rect x="'+X(0)+'" y="22" width="'+(X(a)-X(0))+'" height="'+(BOT-22)+'" fill="var(--line)" opacity=".45"/><rect x="'+X(b)+'" y="22" width="'+(X(24)-X(b))+'" height="'+(BOT-22)+'" fill="var(--line)" opacity=".45"/>'}
 [["Temperature °C",TY],["Rain chance %",RY],["Wind and gusts km/h",WY],["Humidity and cloud cover %",HY]].forEach(function(p){o+='<text class="m" x="'+M+'" y="'+(p[1][0]-7)+'">'+p[0]+'</text>'});
 for(var h=0;h<24;h++){if(h%3===0)o+='<line x1="'+X(h)+'" x2="'+X(h)+'" y1="22" y2="'+BOT+'" stroke="var(--line)" stroke-width=".6"/><text class="m" x="'+X(h)+'" y="378" text-anchor="middle">'+(h<10?"0":"")+h+'</text>'}
 [tmin,Math.round((tmin+tmax)/2),tmax].forEach(function(v){o+='<line x1="'+M+'" x2="'+(W-R)+'" y1="'+yT(v)+'" y2="'+yT(v)+'" stroke="var(--line)" stroke-width=".5"/><text class="m" x="'+(M-4)+'" y="'+(yT(v)+3)+'" text-anchor="end">'+v+'</text>'});
 [0,50,100].forEach(function(v){o+='<text class="m" x="'+(M-4)+'" y="'+(yR(v)+3)+'" text-anchor="end">'+v+'</text>'});
 [0,50,100].forEach(function(v){o+='<text class="m" x="'+(M-4)+'" y="'+(yH(v)+3)+'" text-anchor="end">'+v+'</text>'});
 [0,35,gm].forEach(function(v){o+='<text class="m" x="'+(M-4)+'" y="'+(yW(v)+3)+'" text-anchor="end">'+v+'</text>'});
 o+='<line x1="'+M+'" x2="'+(W-R)+'" y1="'+yW(35)+'" y2="'+yW(35)+'" stroke="var(--poor)" stroke-width=".8" stroke-dasharray="3 3"/>';
 function path(i,yf){var s="",on=0;for(var h=0;h<24;h++){if(!H[h]||H[h][i]==null){on=0;continue}s+=(on?"L":"M")+C(h).toFixed(1)+" "+yf(H[h][i]).toFixed(1)+" ";on=1}return s}
 o+='<path d="'+path(9,yT)+'" fill="none" stroke="var(--mute)" stroke-width="1.5" stroke-dasharray="4 3"/><path d="'+path(1,yT)+'" fill="none" stroke="var(--sun)" stroke-width="2.5" stroke-linejoin="round"/>';
 o+='<path d="'+path(11,yH)+'" fill="none" stroke="var(--rain)" stroke-width="2"/><path d="'+path(12,yH)+'" fill="none" stroke="var(--cloud)" stroke-width="1.6" stroke-dasharray="4 2"/>';
 o+='<path d="'+path(4,yW)+'" fill="none" stroke="var(--accent)" stroke-width="2"/><path d="'+path(3,yW)+'" fill="none" stroke="var(--fair)" stroke-width="1.6" stroke-dasharray="4 2"/>';
 for(h=0;h<24;h++){var r=H[h];if(!r)continue;
  o+='<text class="e" x="'+C(h)+'" y="17" text-anchor="middle">'+r[6]+'</text>';
  o+='<circle cx="'+C(h)+'" cy="'+yT(r[1])+'" r="2.5" fill="var(--sun)"/>';
  if(h%2===0)o+='<text x="'+C(h)+'" y="'+(yT(r[1])-7)+'" text-anchor="middle">'+r[1]+'°</text>';
  var bh=Math.max(r[2]?1.5:0,r[2]/100*(RY[1]-RY[0]));
  o+='<rect x="'+(X(h)+4)+'" y="'+(RY[1]-bh)+'" width="'+(cw-8)+'" height="'+bh+'" rx="2" fill="var(--rain)"/>';
  if(r[2]>=10)o+='<text x="'+C(h)+'" y="'+(RY[1]-bh-3)+'" text-anchor="middle">'+r[2]+'</text>'}
 var n=nowLondon();if(HOURLY.date===iso(n)){var nx=X(n.getHours()+n.getMinutes()/60);o+='<line x1="'+nx+'" x2="'+nx+'" y1="22" y2="'+BOT+'" stroke="var(--fg)" stroke-width="1.2" stroke-dasharray="2 2"/><text x="'+nx+'" y="'+(BOT+11)+'" text-anchor="middle" style="font-weight:700">now</text>'}
 el.innerHTML=o+'</svg>';el.hidden=false;
 var mx=rows.reduce(function(a,r){return r[1]>a[1]?r:a}),mn=rows.reduce(function(a,r){return r[1]<a[1]?r:a}),g=rows.reduce(function(a,r){return r[3]>a[3]?r:a}),p=rows.reduce(function(a,r){return r[2]>a[2]?r:a});
 sm.innerHTML="High "+mx[1]+"° at "+mx[0]+" · low "+mn[1]+"° at "+mn[0]+" · strongest gusts "+g[3]+" km/h at "+g[0]+" · highest rain chance "+p[2]+"% at "+p[0]+(rs.length===2?" · sunrise "+rs[0]+", sunset "+rs[1]:"")+'.<details class="how"><summary>How to read the chart</summary><p>Amber dashed line = gusts, teal = wind, red dashes = 35 km/h. Grey dashes = feels like; in the humidity panel blue = humidity, dashed = cloud cover. Swipe the chart sideways for the rest of the day. The same hours are listed below the chart.</p>'+(HOURLY.obs?'<p>Hours '+HOURLY.obs+' are filled in from Open-Meteo\'s modelled hourly analysis for this location, not from forecasts or station readings, so they have no rain-chance bars and may differ slightly from the forecast hours.</p>':'')+'</details>';el.setAttribute("aria-label","Hour-by-hour chart of today's temperature, rain chance, wind and humidity. "+sm.textContent.split(/How to read|Sut i ddarllen/)[0])}

function renderHours(){
 var t=iso(nowLondon()),h=nowLondon().getHours(),el=$("hours");
 if(HOURLY.date!==t){el.hidden=true;renderHourChart(null);$("hnote").textContent="Hour-by-hour detail is only shown on the day the page was last refreshed ("+fmt(HOURLY.date)+"). Today's daily forecast is above.";return}
 renderHourChart(HOURLY.rows);var rows=HOURLY.rows.filter(function(r){return +r[0].slice(0,2)>=h-1});
 if(!rows.length){el.hidden=true;$("hnote").textContent="The hourly forecast for today has run out; see the daily forecast above.";return}
 el.innerHTML=hoursHtml(rows,"Open-Meteo model forecast, fetched "+HOURLY.when+".");el.classList.add("nodetail");el.hidden=false;var tg=$("hdtog");if(tg)tg.onclick=function(){var on=el.classList.toggle("nodetail");tg.setAttribute("aria-pressed",String(!on));tg.textContent=on?"Show feels-like, humidity and UV":"Hide feels-like, humidity and UV"};$("hnote").textContent="Forecast data: Open-Meteo.com (CC BY 4.0)."}

var AQB={no2:[67,134,200,267,334,400,467,534,600],o3:[33,66,100,120,140,160,187,213,240],pm25:[11,23,35,41,47,53,58,64,70],pm10:[16,33,50,58,66,75,83,91,100]};

var AQN=[["no2","Nitrogen dioxide (NO\u2082)"],["o3","Ozone (O\u2083)"],["pm25","Fine particles (PM2.5)"],["pm10","Particles (PM10)"]];

function aqIdx(p,v){if(v==null)return 0;var b=AQB[p],i=0;while(i<9&&v>b[i])i++;return i+1}

function aqBand(i){return i<1?0:i<4?1:i<7?2:i<10?3:4}

function aqMean(a,n,min){var s=0,c=0;a.slice(-n).forEach(function(x){if(x!=null){s+=x;c++}});return c>=min?s/c:null}

function aqSpark(a){var v=a.slice(-24),m=Math.max.apply(null,v.filter(function(x){return x!=null}).concat([1])),d="",pen=0;
 v.forEach(function(x,i){if(x==null){pen=0;return}d+=(pen?"L":"M")+(i*260/23).toFixed(1)+" "+(24-x/m*22).toFixed(1)+" ";pen=1});
 return '<svg viewBox="0 0 260 26" preserveAspectRatio="none" role="img" aria-label="Last 24 hours, peak '+Math.round(m)+' micrograms per cubic metre"><path d="'+d+'" fill="none" stroke="var(--accent)" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>'}


var LOCS={{BLOCK:LOCS}};
var TABS={{BLOCK:TABS}};var COUNTY={{BLOCK:COUNTY}};var AIRLL={{BLOCK:AIRLL}};function bearing(a,b,c,d){var R=Math.PI/180,y=Math.sin((d-b)*R)*Math.cos(c*R),x=Math.cos(a*R)*Math.sin(c*R)-Math.sin(a*R)*Math.cos(c*R)*Math.cos((d-b)*R);return["north","north-east","east","south-east","south","south-west","west","north-west"][Math.round(((Math.atan2(y,x)/R+360)%360)/45)%8]}
var LOCK,LOC,LAT,LON,DAILY,HOURLY,BAKED_NOW;
var AIR={{BLOCK:AIR}};
var RIVERS={{BLOCK:RIVERS}};
var FLOODS={{BLOCK:FLOODS}};
var SPILLS={{BLOCK:SPILLS}};
var OUTLOOK={{BLOCK:OUTLOOK}};
var SITE={{BLOCK:SITE}};
var AREAS={{BLOCK:AREAS}};
var WALKS={{BLOCK:WALKS}};
var WSETS={{BLOCK:WSETS}};
function dist(a,b,c,d){var R=Math.PI/180,x=(c-a)*R,y=(d-b)*R*Math.cos((a+c)/2*R);return 6371*Math.sqrt(x*x+y*y)}
function sunTimes(d,lat,lon){var R=Math.PI/180,y=d.getFullYear(),m=d.getMonth(),dd=d.getDate(),N=Math.floor((Date.UTC(y,m,dd)-Date.UTC(y,0,0))/864e5),lh=lon/15,out=[];
 [1,0].forEach(function(rise){var t=N+((rise?6:18)-lh)/24,M=0.9856*t-3.289,L=M+1.916*Math.sin(M*R)+0.02*Math.sin(2*M*R)+282.634;L=(L%360+360)%360;
  var RA=Math.atan(0.91764*Math.tan(L*R))/R;RA=(RA%360+360)%360;RA+=Math.floor(L/90)*90-Math.floor(RA/90)*90;RA/=15;
  var sd=0.39782*Math.sin(L*R),cd=Math.cos(Math.asin(sd)),ch=(Math.cos(90.833*R)-sd*Math.sin(lat*R))/(cd*Math.cos(lat*R));
  if(ch>1||ch<-1){out.push(null);return}
  var H=(rise?360-Math.acos(ch)/R:Math.acos(ch)/R)/15,T=H+RA-0.06571*t-6.622,UT=((T-lh)%24+24)%24;
  out.push(new Date(Date.UTC(y,m,dd)+UT*36e5).toLocaleTimeString("en-GB",{timeZone:"Europe/London",hour:"2-digit",minute:"2-digit"}))});
 return out[0]&&out[1]?out:[]}
function fmMs(ms){return new Date(ms).toLocaleString("en-GB",{timeZone:"Europe/London",weekday:"short",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})}
function ageNote(ms){var a=(Date.now()-ms)/36e5;return a>3?' <b>and is now '+(a>48?Math.round(a/24)+" days":Math.round(a)+" hours")+" old, so check the live sources</b>":""}
var AQLAB=["","Low","Low","Low","Moderate","Moderate","Moderate","High","High","High","Very High"];
function airCalc(s){var o={};AQN.forEach(function(p){var a=s[p[0]];if(!a){o[p[0]]=null;return}var v=p[0]==="no2"?a[a.length-1]:p[0]==="o3"?aqMean(a,8,6):aqMean(a,24,18);o[p[0]]={v:v,i:aqIdx(p[0],v)}});return o}
function airOv(c){var m=0;for(var k in c)if(c[k])m=Math.max(m,c[k].i);return m}
function akm(s){var p=AIRLL[s.k];return p?Math.round(dist(LAT,LON,p[0],p[1])):s.km[LOCK]}function adir(s){var p=AIRLL[s.k];return p?bearing(LAT,LON,p[0],p[1]):s.dir}function airSort(){return AIR.st.slice().sort(function(a,b){return akm(a)-akm(b)})}
function renderAir(){var el=$("air"),A=AIR;if(!el)return;
 var o="",age=(Date.now()-A.last)/36e5,t=new Date(A.last).toLocaleString("en-GB",{timeZone:"Europe/London",weekday:"short",hour:"2-digit",minute:"2-digit"});
 o+='<div class="small" style="margin-bottom:8px">Latest hourly reading: '+t+' UK time'+(age>6?' <b style="color:var(--poor)">(about '+Math.round(age)+' hours old; newer data arrives when this page is refreshed)</b>':'')+'. Values in µg/m³, nearest station first.</div>';
 var sts=airSort(),blk=function(s,i){var c=airCalc(s),ov=airOv(c);
  var cell=function(p){var x=c[p[0]],lab={no2:"NO₂",o3:"Ozone",pm25:"PM2.5",pm10:"PM10"}[p[0]];return '<div><div class="pl">'+lab+'</div>'+(x&&x.v!=null?'<b>'+Math.round(x.v)+'</b><br><span class="dq dq'+aqBand(x.i)+'">'+AQLAB[x.i]+' '+x.i+'</span>':'<span class="small">no reading</span>')+'</div>'};
  return '<div class="aqs"><h3>'+s.n+'</h3><div class="small">About '+akm(s)+' km '+adir(s)+' of '+LOC.name+'. Overall: <span class="dq dq'+aqBand(ov)+'"><i class="cd"></i>'+(ov?AQLAB[ov]+' '+ov:'n/a')+'</span></div><div class="aqg">'+AQN.map(cell).join("")+'</div></div>'};
 o+=sts.slice(0,2).map(blk).join("")+(sts.length>2?'<details class="more"><summary>Show the other '+(sts.length-2)+' stations</summary>'+sts.slice(2).map(blk).join("")+'</details>':'');
 el.innerHTML=o;
 $("airnote").innerHTML='<details class="about"><summary>About this data</summary><div class="small">Hourly readings from Defra\'s UK-AIR network (data provisional and unvalidated; Open Government Licence v3.0). '+SITE.airnote+' NO₂ is the latest hour, ozone an 8-hour mean and particles 24-hour means. Index uses the UK Daily Air Quality Index: 1-3 Low, 4-6 Moderate, 7-9 High, 10 Very High.</div></details>'}
{{CODE:rivers}}
{{CODE:sewage}}
var WF="All",WN=4,WALL=false;
function wtile(w){var a='fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"',b;
 if(w.w)b='<path d="M10 34q6-6 12 0t12 0t12 0t12 0" '+a+'/><path d="M10 48q6-6 12 0t12 0t12 0t12 0" '+a+'/>';
 else b='<path d="M8 58H64" '+a+'/><path d="M22 58V50M22 22L12 50H32ZM50 58V50M50 30L41 50H59Z" fill="var(--accent)" fill-opacity=".28" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round"/>';
 return '<div class="wt" aria-hidden="true"><svg viewBox="0 0 72 72" focusable="false">'+b+'</svg></div>'}
function drawWalks(){var fl=["All","Waterside","Easy","Hard"],set=WSETS[LOCK].map(function(k){return WALKS[k]});
 $("filters").innerHTML=fl.map(function(x){return '<button aria-pressed="'+(WF===x)+'" data-f="'+x+'">'+x+'</button>'}).join("");
 var vis=set.filter(function(w){return WF==="All"||(WF==="Waterside"&&w.w)||(WF==="Easy"&&w.d==="Easy")||(WF==="Hard"&&w.d==="Hard")}),shown=WALL?vis:vis.slice(0,WN);
 $("walks").innerHTML=vis.length?shown.map(function(w){
  return '<article class="card walk">'+wtile(w)+'<div class="wbody"><h3>'+w.n+'</h3><div class="meta"><span>'+w.d+'</span><span>'+w.km+' km</span><span>'+w.h+'</span><span>'+(w.w?"Waterside":SITE.land)+'</span></div><p>'+w.t+'</p><details class="more"><summary>Getting there and route notes</summary><p class="small"><b>Getting there:</b> '+w.get+'</p><p class="small"><b>Underfoot:</b> '+w.under+'</p>'+(w.u?'<p class="small"><b>More detail:</b> <a href="'+w.u[1]+'" target="_blank" rel="noopener">'+w.u[0]+'</a></p>':'')+'</details></div></article>'}).join("")+(vis.length>WN?'<button type="button" class="more" id="wmore" aria-expanded="'+WALL+'">'+(WALL?'Show fewer walks':'Show all '+vis.length+' walks')+'</button>':''):'<p class="small">No walks match this filter for '+LOC.name+'.</p>';
 document.querySelectorAll("[data-f]").forEach(function(b){b.onclick=function(){WF=b.dataset.f;WALL=false;drawWalks()}});
 var wm=$("wmore");if(wm)wm.onclick=function(){WALL=!WALL;drawWalks();if(!WALL)$("k").scrollIntoView()}}
function renderGlance(){var n=nowLondon(),h=n.getHours(),t=iso(n),T=[];
 var rows=(HOURLY&&HOURLY.date===t?HOURLY.rows:[]).filter(function(r){return +r[0].slice(0,2)>=h}),d0=DAILY.filter(function(x){return x.date>=t})[0]||{pop:0,gust:0};
 var pr=rows.length?rows.reduce(function(a,r){return r[2]>a[2]?r:a}):null,gr=rows.length?rows.reduce(function(a,r){return r[3]>a[3]?r:a}):null;
 T.push(["Now",BAKED_NOW.t+"°C",BAKED_NOW.phrase,""]);
 T.push(["Rain chance",(pr?pr[2]:d0.pop)+"%",pr?"highest left today, at "+pr[0]:"forecast for today",""]);
 T.push(["Strongest gusts",(gr?gr[3]:d0.gust)+" km/h",gr?"highest left today, at "+gr[0]:"forecast for today",""]);
 var st=airSort()[0];if(st){var ov=airOv(airCalc(st));T.push(["Air quality",ov?AQLAB[ov]+" "+ov:"n/a","index at "+st.n.replace(/ \(.*\)/,""),ov?"dq"+aqBand(ov):""])}
 var rv=RIVERS.st.slice().sort(function(a,b){return dist(LAT,LON,a.lat,a.lon)-dist(LAT,LON,b.lat,b.lon)})[0];
 if(rv){var nw=rv.v[rv.v.length-1];T.push(["Nearest river",nw.toFixed(2)+" m",rv.r+", "+(rv.lo!=null?(nw<rv.lo?"below":nw>rv.hi?"above":"within")+" "+SITE.rng+" range":(rv.tr?"level "+rv.tr.toLowerCase():"latest reading")),""])}
 $("glance").innerHTML='<h2 id="gh" class="vh">Right now</h2>'+T.map(function(x){return '<div class="g"><div class="gl">'+x[0]+'</div><div class="gv '+x[3]+'">'+x[1]+'</div><div class="gs">'+x[2]+'</div></div>'}).join("")}
function renderTabs(){var b=function(t){return '<button role="tab" aria-selected="'+(LOCK===t[0])+'" aria-pressed="'+(LOCK===t[0])+'" data-t="'+t[0]+'">'+he(t[1])+'</button>'},g1=TABS.filter(function(t){return !t[3]||t[3]==="A"}),g2=TABS.filter(function(t){return t[3]&&t[3]!=="A"}),op=g2.some(function(t){return t[0]===LOCK})||!!(document.querySelector("details.tg2[open]"));
 $("tabs").innerHTML='<div class="tgl" id="tg1l">'+he(SITE.tablabel)+'</div><div class="tgb" role="tablist" aria-labelledby="tg1l">'+g1.map(b).join("")+'</div>'+(g2.length?'<details class="tg2"'+(op?' open':'')+'><summary>'+he(SITE.tabmore||"More places")+' ('+g2.length+' places)</summary><div class="tgb" role="tablist" aria-label="'+he(SITE.tabmorelabel||"More places")+'">'+g2.map(b).join("")+'</div></details>':'');
 document.querySelectorAll("[data-t]").forEach(function(x){x.onclick=function(){setTab(x.dataset.t);try{location.hash=TABS.filter(function(t){return t[0]===x.dataset.t})[0][2]}catch(e){}}})}
function setTab(k){LOCK=k;LOC=LOCS[k];LAT=LOC.lat;LON=LOC.lon;BAKED_NOW=LOC.now;HOURLY=LOC.hourly;var NOWX=!LOC.now||!LOC.baked.length;if(NOWX){BAKED_NOW={t:"–",e:"☁️",phrase:"Forecast loading",wind:"–",gust:"–",hum:"–",when:"not yet fetched"};HOURLY={date:"",rows:[]}}
 DAILY=LOC.baked.map(function(r){return{date:r[0],hi:r[1],lo:r[2],txt:r[3],pop:r[4],wind:r[5],gust:r[6],e:r[7]}});
 renderTabs();if(NOWX){DAILY=[];$("today").textContent=LOC.name+", "+COUNTY[LOCK];$("days").innerHTML="<p class=\"small\">The forecast for "+LOC.name+" has not been fetched yet. Air quality, rivers, flood warnings and walks below are already filled in.</p>";$("chart").innerHTML=""}else renderDays();renderNow({t:BAKED_NOW.t,e:BAKED_NOW.e,phrase:BAKED_NOW.phrase,wind:BAKED_NOW.wind,gust:BAKED_NOW.gust,hum:BAKED_NOW.hum},(LOC.live?"Live Open-Meteo conditions for ":"Open-Meteo conditions for ")+LOC.name+" at "+BAKED_NOW.when+".");
 renderHero();renderFloodTop();renderHours();renderAir();renderRivers();renderSpills();drawWalks();renderGlance();liveTown(k)}

var HEROES={{BLOCK:HEROES}};
function he(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function renderHero(){var el=$("hero"),h=HEROES[LOCK];if(!h){el.hidden=true;el.innerHTML="";return}
 el.innerHTML='<img src="'+he(h.src)+'" alt="'+he(h.alt)+'" width="960" height="300"><figcaption>'+he(h.cap)+'. Photo: '+he(h.by)+', <a href="'+he(h.pg)+'" target="_blank" rel="noopener">'+he(h.site||"Wikimedia Commons")+'</a>, <a href="'+he(h.licurl||"https://creativecommons.org/licenses/by-sa/2.0/")+'" target="_blank" rel="noopener">'+he(h.lic||"CC BY-SA 2.0")+'</a>.'+(SITE.photonote?' '+he(SITE.photonote.replace("{place}",LOC.name)):'')+'</figcaption>';el.hidden=false}
function init(){try{document.documentElement.lang="en-GB"}catch(e){}
 document.querySelectorAll(".jl").forEach(function(a){a.onclick=function(e){var t=$(a.getAttribute("href").slice(1));if(!t)return;e.preventDefault();t.scrollIntoView();t.setAttribute("tabindex","-1");t.focus({preventScroll:true})}});
 var h="";try{h=(location.hash||"").slice(1)}catch(e){}
 var f=TABS.filter(function(t){return t[2]===h})[0];setTab(f?f[0]:TABS[0][0])}
{{CODE:live}}
/* Verdict line (decision 3, 26 Nov 2026). Rules: rain from the highest chance left today,
   under 20% dry, 20-49% showers possible, 50%+ rain likely; gusts left today, under 35 km/h
   light winds, 35-44 breezy, 45+ windy; a flood alert or warning in force goes first. Same
   thresholds as the gust colours and the walk rating. No safety, swim or health advice. */
function verdictParts(name,rain,rt,gust,fl){var o=[];
 if(fl)o.push(["vf",fl.lvl+(fl.town?" in force for "+name+".":" in force in this area.")]);
 o.push(["lead",name+" today:"]);
 if(rain!=null)o.push(["c",rain<20?"dry":rain<50?"showers possible (up to "+rain+"%"+(rt?" around "+rt:"")+")":"rain likely "+(rt?"around "+rt+" ":"")+"("+rain+"%)"]);
 if(gust!=null)o.push(["c",gust<35?"light winds":(gust<45?"breezy":"windy")+", gusts to "+gust+" km/h"]);
 return o}
function verdictText(P){var s="",c=0;P.forEach(function(p){s+=(s?(p[0]==="c"&&c++?", ":" "):"")+p[1]});return s+"."}
function vfloodName(s){s=String(s||"").toLowerCase();return /severe/.test(s)?[1,"Severe flood warning"]:/warning/.test(s)?[2,"Flood warning"]:/alert/.test(s)?[3,"Flood alert"]:null}
/* Default: the board's own "in force" list, which covers its whole area. Boards that map
   notices to each town replace this in their code/coast.js. */
function vflood(){var L=[];try{(typeof floodActive==="function"?floodActive():(window.FLOODS&&FLOODS.items)||[]).forEach(function(x){var v=vfloodName(Array.isArray(x)?x[0]:x.lvl||({1:"severe",2:"warning",3:"alert"})[x.sev]);if(v)L.push(v)})}catch(e){}
 if(!L.length)return null;L.sort(function(a,b){return a[0]-b[0]});return{lvl:L[0][1],town:false}}
function renderVerdict(){var el=$("verdict");if(!el)return;var n=nowLondon(),h=n.getHours(),t=iso(n),
 rows=(HOURLY&&HOURLY.date===t?HOURLY.rows:[]).filter(function(r){return +r[0].slice(0,2)>=h}),d0=(window.DAILY||[]).filter(function(x){return x.date>=t})[0];
 if(!LOC||(!rows.length&&!d0)){el.hidden=true;el.innerHTML="";return}
 var pr=rows.length?rows.reduce(function(a,r){return r[2]>a[2]?r:a}):null,gr=rows.length?rows.reduce(function(a,r){return r[3]>a[3]?r:a}):null,
 P=verdictParts(LOC.name,pr?pr[2]:d0.pop,pr?pr[0]:"",gr?gr[3]:d0.gust,vflood()),o="";
 var c=0;P.forEach(function(p,i){o+=(i?(p[0]==="c"&&c++?'<span>, </span>':' '):'')+'<span'+(p[0]==="vf"?' class="vf"':'')+'>'+he(p[1])+'</span>'});
 el.innerHTML=o+'<span>.</span>';el.hidden=false}
/* Age badge (plan recommendation 5, 28 Nov 2026): how old the "Right now" conditions are, worked
   out in the browser from the stamp the page carries (BAKED_NOW.when, e.g. "22 Nov, 16:17" UK
   time), so a page opened hours later says so. Amber, with "Old data", at 3 hours or more. Hidden
   when the stamp does not parse or is more than 90 min in the future. Whole hours and days are
   rounded down. Ages are wall-clock UK time, so one across a clock change is an hour out. */
function ageMins(w,now){var m=/^(\d{1,2}) ([A-Z][a-z]{2}), (\d\d):(\d\d)$/.exec(String(w||"")),mo=m?mons.indexOf(m[2]):-1;if(mo<0)return null;
 var y=now.getFullYear();if(mo>now.getMonth()+1)y--;
 var a=(Date.UTC(now.getFullYear(),now.getMonth(),now.getDate(),now.getHours(),now.getMinutes())-Date.UTC(y,mo,+m[1],+m[3],+m[4]))/6e4;
 return a<0?(a>-90?0:null):a}
function ageText(a){var h=Math.floor(a/60);return (a>=180?"Old data · ":"")+(a<2?"Updated just now":a<60?"Updated "+Math.round(a)+" min ago":a<2880?"Updated "+h+(h===1?" hour":" hours")+" ago":"Updated "+Math.floor(a/1440)+" days ago")}
function renderAge(){var el=$("age");if(!el)return;var a=null;try{a=ageMins(BAKED_NOW&&BAKED_NOW.when,nowLondon())}catch(e){}
 if(a==null){el.hidden=true;el.textContent="";return}
 var t=ageText(a),c="age"+(a>=180?" old":"");if(el.className!==c)el.className=c;if(el.getAttribute("data-en")!==t){el.setAttribute("data-en",t);el.textContent=t}el.hidden=false}
{{CODE:extra}}
var renderGlance0=renderGlance;renderGlance=function(){renderGlance0.apply(this,arguments);try{renderVerdict()}catch(e){}try{renderAge()}catch(e){}};
setInterval(function(){try{renderAge()}catch(e){}},60000);
init();
