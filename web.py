from flask import Flask, jsonify, render_template_string
import os
from bot import server_status

app = Flask(__name__)

# --- API Route ---
@app.route("/api/online")
def api_online():
    return jsonify(server_status)

# --- HTML Template mit neuem Design ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Minecraft Server Dashboard</title>
<style>
body {
    margin:0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #0e0e0e;
    color: #f5f5f5;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 2rem;
}
.card {
    background: #1c1c1c;
    border-radius: 1rem;
    padding: 2rem;
    margin: 1rem;
    max-width: 600px;
    width: 90%;
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
}
h1 { font-size:2rem; margin-bottom:1rem; text-align:center; }
h2 { font-size:1.25rem; margin-bottom:0.5rem; }
.status-dot {
    display:inline-block;
    width:12px;
    height:12px;
    border-radius:50%;
    background:#e74c3c;
    margin-left:5px;
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0%,100% { transform: scale(0.8); opacity:0.6; }
    50% { transform: scale(1.2); opacity:1; }
}
ul { padding-left:1rem; }
li { margin-bottom:0.3rem; }
.footer { text-align:center; margin-top:1rem; font-size:0.8rem; color:#aaa; }
</style>
</head>
<body>
<div class="card">
    <h1>Minecraft Server Dashboard</h1>
    <h2>Status: <span id="status">lade…</span><span class="status-dot"></span></h2>
    <p>Uptime: <span id="uptime">–</span></p>
    <p>Letztes Update: <span id="last_update">–</span></p>
    <h2>Spieler online:</h2>
    <ul id="players"></ul>
    <h2>Heute online gewesen:</h2>
    <ul id="sessions"></ul>
    <div class="footer">Live-Update alle 10 Sekunden</div>
</div>
<script>
async function refresh() {
    try {
        const res = await fetch('/api/online');
        if(!res.ok) return;
        const data = await res.json();

        document.getElementById('status').textContent = data.status_text;
        document.getElementById('uptime').textContent = data.uptime;
        document.getElementById('last_update').textContent = data.last_update;

        const list = document.getElementById('players');
        list.innerHTML = '';
        if(!data.players || data.players.length===0){
            list.innerHTML='<li style="color:#888;font-style:italic;">Niemand online</li>';
        } else {
            data.players.forEach(p=>{
                const li=document.createElement('li');
                li.textContent=p;
                li.style.color='#2ecc71';
                list.appendChild(li);
            });
        }

        const sessList=document.getElementById('sessions');
        sessList.innerHTML='';
        const sessions=data.sessions||{};
        for(const [player, obj] of Object.entries(sessions)){
            const container=document.createElement('li');
            container.style.marginBottom='0.5rem';
            let text=player+' → ';
            const parts=obj.sessions.map(s=>{
                let start=new Date(s.start).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
                let end=s.end?new Date(s.end).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}):"jetzt";
                return start+'–'+end;
            });
            text+=parts.join(', ');
            let hours=Math.floor(obj.total_seconds/3600);
            let minutes=Math.floor((obj.total_seconds%3600)/60);
            text+=' ('+hours+'h '+minutes+'m)';
            container.textContent=text;
            sessList.appendChild(container);
        }

    } catch(err){ console.error(err); }
}
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

def start_web():
    port=int(os.getenv("PORT",10000))
    app.run(host="0.0.0.0", port=port, debug=False)