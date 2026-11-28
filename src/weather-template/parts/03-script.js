
(function(){var h=document.documentElement,b=document.getElementById("ltBtn");if(!b)return;
function set(on,save){h.classList.toggle("bigtext",on);b.setAttribute("aria-pressed",on?"true":"false");b.textContent=on?"Normal text":"Larger text";if(save){try{localStorage.setItem("lt-bigtext",on?"1":"0")}catch(e){}}}
var s=false;try{s=localStorage.getItem("lt-bigtext")==="1"}catch(e){}
set(s,false);b.addEventListener("click",function(){set(!h.classList.contains("bigtext"),true)});})();
