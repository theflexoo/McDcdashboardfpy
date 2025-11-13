import threading
import os
import bot
import web

if __name__ == "__main__":
    # Start bot in background thread (daemon so it stops with main process)
    t = threading.Thread(target=bot.start_bot, daemon=True)
    t.start()

    # Start Flask web app in main thread (Render expects the webserver in main thread)
    port = int(os.getenv("PORT", 10000))
    web.app.run(host="0.0.0.0", port=port, debug=False)