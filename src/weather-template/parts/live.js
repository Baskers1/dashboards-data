/* Live forecast (22 Nov 2026). When the page opens, and when a town is chosen, the
   reader's browser asks Open-Meteo for that town and replaces its now, hourly and 8-day
   figures with the answer. omBlock() is a copy of place_block() in
   scrapekit/scrapers/om_rows.py, checks included, so live figures have exactly the shape
   and rounding of the hourly snapshot (test_live.py runs both on one answer). Any failure
   (no answer in 8 s, a refused request, a check that fails) leaves the hourly snapshot on
   the page. On a claude.ai artifact link the request is always refused, so readers there
   see the snapshot, as before. Costs no Claude tokens: the reader's browser calls
   Open-Meteo directly. */
var OMQ="&timezone=Europe%2FLondon&wind_speed_unit=kmh&forecast_days=8&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset&hourly=temperature_2m,precipitation_probability,precipitation,wind_gusts_10m,wind_speed_10m,wind_direction_10m,weather_code,apparent_temperature,dew_point_2m,relative_humidity_2m,cloud_cover,uv_index,visibility";
var OMPH={0:"Clear",1:"Mostly clear",2:"Partly cloudy",3:"Overcast",45:"Foggy",48:"Rime fog",51:"Light drizzle",53:"Moderate drizzle",55:"Heavy drizzle",56:"Freezing drizzle",57:"Freezing drizzle",61:"Slight rain",63:"Moderate rain",65:"Heavy rain",66:"Freezing rain",67:"Freezing rain",71:"Slight snow",73:"Moderate snow",75:"Heavy snow",77:"Snow grains",80:"Slight showers",81:"Moderate showers",82:"Violent showers",85:"Slight snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Thunderstorm with hail"};
var OMU={daily:{temperature_2m_max:"°C",temperature_2m_min:"°C",precipitation_probability_max:"%",wind_speed_10m_max:"km/h",wind_gusts_10m_max:"km/h"},hourly:{temperature_2m:"°C",apparent_temperature:"°C",dew_point_2m:"°C",precipitation:"mm",precipitation_probability:"%",relative_humidity_2m:"%",cloud_cover:"%",visibility:"m",wind_speed_10m:"km/h",wind_gusts_10m:"km/h",wind_direction_10m:"°"},current:{temperature_2m:"°C",relative_humidity_2m:"%",wind_speed_10m:"km/h",wind_gusts_10m:"km/h",wind_direction_10m:"°"}};
var OMR={temperature_2m:[-25,45],temperature_2m_max:[-25,45],temperature_2m_min:[-25,45],apparent_temperature:[-35,50],dew_point_2m:[-35,40],wind_speed_10m:[0,200],wind_speed_10m_max:[0,200],wind_gusts_10m:[0,250],wind_gusts_10m_max:[0,250],wind_direction_10m:[0,360],relative_humidity_2m:[0,100],precipitation_probability:[0,100],precipitation_probability_max:[0,100],precipitation:[0,100],cloud_cover:[0,100],uv_index:[0,15],visibility:[0,100000],weather_code:[0,99]};
var OMC=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];
function omR0(x){return x==null?null:x>=0?Math.floor(x+0.5):-Math.floor(-x+0.5)}
function omR1(x){return x==null?null:omR0(x*10)/10}
function omCmp(d){return OMC[Math.floor((((d%360)+360)%360)/22.5+0.5)%16]}
function omPh(c){if(!(c in OMPH))throw Error("code "+c);return OMPH[c]}
function omEm(c){return c===0?"☀️":c<3?"🌤️":c===3?"☁️":c<50?"🌫️":c<70?"🌧️":c<80?"🌨️":c<95?"🌦️":"⛈️"}
/* today: "YYYY-MM-DD" London; when: the stamp shown; offs: London's UTC offset in seconds
   today; nowMs: the clock, for the age check (null skips it). Throws if any check fails. */
