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

def run():
    # Use port 8080 or whatever the cloud provider expects (Render uses PORT env var, defaults to 10000 usually)
    # But usually 0.0.0.0 is needed.
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
