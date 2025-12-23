from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import html
import re

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
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 2MB
ALLOWED_IMAGE_PREFIX = re.compile(r"^data:image/(png|jpeg|jpg|webp);base64,")

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SOCKET EVENTS ----------------

@socketio.on("connect")
def on_connect():
    username = f"User-{random.randint(1000, 9999)}"
    online_users[request.sid] = username

    emit("init_user", {"user": username})
    emit("users_update", list(online_users.values()), broadcast=True)

    print(f"[+] {username} connected")

@socketio.on("disconnect")
def on_disconnect():
    user = online_users.pop(request.sid, None)
    emit("users_update", list(online_users.values()), broadcast=True)

    if user:
        print(f"[-] {user} disconnected")

@socketio.on("send_message")
def handle_message(data):
    user = online_users.get(request.sid)
    if not user:
        return

    msg = data.get("msg")
    image = data.get("image")

    # --- TEXT MESSAGE ---
    if msg:
        safe_msg = html.escape(str(msg))[:1000]

        emit("receive_message", {
            "user": user,
            "msg": safe_msg
        }, broadcast=True)

    # --- IMAGE MESSAGE ---
    elif image:
        if not isinstance(image, str):
            return

        # Validate base64 header
        if not ALLOWED_IMAGE_PREFIX.match(image):
            return

        # Approx size check
        image_size = len(image) * 3 // 4
        if image_size > MAX_IMAGE_SIZE:
            return

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
    socketio.run(
        app,
        host="127.0.0.1",
        port=5001,
        allow_unsafe_werkzeug=True
    )
