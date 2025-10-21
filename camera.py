# cam_server.py — un seul fichier, ne crée PAS de fenêtres GUI
from flask import Flask, Response, render_template_string, send_file
import cv2
import threading
import time
import signal
import sys

app = Flask(__name__)

# Config
CAM_INDEX = 0  # change 0->1->2 si nécessaire
HOST = "0.0.0.0"
PORT = 8000

# Variables partagées
frame_lock = threading.Lock()
latest_frame = None
running = True

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Flux caméra</title>
<style>
  body{font-family:Arial,Helvetica,sans-serif;background:#f5f7fa;margin:0;display:flex;flex-direction:column;align-items:center;min-height:100vh;}
  header{width:100%;background:#0b5ed7;color:#fff;padding:1rem;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,0.08);}
  main{padding:2rem;display:flex;flex-direction:column;align-items:center;gap:1rem;}
  img{max-width:90vw;border-radius:8px;border:6px solid #fff;box-shadow:0 10px 30px rgba(11,94,215,0.12);}
  button{background:#0b5ed7;color:#fff;border:none;padding:.6rem 1rem;border-radius:6px;cursor:pointer}
  footer{margin-top:auto;padding:1rem;color:#666}
</style>
</head>
<body>
<header><h1>Flux caméra — Serveur Python</h1></header>
<main>
  <p>Flux en direct :</p>
  <object data="/video_feed" type="multipart/x-mixed-replace" width="640" height="480"></object>
  <div>
    <button onclick="snapshot()">Prendre un snapshot</button>
  </div>
  <p id="status"></p>
</main>
<footer>&copy; 2025</footer>

<script>
async function snapshot(){
  try {
    const resp = await fetch('/snapshot');
    if(!resp.ok){ document.getElementById('status').textContent = 'Erreur snapshot'; return; }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const w = window.open('');
    w.document.write('<img src="'+url+'" style="max-width:100%;">');
  } catch(e){
    document.getElementById('status').textContent = 'Erreur: '+e;
  }
}
</script>
</body>
</html>
"""


def camera_worker(index):
    global latest_frame, running
    cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    if not cap.isOpened():
        print(f"[ERREUR] Impossible d'ouvrir la caméra index={index}", file=sys.stderr)
        running = False
        return
    print("[INFO] Caméra ouverte.")
    # Optionnel : régler résolution (décommenter si besoin)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    while running:
        ret, frame = cap.read()
        if not ret:
            # attente courte si échec, évite burn CPU
            time.sleep(0.05)
            continue
        # Optionnel : traitement ici (filtre, overlay, redimension)
        with frame_lock:
            latest_frame = frame.copy()
        # petite attente pour limiter la fréquence si besoin
        time.sleep(0.01)
    cap.release()
    print("[INFO] Caméra fermée.")


def encode_frame_jpeg(frame):
    ret, buf = cv2.imencode(".jpg", frame)
    if not ret:
        return None
    return buf.tobytes()


def gen_frames():
    global running
    while running:
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()
        if frame is None:
            time.sleep(0.05)
            continue
        # Redimension
        frame = cv2.resize(frame, (320, 240))
        # Encodage JPEG compressé
        ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        if not ret:
            continue
        frame_bytes = buf.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/video_feed")
def video_feed():
    # Ne pas buffer, renvoyer directement le flux MJPEG
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/snapshot")
def snapshot():
    with frame_lock:
        frame = None if latest_frame is None else latest_frame.copy()
    if frame is None:
        return ("No frame available", 503)
    jpg = encode_frame_jpeg(frame)
    if jpg is None:
        return ("Encoding failed", 500)
    return Response(jpg, mimetype="image/jpeg")


def handle_signal(sig, frame):
    global running
    print("\n[INFO] Arrêt demandé, fermeture...")
    running = False


if __name__ == "__main__":
    # catch Ctrl+C
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Lancer le thread caméra
    cam_thread = threading.Thread(target=camera_worker, args=(CAM_INDEX,), daemon=True)
    cam_thread.start()

    # Lancer Flask (debug=False pour éviter reload qui recrée des threads)
    try:
        app.run(host=HOST, port=PORT, debug=False)
    except Exception as e:
        running = False
        cam_thread.join(timeout=2)
        print("[INFO] Serveur arrêté.")
