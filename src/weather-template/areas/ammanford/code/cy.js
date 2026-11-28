
(function(){
var W={{BLOCK:CYW}},CYP={"Ammanford": "Rhydaman", "Glanamman": "Glanaman", "Tycroes": "Tŷ-croes", "Llandybie": "Llandybïe", "Penygroes": "Pen-y-groes", "Gorslas": "Gors-las", "Brynamman": "Brynaman", "Cwmgors": "Cwm-gors", "Gwaun-Cae-Gurwen": "Gwauncaegurwen", "Trapp": "Trap", "Tumble": "Y Tymbl", "Llannon": "Llan-non", "Hendy": "Yr Hendy", "Felinfoel": "Felin-foel", "Ffairfach": "Ffair-fach", "Swansea": "Abertawe", "Carmarthenshire": "Sir Gaerfyrddin", "Neath Port Talbot": "Castell-nedd Port Talbot"},NOMUT=["Cross Hands"],PL=["Neath Port Talbot", "Gwaun-Cae-Gurwen", "Carmarthenshire", "Pontarddulais", "Ystradgynlais", "Capel Hendre", "Cross Hands", "Llangennech", "Cefneithin", "Pontyberem", "Llanarthne", "Pontardawe", "Ystalyfera", "Ammanford", "Glanamman", "Llandybie", "Penygroes", "Brynamman", "Llandeilo", "Ffairfach", "Bethlehem", "Gorseinon", "Felinfoel", "Llanelli", "Garnant", "Tycroes", "Gorslas", "Cwmgors", "Drefach", "Llannon", "Clydach", "Swansea", "Tumble", "Betws", "Saron", "Trapp", "Hendy", "Powys"];
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
function tr(s){var P=[],D=[],C=[],N=[];
 var t=s.replace(PRE,function(m){P.push(m);return '{P}'}).replace(DRE,function(m){D.push(m);return '{D}'}).replace(CRE,function(m){C.push(m);return '{C}'}).replace(NRE,function(m){N.push(m);return '#'});
 var v=W[t];if(v==null){var m=s.match(/^(DCWW\d+) · ([\d.]+) km from (.+?) · discharges to (.+?) ·$/);
  if(m&&PL.indexOf(m[3])>=0)return m[1]+' · '+putPlace(m[2]+' km o ',m[3])+' · yn gollwng i '+cyWater(m[4])+' ·';return null}var out='',re=/\{Pm\}|\{Pe\}|\{Px\}|\{P\}|\{D\}|\{C\}|#/g,last=0,x;
 while(x=re.exec(v)){out+=v.slice(last,x.index);last=re.lastIndex;var k=x[0];
  if(k=='{D}')out+=cyDate(D.shift()||'');else if(k=='{C}')out+=C.shift()||'';else if(k=='#')out+=N.shift()||'';
  else if(k=='{Pe}')out+=P.shift()||'';else if(k=='{Px}')P.shift();else out=putPlace(out,P.shift()||'',k=='{Pm}')}
 return out+v.slice(last)}
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
window.__cyTr=tr;
})();