function omBlock(j,today,when,offs,nowMs){var D=j.daily,H=j.hourly,C=j.current,p,k,i,v,r;
 if(!D||!H||!C)throw Error("missing block");
 for(p in OMU){var u=j[p+"_units"];if(!u)throw Error("no units");for(k in OMU[p])if(u[k]!==OMU[p][k])throw Error("unit "+k)}
 if(j.timezone!=="Europe/London"||j.utc_offset_seconds!==offs)throw Error("clock");
 [D,H].forEach(function(b){for(k in b){r=OMR[k];if(!r||!Array.isArray(b[k]))continue;b[k].forEach(function(x){if(x!=null&&(x<r[0]||x>r[1]))throw Error("range "+k)})}});
 for(k in C){r=OMR[k];v=C[k];if(r&&v!=null&&(v<r[0]||v>r[1]))throw Error("range current "+k)}
 if(typeof C.time!=="string"||C.time.slice(0,10)!==today)throw Error("current not today");
 if(nowMs!=null){var lag=(nowMs-(Date.parse(C.time+":00Z")-offs*1000))/6e4;if(lag<-15||lag>90)throw Error("current age")}
 if(!D.time||D.time[0]!==today||D.time.length<8)throw Error("daily not today");
 var baked=[];for(i=0;i<8;i++)baked.push([D.time[i],omR0(D.temperature_2m_max[i]),omR0(D.temperature_2m_min[i]),omPh(D.weather_code[i]),omR0(D.precipitation_probability_max[i]||0),omR0(D.wind_speed_10m_max[i]),omR0(D.wind_gusts_10m_max[i]),omEm(D.weather_code[i])]);
 var sr=D.sunrise[0].slice(11,16),ss=D.sunset[0].slice(11,16),rows=[];
 H.time.forEach(function(ts,i){if(ts.slice(0,10)!==today)return;var t=ts.slice(11,16),c=H.weather_code[i],hh=t.slice(0,2)+":30",night=(hh<sr||hh>ss)&&c<2;
  if(H.temperature_2m[i]==null||c==null)throw Error("hour "+t);
  rows.push([t,omR0(H.temperature_2m[i]),omR0(H.precipitation_probability[i]),omR0(H.wind_gusts_10m[i]),omR0(H.wind_speed_10m[i]),omCmp(H.wind_direction_10m[i]||0),night?"🌙":omEm(c),omPh(c),omR1(H.precipitation[i]),omR0(H.apparent_temperature[i]),omR0(H.dew_point_2m[i]),omR0(H.relative_humidity_2m[i]),omR0(H.cloud_cover[i]),omR1(H.uv_index[i]),H.visibility[i]!=null?omR1(H.visibility[i]/1000):null,null,"om"])});
 if(rows.length!==24)throw Error("hours "+rows.length);
 return{baked:baked,now:{t:omR0(C.temperature_2m),e:omEm(C.weather_code),phrase:omPh(C.weather_code),wind:omCmp(C.wind_direction_10m||0)+" "+omR0(C.wind_speed_10m)+" km/h",gust:omR0(C.wind_gusts_10m),hum:omR0(C.relative_humidity_2m),when:when},hourly:{date:today,when:when,rows:rows}}}
function omOffs(){var n=new Date(),p={};new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",hourCycle:"h23",year:"numeric",month:"numeric",day:"numeric",hour:"numeric",minute:"numeric"}).formatToParts(n).forEach(function(x){p[x.type]=+x.value});
 return Math.round((Date.UTC(p.year,p.month-1,p.day,p.hour,p.minute)-Math.floor(n.getTime()/6e4)*6e4)/6e4)*60}
var LIVE={};
function liveTown(k){var L=LOCS[k];if(!L||L.lat==null||!window.fetch||!window.Intl)return;var s=LIVE[k];if(s&&Date.now()-s<6e5)return;LIVE[k]=Date.now();
 var ac=window.AbortController?new AbortController():null,to=setTimeout(function(){if(ac)ac.abort()},8000);
 fetch("https://api.open-meteo.com/v1/forecast?latitude="+L.lat+"&longitude="+L.lon+OMQ,ac?{signal:ac.signal}:{}).then(function(r){if(!r.ok)throw Error("http "+r.status);return r.json()}).then(function(j){clearTimeout(to);
  var n=nowLondon(),when=n.getDate()+" "+["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][n.getMonth()]+", "+String(n.getHours()).padStart(2,"0")+":"+String(n.getMinutes()).padStart(2,"0"),b=omBlock(j,iso(n),when,omOffs(),Date.now());
  L.baked=b.baked;L.now=b.now;L.hourly=b.hourly;L.live=1;if(LOCK===k)setTab(k)}).catch(function(){clearTimeout(to)})}
