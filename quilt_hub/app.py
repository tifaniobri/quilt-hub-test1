import os
from flask import Flask, render_template, request, url_for
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid
from PIL import Image, ImageOps, ImageFilter
import numpy as np
ALLOWED_EXTS = {"png", "jpg", "jpeg", "webp"}
def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


@app.route("/tools")
def tools():
    return render_template("tools.html")

@app.route("/tools/color-palette", methods=["GET", "POST"])
def color_palette():
    pairs = []
    mode = "auto"

    if request.method == "POST":
        mode = request.form.get("mode", "auto")
        files = request.files.getlist("images")

        static_dir = Path(app.static_folder)  # works locally and on Render
        upload_dir = static_dir / "uploads"
        processed_dir = static_dir / "processed"
        upload_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            if not f or not f.filename:
                continue
            if not allowed_file(f.filename):
                continue
                
            # Make filename safe + unique
            original_name = secure_filename(f.filename)
            stem, dot, ext = original_name.rpartition(".")
            ext = ext if dot else "png"

            uid = uuid.uuid4().hex[:10]
            saved_name = f"{stem or 'image'}_{uid}.{ext}"
            saved_path = upload_dir / saved_name
            f.save(saved_path)

            # Create BW/Grey palette version
            img0 = Image.open(saved_path).convert("L")
            arr0 = np.array(img0)

            # Metrics to detect "pale fabric" images
            p10 = float(np.quantile(arr0, 0.10))
            p90 = float(np.quantile(arr0, 0.90))
            dyn = p90 - p10
            mean = float(arr0.mean())

            # Gentle mode triggers when image is BOTH light AND low-contrast
            if mode == "gentle":
                is_gentle = True
            elif mode == "strong":
                is_gentle = False
            else:
                is_gentle = (mean > 175) and (dyn < 45)

            if is_gentle:
                # GENTLE MODE: keep it mostly light gray, very little black
                img = img0  # IMPORTANT: no autocontrast here

                t_black = int(np.quantile(arr0, 0.01))   # only darkest 1% becomes black
                t_white = int(np.quantile(arr0, 0.98))   # only brightest 2% becomes white
                mid = 225                                # very light gray

                pal = img.point(lambda p: 0 if p < t_black else (mid if p < t_white else 255), mode="L")
            else:
                # STRONG MODE: restore deep blacks and separation
                img = ImageOps.autocontrast(img0, cutoff=0)  # stronger than before

                # Darken shadows a bit (gamma > 1 darkens)
                gamma = 1.35
                img = img.point(lambda p: int(255 * ((p / 255) ** gamma)), mode="L")

                arr = np.array(img)
                t_black = int(np.quantile(arr, 0.45))    # MORE black in shadows
                t_white = int(np.quantile(arr, 0.85))
                mid = 110                                # darker mid-gray

                pal = img.point(lambda p: 0 if p < t_black else (mid if p < t_white else 255), mode="L")

            processed_name = f"{stem or 'image'}_{uid}_bw.png"
            processed_path = processed_dir / processed_name
            pal.save(processed_path, format="PNG")

            pairs.append({
                "original": f"uploads/{saved_name}",
                "bw": f"processed/{processed_name}",
            })

    return render_template("color_palette.html", pairs=pairs, mode=mode)

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug)
