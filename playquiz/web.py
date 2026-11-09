"""Página web sencilla para votar desde celulares u otras computadoras."""

PAGINA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PlayQuiz</title>
<style>
:root{--a:#E8505B;--b:#2B7DE9;--ink:#262B40;--bg:#F4F1FF;--p:#6C4DF6}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--p);color:#fff;padding:16px;text-align:center;font-size:1.6rem;font-weight:800}
main{max-width:760px;margin:0 auto;padding:16px}
.card{background:#fff;border-radius:18px;padding:20px;box-shadow:0 4px 14px #0001;margin-bottom:16px}
h2{margin:.2em 0 .6em;font-size:1.4rem;text-align:center}
.opts{display:grid;gap:12px}@media(min-width:600px){.opts{grid-template-columns:1fr 1fr}}
button{font:inherit;font-weight:700;border:0;border-radius:14px;padding:22px 12px;color:#fff;cursor:pointer;font-size:1.15rem}
#a{background:var(--a)}#b{background:var(--b)}button.sec{background:var(--p);padding:14px;margin-top:10px;width:100%}
select{width:100%;padding:12px;font-size:1rem;border-radius:10px;margin:8px 0}
.bar{height:10px;background:#dde;border-radius:6px;overflow:hidden;margin-bottom:12px}.bar i{display:block;height:100%;background:var(--p)}
img{width:100%;border-radius:10px}.msg{text-align:center;font-weight:600;margin:8px 0}
</style></head><body>
<header>🎯 PlayQuiz</header><main>
<div class="card" id="menu"><h2>Elige una temática</h2>
<select id="cat"></select><select id="n"><option>5</option><option selected>10</option><option>15</option></select>
<button class="sec" onclick="empezar()">¡Jugar!</button></div>
<div class="card" id="juego" hidden>
<div class="bar"><i id="prog"></i></div><div id="cont" class="msg"></div>
<h2 id="preg"></h2><div class="opts"><button id="a"></button><button id="b"></button></div>
<div id="res" hidden><img id="graf" alt="Gráfico de resultados"><div id="aviso" class="msg"></div>
<button class="sec" id="sig" onclick="siguiente()">Siguiente ▶</button></div></div>
<div class="card" id="fin" hidden><h2>¡Terminaste!</h2><div class="msg" id="resumen"></div>
<button class="sec" onclick="location.reload()">Jugar otra vez</button></div>
</main><script>
let jid;try{jid=localStorage.getItem('jid');if(!jid){jid=(crypto.randomUUID?crypto.randomUUID():String(Math.random()).slice(2)+Date.now()).replace(/-/g,'');localStorage.setItem('jid',jid)}}catch(e){jid='web'+Date.now()}
let qs=[],i=0,cuenta={mayoria:0,minoria:0,empate:0};
const $=id=>document.getElementById(id);
fetch('/api/categorias').then(r=>r.json()).then(cs=>{$('cat').innerHTML='<option value="">🎲 Todas (aleatorio)</option>'+cs.map(c=>`<option value="${c.id}">${c.emoji} ${c.nombre}</option>`).join('')});
async function empezar(){const r=await fetch(`/api/preguntas?n=${$('n').value}&categoria=${$('cat').value}`);qs=await r.json();i=0;$('menu').hidden=true;$('juego').hidden=false;mostrar()}
function mostrar(){const q=qs[i];$('res').hidden=true;$('a').disabled=$('b').disabled=false;$('preg').textContent=q.pregunta;$('a').textContent=q.opcion_a;$('b').textContent=q.opcion_b;$('cont').textContent=`Pregunta ${i+1} de ${qs.length}`;$('prog').style.width=(i/qs.length*100)+'%'}
async function votar(o){$('a').disabled=$('b').disabled=true;const q=qs[i];
const r=await fetch('/api/votar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pregunta_id:q.id,jugador_id:jid,opcion:o})});const d=await r.json();
if(!d.votos_a&&d.votos_a!==0){alert(d.error||'Error');return}
const eleg=d.tu_opcion||o;const p=eleg=='A'?d.votos_a:d.votos_b,otro=eleg=='A'?d.votos_b:d.votos_a;
cuenta[p==otro?'empate':p>otro?'mayoria':'minoria']++;
$('graf').src=`/api/grafico/${q.id}.png?eleccion=${eleg}&t=${Date.now()}`;
$('aviso').textContent=d.duplicado?'Ya habías votado esta pregunta: tu voto no se cuenta dos veces.':'';
$('res').hidden=false;$('sig').textContent=i==qs.length-1?'Ver resumen 🏁':'Siguiente ▶'}
$('a').onclick=()=>votar('A');$('b').onclick=()=>votar('B');
function siguiente(){i++;if(i>=qs.length){$('juego').hidden=true;$('fin').hidden=false;
$('resumen').textContent=`Coincidiste con la opción más votada en ${cuenta.mayoria} preguntas, con la menos votada en ${cuenta.minoria} y hubo ${cuenta.empate} empates.`}else mostrar()}
</script></body></html>"""
