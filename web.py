from flask import Flask, jsonify, render_template
import os
from bot import server_status
# Flask app expects templates in templates/ and static in static/
app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/api/online")
def api_online():
    # Return the live server_status. It's already German-ready.
    return jsonify(server_status)

@app.route("/")
def index():
    return render_template("dashboard.html")

def start_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)