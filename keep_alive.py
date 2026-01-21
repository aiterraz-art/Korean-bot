from flask import Flask
from threading import Thread
import logging

# Filter out Flask startup logs to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "I'm alive! 🤖 K-Voice Coach is running."

import os

def run():
    # Render assigns a random port in the PORT env var. We must use it.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
