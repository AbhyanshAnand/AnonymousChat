from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import html
import re
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# SID -> username (SERVER AUTHORITY)
online_users = {}

# --- CONFIG ---
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_PREFIX = re.compile(r"^data:image/(png|jpeg|jpg|webp);base64,")

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# ---------------- SOCKET EVENTS ----------------

@socketio.on("connect")
def on_connect():
    username = f"User-{random.randint(1000, 9999)}"
    online_users[request.sid] = username

    emit("init_user", {"user": username})
    emit("users_update", list(online_users.values()), broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    online_users.pop(request.sid, None)
    emit("users_update", list(online_users.values()), broadcast=True)

@socketio.on("send_message")
def handle_message(data):
    user = online_users.get(request.sid)
    if not user:
        return

    msg = data.get("msg")
    image = data.get("image")

    # TEXT
    if msg:
        safe_msg = html.escape(str(msg))[:1000]
        emit("receive_message", {
            "user": user,
            "msg": safe_msg
        }, broadcast=True)

    # IMAGE
    elif image:
        if (
            isinstance(image, str)
            and ALLOWED_IMAGE_PREFIX.match(image)
            and (len(image) * 3 // 4) <= MAX_IMAGE_SIZE
        ):
            emit("receive_message", {
                "user": user,
                "image": image
            }, broadcast=True)

@socketio.on("typing")
def typing():
    user = online_users.get(request.sid)
    if user:
        emit("user_typing", {"user": user},
             broadcast=True, include_self=False)

@socketio.on("stop_typing")
def stop_typing():
    emit("user_stop_typing", broadcast=True, include_self=False)

# ---------------- RUN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True
    )
