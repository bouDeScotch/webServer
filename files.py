from camera import CAM_INDEX
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    send_from_directory,
    flash,
    render_template,
    Response,
    abort,
    stream_with_context,
)
from flask_socketio import SocketIO
import os
import random
import string
import cv2
import sys
from infos import get_system_info
import time
import get_random_file
import requests
from urllib.parse import quote
import queue
import sounddevice as sd


CAM_INDEX = 0

UPLOAD_FOLDER = "uploads"
MAX_TOTAL_SIZE = 4 * 1024**3  # 4 Go
MAX_FILE_SIZE = 4 * 1024**3  # 4 Go

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "supersecretkey"  # nécessaire pour flash()

socketio = SocketIO(app, cors_allowed_origins="*")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

audio_q = queue.Queue()


def get_folder_size(folder):
    total = 0
    for dirpath, _, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total


def cleanup_folder(required_space):
    """Supprime les fichiers les plus anciens jusqu'à libérer l'espace nécessaire"""
    files = [
        (os.path.getctime(os.path.join(UPLOAD_FOLDER, f)), f)
        for f in os.listdir(UPLOAD_FOLDER)
    ]
    files.sort()  # du plus ancien au plus récent
    freed = 0
    for _, f in files:
        fp = os.path.join(UPLOAD_FOLDER, f)
        size = os.path.getsize(fp)
        os.remove(fp)
        freed += size
        if freed >= required_space:
            break


def generate_file_list_cache(directory="~"):
    with open(".file_list_cache.txt", "w") as f:
        f.write("\n".join(get_random_file.get_all_files(directory)))


def short_id(n=7):
    chars = string.ascii_letters + string.digits  # a-zA-Z0-9
    return "".join(random.choices(chars, k=n))


@app.route("/cat/<path:text>")
def cat_says(text):
    safe_text = quote(text)
    url = f"https://cataas.com/cat/says/{safe_text}"

    try:
        r = requests.get(url, timeout=8, stream=True)
    except Exception as e:
        abort(502)

    if r.status_code != 200:
        abort(r.status_code)

    content_type = r.headers.get("Content-Type", "image/jpeg")
    headers = {
        "Content-Type": content_type,
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    return Response(
        stream_with_context(r.iter_content(chunk_size=8192)),
        headers=headers,
        status=200,
    )


@app.route("/cam", methods=["GET"])
def get_camera():
    global current_cam_pic_idx

    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_ANY)
    if not cap.isOpened():
        print("[ERREUR] Impossible d'ouvrir la caméra", file=sys.stderr)
        return render_template("cam_error.html")
    print("[INFO] Caméra ouverte pour capture unique.")
    ret, frame = cap.read()
    cap.release()
    data = ""
    data = cv2.imencode(".jpg", frame)[1].tobytes()
    response = app.response_class(data, mimetype="image/jpeg")
    # Enregistrer l'image dans un fichier temporaire pour affichage plus simple
    # Delete old picture if exists
    if os.path.exists(path=os.path.join(app.root_path, "static", current_cam_pic_idx)):
        os.remove(path=os.path.join(app.root_path, "static", current_cam_pic_idx))
    # New picture idx
    current_cam_pic_idx = short_id(4)
    img_path = os.path.join(
        app.root_path, "static", current_cam_pic_idx + "_cam_capture.jpg"
    )
    with open(img_path, "wb") as f:
        f.write(data)
    return render_template(
        "cam.html",
        img_url=url_for("static", filename=current_cam_pic_idx + "_cam_capture.jpg"),
    )


@app.route("/favicon.ico", methods=["GET"])
def favicon():
    favicon_path = os.path.join(app.root_path, "favicon.ico")
    data = ""
    with open(favicon_path, "rb") as f:
        data = f.read()
        print(len(data))
    response = app.response_class(data, mimetype="image/vnd.microsoft.icon")
    return response


@app.route("/", methods=["GET", "POST"])
def upload_file():
    file_url = None
    if request.method == "POST":
        if "file" not in request.files:
            flash("Aucun fichier envoyé")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("Nom de fichier vide")
            return redirect(request.url)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            flash("Fichier trop volumineux")
            return redirect(request.url)
        # Nettoyage si dossier trop plein
        current_size = get_folder_size(UPLOAD_FOLDER)
        if current_size + size > MAX_TOTAL_SIZE:
            cleanup_folder(current_size + size - MAX_TOTAL_SIZE)
        # Génère un nom unique
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{short_id()}{ext}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(save_path)
        file_url = url_for("uploaded_file", filename=unique_name, _external=True)
    return render_template("index.html", file_url=file_url)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/stats", methods=["GET"])
def system_stats():
    try:
        # Appel de la fonction get_system_info()
        infos = get_system_info()

        # Génère une page HTML basique
        data = ""
        for k, v in infos.items():
            data += f"<tr><td>{k}</td><td>{v}</td></tr>\n"
        return render_template("stats.html", formatted_stats=data)

    except Exception as e:
        return f"<pre>Erreur lors de la récupération des infos système : {e}</pre>", 500


@app.route("/random", methods=["GET"])
def random_file():
    global last_file_list_generation, file_list, downloadIndexes

    if time.time() - last_file_list_generation > 3600:
        generate_file_list_cache()
        last_file_list_generation = time.time()
    file_list = []
    with open(".file_list_cache.txt", "r") as f:
        file_list = f.read().splitlines()

    downloadId = short_id(16)
    file_path = random.choice(file_list)
    downloadIndexes[downloadId] = {
        "generation_time": time.time(),
        "file_path": file_path,
    }
    try:
        downloadIndexes[downloadId]["file_size"] = os.path.getsize(file_path)
    except Exception:
        pass

    return render_template(
        "random.html",
        download_id=downloadId,
        file_path=file_path,
        file_size=downloadIndexes[downloadId]["file_size"],
    )


@app.route("/random/download/<download_id>", methods=["GET"])
def serve_random_file(download_id):
    global downloadIndexes

    if download_id not in downloadIndexes:
        return "<h1>Identifiant de téléchargement invalide.</h1>", 404

    entry = downloadIndexes[download_id]
    # Vérifie si le lien a expiré (10 minutes)
    if time.time() - entry["generation_time"] > 600:
        del downloadIndexes[download_id]
        return "<h1>Le lien de téléchargement a expiré.</h1>", 410

    file_path = entry["file_path"]
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    return send_from_directory(directory, filename, as_attachment=True)


@app.route("/style/<filepath>", methods=["GET"])
def serve_style_sheet(filepath):
    print("wahou")
    style_dir = os.path.join(app.root_path, "templates")
    return send_from_directory(style_dir, filepath)


if __name__ == "__main__":
    current_cam_pic_idx = short_id(4)
    last_file_list_generation = time.time()
    file_list = get_random_file.get_all_files()
    downloadIndexes = {}
    print(f"[INFO] {len(file_list)} fichiers indexés.")
    with open(".file_list_cache.txt", "w") as f:
        f.write("\n".join(file_list))
    print(
        f"[INFO] Cache mis à jour. Taille du cache : {os.path.getsize('.file_list_cache.txt')} octets."
    )

    try:
        app.run(host="0.0.0.0", port=8000, debug=True)
    except Exception as e:
        print(f"[ERROR] {e}")
