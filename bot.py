import discord
from discord.ext import tasks
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# === .env laden ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
EXAROTON_API_KEY = os.getenv("EXAROTON_API_KEY")
SERVER_ID = os.getenv("SERVER_ID")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# === Discord Setup ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# === Variablen ===
online_since = None
last_players = set()
last_status = None
message_id = None
last_reset_day = None

# Spieler-Sessions: { "Name": [ {"start": datetime, "end": datetime|None}, ... ] }
player_sessions = {}

# === Globale Statusdaten für Web.py ===
server_status = {
    "status_text": "",
    "color": "#e74c3c",
    "players": [],
    "sessions": {},
    "uptime": "–",
    "last_update": None
}

# === API Abfrage ===
def get_server_status():
    url = f"https://api.exaroton.com/v1/servers/{SERVER_ID}"
    headers = {"Authorization": f"Bearer {EXAROTON_API_KEY}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        return data.get("data")
    except Exception as e:
        print("Fehler bei API:", e)
        return None

# Helper: convert color int to hex string (if later you store ints)
def color_to_hex(color):
    try:
        return f"#{color:06x}"
    except:
        # assume already hex string
        return str(color)

# === Discord Events ===
@client.event
async def on_ready():
    print(f"✅ Eingeloggt als {client.user}")
    # start loop if not already running
    try:
        if not status_loop.is_running():
            status_loop.start()
    except Exception:
        # in some edge cases, is_running() might fail; try starting anyway
        try:
            status_loop.start()
        except Exception as e:
            print("Konnte status_loop nicht starten:", e)

# === Status Loop (alle 10 Sekunden) ===
@tasks.loop(seconds=10)
async def status_loop():
    global online_since, last_status, last_players, message_id, last_reset_day, player_sessions, server_status

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        # Kanal nicht gefunden; evtl. Bot hat keine Rechte oder ID falsch
        print("Channel nicht gefunden, überprüfe CHANNEL_ID.")
        return

    server = get_server_status()
    if not server:
        # API-Problem: skip update but keep running
        return

    now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
    current_date = now_berlin.date()

    # --- Auto-Reset genau um Mitternacht (Berlin) ---
    if last_reset_day is None:
        last_reset_day = current_date
    elif current_date > last_reset_day:
        print("🌙 Mitternachts-Reset ausgeführt.")
        # close open sessions at midnight (set end to midnight time)
        for p, sessions in player_sessions.items():
            for s in sessions:
                if s.get("end") is None:
                    s["end"] = now_berlin
        # clear sessions for new day
        player_sessions = {}
        last_reset_day = current_date

    status_code = server.get("status")
    name = server.get("name", "Server")
    player_info = server.get("players", {}) or {}
    player_list = set(player_info.get("list", [])) if "list" in player_info else set()

    # --- Status Mapping ---
    status_map = {
        0: ("🟥 Offline", 0xe74c3c),
        1: ("🟩 Online", 0x2ecc71),
        2: ("🟨 Startet", 0xf1c40f),
        3: ("🟧 Stoppt", 0xe67e22),
        4: ("🔁 Neustartet", 0x3498db)
    }
    status_text, color_int = status_map.get(status_code, ("❓ Unbekannt", 0x95a5a6))
    color_hex = color_to_hex(color_int)

    # --- Online-Zeit (uptime) ---
    if status_code == 1:
        if online_since is None:
            online_since = now_berlin
        uptime_delta = now_berlin - online_since
        uptime_str = f"{uptime_delta.seconds//3600}h {(uptime_delta.seconds//60)%60}m"
    else:
        online_since = None
        uptime_str = "–"

    # --- Spieler Joins / Leaves tracken (mehrere sessions möglich) ---
    joined = player_list - last_players
    left = last_players - player_list

    for p in joined:
        player_sessions.setdefault(p, []).append({"start": now_berlin, "end": None})
    for p in left:
        if p in player_sessions:
            # find last open session
            for s in reversed(player_sessions[p]):
                if s.get("end") is None:
                    s["end"] = now_berlin
                    break

    last_players = player_list

    # --- Build session structure for display & web ---
    session_lines = []
    sessions_for_web = {}
    for player, sessions in player_sessions.items():
        total = timedelta()
        parts = []
        for s in sessions:
            s_start = s["start"]
            s_end = s.get("end") or now_berlin
            # format for embed display: local berlin HH:MM
            start_str = s_start.astimezone(ZoneInfo("Europe/Berlin")).strftime("%H:%M")
            end_str = s_end.astimezone(ZoneInfo("Europe/Berlin")).strftime("%H:%M") if s.get("end") else "…"
            parts.append(f"{start_str}–{end_str}")
            total += (s_end - s_start)
        total_str = f"{total.seconds//3600}h {(total.seconds//60)%60}m"
        session_lines.append(f"• {player} → {', '.join(parts)} ({total_str})")

        # sessions for web: iso with tz offset
        sessions_for_web[player] = {
            "sessions": [
                {"start": s["start"].astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
                 "end": s["end"].astimezone(ZoneInfo("Europe/Berlin")).isoformat() if s.get("end") else None}
                for s in sessions
            ],
            "total_seconds": int(total.total_seconds())
        }

    session_text = "\n".join(session_lines) if session_lines else "Noch keine Aktivität heute"

    # --- Serverstatus fuer Web.py aktualisieren (deutsche Strings) ---
    server_status["status_text"] = status_text
    server_status["color"] = color_hex
    server_status["players"] = list(player_list)
    server_status["sessions"] = sessions_for_web
    server_status["uptime"] = uptime_str
    server_status["last_update"] = now_berlin.strftime("%H:%M:%S CET")

    # --- Embed vorbereiten (Deutsch) ---
    embed = discord.Embed(
        title=f"{status_text} • {name}",
        description="💠 **Statusübersicht**",
        color=color_int if isinstance(color_int, int) else 0x95a5a6,
        timestamp=now_berlin
    )
    embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
    embed.add_field(name="👥 Spieler online", value=", ".join(player_list) if player_list else "Niemand online", inline=True)
    embed.add_field(name="📊 Heute online gewesen", value=session_text, inline=False)
    embed.set_footer(text=f"🕒 Letztes Update: {server_status['last_update']} • Automatisches Live-Update alle 10 Sekunden")

    # --- Nachricht verwalten: nur edit statt neues posten ---
    try:
        if (last_status != 1 and status_code == 1) or message_id is None:
            # delete old bot messages in channel (async-for inside async function)
            async for msg in channel.history(limit=50):
                if msg.author == client.user:
                    await msg.delete()
            msg = await channel.send(embed=embed)
            message_id = msg.id
        else:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(embed=embed)
            except Exception:
                msg = await channel.send(embed=embed)
                message_id = msg.id
    except Exception as e:
        print("Fehler beim Verwalten der Nachricht:", e)

    last_status = status_code

def start_bot():
    client.run(TOKEN)