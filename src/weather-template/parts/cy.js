
(function(){
var W={{BLOCK:CYW}},CYL={{BLOCK:CYPL}},CYP=CYL.CYP,NOMUT=CYL.NOMUT,PL=CYL.PL;
function esc(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
var PRE=new RegExp('(?<![\\w-])('+PL.map(esc).join('|')+')(?![\\w-])','g'),
 DRE=/(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),? )?\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b(?:,? \d\d:\d\d)?/g,
 CRE=/\b(?:NNE|ENE|ESE|SSE|SSW|WSW|WNW|NNW|NE|SE|SW|NW|N|E|S|W)\b/g,NRE=/\d+(?:\.\d+)?/g;
var DY={Mon:'Llun',Tue:'Maw',Wed:'Mer',Thu:'Iau',Fri:'Gwe',Sat:'Sad',Sun:'Sul'},
 MO={Jan:'Ion',Feb:'Chwe',Mar:'Maw',Apr:'Ebr',May:'Mai',Jun:'Meh',Jul:'Gor',Aug:'Awst',Sep:'Medi',Sept:'Medi',Oct:'Hyd',Nov:'Tach',Dec:'Rhag'};
function cyDate(d){return d.replace(/\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b/,function(m){return DY[m]}).replace(/\b(Sept|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/,function(m){return MO[m]})}
var SOFT=[['Ll','L'],['Rh','R'],['Ch','Ch'],['Ph','Ph'],['Th','Th'],['C','G'],['P','B'],['T','D'],['G',''],['B','F'],['D','Dd'],['M','F']],
 ASP=[['Ch','Ch'],['Ph','Ph'],['Th','Th'],['C','Ch'],['P','Ph'],['T','Th']],
 NAS=[['Ch','Ch'],['Ph','Ph'],['Th','Th'],['C','Ngh'],['P','Mh'],['T','Nh'],['G','Ng'],['B','M'],['D','N']];
function mut(w,T){for(var i=0;i<T.length;i++)if(w.indexOf(T[i][0])==0){var r=T[i][1]+w.slice(T[i][0].length);return T[i][1]===''?r.charAt(0).toUpperCase()+r.slice(1):r}return w}
// place after preposition: soft (o,i,am,drwy,dros,at,{Pm}), aspirate (a,gyda,tua), nasal (yn)
function putPlace(out,en,force){var cy=CYP[en]||en;if(NOMUT.indexOf(en)>=0)return out+cy;
 var m=out.match(/(^|[\s(’'])([A-Za-zâ]+) $/),w=m?m[2]:'';
 if(/^Yr? /.test(cy)){if(/^(o|i|a|gyda|tua|am|drwy|dros|at)$/.test(w))return out.slice(0,-1)+'’r '+cy.replace(/^Yr? /,'');if(w=='yn')return out+cy.charAt(0).toLowerCase()+cy.slice(1);return out+cy}
 if(force||/^(o|i|am|drwy|dros|at)$/.test(w))return out+mut(cy,SOFT);
 if(w=='a'&&/^[AEIOUWYÂŴŶ]/.test(cy))return out.slice(0,-1)+'c '+cy;
 if(/^(a|gyda|tua)$/.test(w))return out+mut(cy,ASP);
 if(w=='yn'){var n=mut(cy,NAS),p=/^(Ngh|Ng)/.test(n)?'yng ':/^(Mh|M)/.test(n)&&n!=cy?'ym ':'yn ';return out.slice(0,-3)+p+n}
 return out+cy}
function cyWater(x){return x.replace(/^Unnamed [Tt]ributary of (the )?/,'isafon ddienw ').replace(/^[Tt]ributary of (the )?/,'isafon ').replace(/\b(Lower|Upper) (?:River |Afon )?([A-Z]\w+)(?: River)?/,function(m,u,r){return 'Afon '+r+(u=='Lower'?' Isaf':' Uchaf')}).replace(/\b(?:the )?River ([A-Z]\w+)/g,'Afon $1')}
/* Fallbacks (26 Nov 2026): a text with no entry is tried again with wind directions and
   weather words ({X}) and signed numbers tokenised, then sentence by sentence. A text is only
   translated if every sentence is: half-Welsh reads worse than English. */
var XW={"north": "gogledd", "north-north-east": "gogledd-gogledd-ddwyrain", "north-east": "gogledd-ddwyrain", "east-north-east": "dwyrain-gogledd-ddwyrain", "east": "dwyrain", "east-south-east": "dwyrain-de-ddwyrain", "south-east": "de-ddwyrain", "south-south-east": "de-de-ddwyrain", "south": "de", "south-south-west": "de-de-orllewin", "south-west": "de-orllewin", "west-south-west": "gorllewin-de-orllewin", "west": "gorllewin", "west-north-west": "gorllewin-gogledd-orllewin", "north-west": "gogledd-orllewin", "north-north-west": "gogledd-gogledd-orllewin", "clear": "clir", "mostly clear": "clir gan fwyaf", "partly cloudy": "rhannol gymylog", "overcast": "cymylog iawn", "foggy": "niwlog", "rime fog": "niwl barrug", "light drizzle": "glaw mân ysgafn", "moderate drizzle": "glaw mân cymedrol", "heavy drizzle": "glaw mân trwm", "freezing drizzle": "glaw mân rhewllyd", "slight rain": "glaw ysgafn", "moderate rain": "glaw cymedrol", "heavy rain": "glaw trwm", "freezing rain": "glaw rhewllyd", "slight snow": "eira ysgafn", "moderate snow": "eira cymedrol", "heavy snow": "eira trwm", "snow grains": "gronynnau eira", "slight showers": "cawodydd ysgafn", "moderate showers": "cawodydd cymedrol", "violent showers": "cawodydd ffyrnig", "slight snow showers": "cawodydd eira ysgafn", "heavy snow showers": "cawodydd eira trwm", "thunderstorm": "storm fellt a tharanau", "thunderstorm with hail": "storm fellt a tharanau gyda chenllysg", "mostly cloudy": "cymylog gan fwyaf", "cloudy": "cymylog", "nitrogen dioxide": "nitrogen deuocsid", "ozone": "osôn", "fine particles (PM2.5)": "gronynnau mân (PM2.5)", "particles (PM10)": "gronynnau (PM10)"},XRE=new RegExp('\\b('+Object.keys(XW).sort(function(a,b){return b.length-a.length}).map(esc).join('|')+')(?![\\w-])','gi'),NRE2=/-?\d+(?:\.\d+)?/g,XWL={};Object.keys(XW).forEach(function(k){XWL[k.toLowerCase()]=XW[k]});
/* Data names (27 Nov 2026): river gauges (RIVERS), overflow sites and the water they reach
   (SPILLS), air stations (AIR) and flood areas (FLOODS) are read from the page's own data. On a third try a text has
   each name lifted out as {Q}, and a list of names ("A, B and C") as {L}, so one entry covers
   every gauge. A name the dictionary knows is written in Welsh (Afon Aman), others stay as they
   are. Bare place names are left to {P}, which mutates them. */
var NM=(function(){var a=[];function add(s){if(typeof s=='string'&&s.length>3&&/[A-Z]/.test(s)&&PL.indexOf(s)<0&&a.indexOf(s)<0)a.push(s)}
 try{if(typeof RIVERS!='undefined'&&RIVERS&&RIVERS.st)RIVERS.st.forEach(function(g){add(g.r&&g.n?g.r+', '+g.n:'');add(g.r&&g.n?g.r+' at '+g.n:'');add(g.r);add(g.n)})}catch(e){}
 try{if(typeof SPILLS!='undefined'&&SPILLS&&SPILLS.f)SPILLS.f.forEach(function(x){add(x[6]);add(x[7])})}catch(e){}
 try{if(typeof AIR!='undefined'&&AIR&&AIR.st)AIR.st.forEach(function(x){add(x.n)})}catch(e){}
 try{if(typeof FLOODS!='undefined'&&FLOODS&&FLOODS.items)FLOODS.items.forEach(function(x){if(x&&!Array.isArray(x))add(x.area)})}catch(e){}
 return a.sort(function(x,y){return y.length-x.length})})(),
 SRE=NM.length?new RegExp('(?<![\\w-])('+NM.map(esc).join('|')+')(?![\\w-])','g'):null;
function tok(s,ext){var o={P:[],D:[],C:[],N:[],X:[],S:[],L:[]};
 if(ext>1&&SRE){s=s.replace(SRE,function(m){o.S.push(m);return '\u0001'});
  var S2=[],k=0;s=s.replace(/\u0001(?:(?:,? and |; |, )\u0001)*/g,function(m){var it=m.split(/,? and |; |, /),sp=m.match(/,? and |; |, /g)||[],n=it.length,L=o.S.slice(k,k+n);k+=n;
   if(n==1&&ext<3){S2.push(L[0]);return '{Q}'}if(n==1){o.L.push(nm(L[0]));return '{L}'}var out=nm(L[0]);for(var i=1;i<n;i++)out+=(/and/.test(sp[i-1])?(/^[AEIOUYWÂ]/.test(nm(L[i]))?' ac ':' a '):sp[i-1])+nm(L[i]);o.L.push(out);return '{L}'});o.S=S2}
 var t=s.replace(PRE,function(m){o.P.push(m);return '{P}'}).replace(DRE,function(m){o.D.push(m);return '{D}'});
 if(ext)t=t.replace(XRE,function(m){o.X.push(XWL[m.toLowerCase()]);return '{X}'});
 o.t=t.replace(CRE,function(m){o.C.push(m);return '{C}'}).replace(ext?NRE2:NRE,function(m){o.N.push(m);return '#'});return o}
function fill(v,o){var out='',re=/\{Pm\}|\{Pe\}|\{Px\}|\{P\}|\{D\}|\{C\}|\{X\}|\{Q\}|\{L\}|#/g,last=0,x;
 while(x=re.exec(v)){out+=v.slice(last,x.index);last=re.lastIndex;var k=x[0];
  if(k=='{D}')out+=cyDate(o.D.shift()||'');else if(k=='{C}')out+=o.C.shift()||'';else if(k=='{X}')out+=o.X.shift()||'';else if(k=='{Q}')out+=nm(o.S.shift()||'');else if(k=='{L}')out+=o.L.shift()||'';else if(k=='#')out+=o.N.shift()||'';
  else if(k=='{Pe}')out+=o.P.shift()||'';else if(k=='{Px}')o.P.shift();else out=putPlace(out,o.P.shift()||'',k=='{Pm}')}
 return out+v.slice(last)}
function one01(s){var o=tok(s,0),v=W[o.t];if(v!=null)return fill(v,o);o=tok(s,1);v=W[o.t];return v!=null?fill(v,o):null}
function nm(s){var r=one01(s);return r!=null?r:s}
/* Last try (27 Nov 2026): Welsh does not change with English number agreement, so "1 gauge is
   rising" is looked up as "# gauges are rising" and a single name as a one-name list ({L}). One
   dictionary line then covers singular and plural. */
function agree(t){return t.replace(/# hour\b/g,'# hours').replace(/# day\b/g,'# days').replace(/# (gauge|other reading|flood notice)\b/g,'# $1s')
 .replace(/\bThere is # /g,'There are # ').replace(/# (gauges|other readings|flood notices) is\b/g,'# $1 are').replace(/(^|, )# is (within|above|below)\b/g,'$1# are $2')}
function one(s){var r=one01(s);if(r!=null||!SRE)return r;var o=tok(s,2),v=W[o.t];if(v!=null)return fill(v,o);
 o=tok(s,3);v=W[agree(o.t)];return v!=null?fill(v,o):null}
/* Names from the data (gauges, stations, overflow sites) stay as they are: "NAME: reading"
   and "NAME, state" translate the reading or state and keep NAME; "text: NAME and NAME." keeps
   the names. A name is a run of capitalised words, numbers and short joining words. */
var NW=/^[A-Z0-9][\w'’.\-]*(?:(?:,? | · | and | at | near | of | on | y | yr | ar )[A-Z0-9][\w'’.\-]*)*$/;
function named(s){var i=s.indexOf(': '),j,h,t,r;
 if(i>0){h=s.slice(0,i);t=s.slice(i+2);
  if(NW.test(h)&&(r=one(t))!=null)return h+': '+r;
  var tl=t.replace(/\.$/,'');if(NW.test(tl.replace(/ and /g,', '))&&(r=one(h+':'))!=null)return r+' '+t}
 j=s.lastIndexOf(', ');if(j>0){h=s.slice(0,j);t=s.slice(j+2);if(NW.test(h)&&(r=one(t))!=null)return h+', '+r}
 return null}
function one2(s){var r=one(s);return r!=null?r:named(s)}
function tr(s){var r=one2(s);if(r!=null)return r;
 var m=s.match(/^(DCWW\d+) · ([\d.]+) km from (.+?) · discharges to (.+?) ·$/);
  if(m&&PL.indexOf(m[3])>=0)return m[1]+' · '+putPlace(m[2]+' km o ',m[3])+' · yn gollwng i '+cyWater(m[4])+' ·';
 var ss=s.split(/(?<=[.!?])\s+(?=[A-Za-z0-9(“"”])/),out=[];
 for(var i=0;i<ss.length;i++){var t=one2(ss[i]);
  if(t==null){var pp=ss[i].split(/;\s+/);if(pp.length<2)return null;t=[];for(var j=0;j<pp.length;j++){var u=one2(pp[j]);if(u==null)return null;t.push(u)}t=t.join('; ')}
  out.push(t)}
 return out.join(' ')}
var lang='en',TX=new WeakMap(),AT=new WeakMap(),ATTRS=['aria-label','alt','title'];
function txNode(n){var p=n.parentNode;if(!p||p.nodeName=='SCRIPT'||p.nodeName=='STYLE'||(p.closest&&p.closest('[data-notx]')))return;
 var r=TX.get(n),v=n.nodeValue;
 if(lang=='en'){if(r&&v===r.cy)n.nodeValue=r.en;return}
 if(r&&v===r.cy)return;var m=v.match(/^(\s*)([\s\S]*?)(\s*)$/),k=m[2].replace(/\s+/g,' ');if(!k)return;
 var c=tr(k);if(c==null)return;var o=m[1]+c+m[3];TX.set(n,{en:v,cy:o});if(o!==v)n.nodeValue=o}
function txAttr(e,a){if(e.closest&&e.closest('[data-notx]'))return;var v=e.getAttribute(a);if(v==null)return;var M=AT.get(e);if(!M){M={};AT.set(e,M)}var r=M[a];
 if(lang=='en'){if(r&&v===r.cy)e.setAttribute(a,r.en);return}
 if(r&&v===r.cy)return;var c=tr(v.trim().replace(/\s+/g,' '));if(c==null)return;M[a]={en:v,cy:c};if(c!==v)e.setAttribute(a,c)}
function walk(root){if(root.nodeType==3)return txNode(root);if(root.nodeType!=1)return;
 var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),n;while(n=w.nextNode())txNode(n);
 ATTRS.forEach(function(a){if(root.hasAttribute(a))txAttr(root,a);root.querySelectorAll('['+a+']').forEach(function(e){txAttr(e,a)})})}
var TT={en:document.title},mo=new MutationObserver(function(L){mo.disconnect();
 L.forEach(function(r){if(r.type=='characterData')txNode(r.target);else if(r.type=='attributes')txAttr(r.target,r.attributeName);else r.addedNodes.forEach(walk)});obs()});
function obs(){mo.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:ATTRS})}
function setLang(l,save){lang=l;mo.disconnect();walk(document.body);obs();
 document.documentElement.lang=l=='cy'?'cy':'en-GB';document.title=l=='cy'?(tr(TT.en)||TT.en):TT.en;
 document.querySelectorAll('[data-lang]').forEach(function(b){b.setAttribute('aria-pressed',b.getAttribute('data-lang')==l?'true':'false')});
 if(save){try{localStorage.setItem('dash-lang',l)}catch(e){}}}
document.querySelectorAll('[data-lang]').forEach(function(b){b.addEventListener('click',function(){setLang(b.getAttribute('data-lang'),true)})});
var s='en';try{s=localStorage.getItem('dash-lang')||'en'}catch(e){}
obs();if(s=='cy')setLang('cy',false);
window.__cyTr=tr;window.__cyKeys=function(s){var k=[];if(tr(s)!=null)return k;s.split(/(?<=[.!?])\s+(?=[A-Za-z0-9(“"”])/).forEach(function(x){if(one2(x)!=null)return;var pp=x.split(/;\s+/);
 if(pp.length>1)pp.forEach(function(y){if(one2(y)==null)k.push(agree(tok(y,3).t))});else k.push(agree(tok(x,3).t))});return k};
})();
