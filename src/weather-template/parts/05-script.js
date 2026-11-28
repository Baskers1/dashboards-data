(function(){var g=function(i){return document.getElementById(i)},RM=!!(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches),o='<circle class="face" cx="60" cy="60" r="56"/>',i,a,r=Math.PI/180;
for(i=0;i<60;i++){a=i*6*r;var m5=i%5===0,l=m5?8:4;o+='<line class="tk'+(m5?' tk5':'')+'" x1="'+(60+Math.sin(a)*(54-l)).toFixed(1)+'" y1="'+(60-Math.cos(a)*(54-l)).toFixed(1)+'" x2="'+(60+Math.sin(a)*54).toFixed(1)+'" y2="'+(60-Math.cos(a)*54).toFixed(1)+'"/>'}
[12,3,6,9].forEach(function(n){a=n*30*r;o+='<text x="'+(60+Math.sin(a)*37).toFixed(1)+'" y="'+(60-Math.cos(a)*37+3.2).toFixed(1)+'">'+n+'</text>'});
o+='<line id="hh" x1="60" y1="60" x2="60" y2="34" stroke="var(--fg)" stroke-width="4" stroke-linecap="round"/><line id="mh" x1="60" y1="60" x2="60" y2="20" stroke="var(--fg)" stroke-width="2.5" stroke-linecap="round"/><line id="sh" x1="60" y1="68" x2="60" y2="16" stroke="var(--accent)" stroke-width="1.2" stroke-linecap="round"/><circle cx="60" cy="60" r="3" fill="var(--accent)"/>';
var c=g("clk");if(!c)return;c.innerHTML=o;if(RM)g("sh").setAttribute("visibility","hidden");
function tick(){var p={};new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",hourCycle:"h23",hour:"numeric",minute:"numeric",second:"numeric",timeZoneName:"short"}).formatToParts(new Date()).forEach(function(x){p[x.type]=x.value});
var h=+p.hour,m=+p.minute,s=+p.second,z=function(n){return String(n).padStart(2,"0")};
g("hh").setAttribute("transform","rotate("+((h%12+m/60)*30)+" 60 60)");g("mh").setAttribute("transform","rotate("+((m+s/60)*6)+" 60 60)");g("sh").setAttribute("transform","rotate("+(s*6)+" 60 60)");
g("dig").textContent=z(h)+":"+z(m)+(RM?"":":"+z(s))+" "+(p.timeZoneName||"")}
tick();setInterval(tick,RM?15000:1000)})();