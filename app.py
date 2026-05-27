"""OCR Solutions – Flask OCR web app with Mega.nz cloud, checkpoints, keepalive"""

HEADER = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>OCR Solutions – {{ title }}</title>\n<style>\n* { margin: 0; padding: 0; box-sizing: border-box; font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; }\n:root { --primary: #0c1f33; --secondary: #125683; --accent: #7f89d4; --light: #ecf0f1; --dark: #2c3e50; --success: #27ae60; --git-color: #e24124; }\nbody { line-height: 1.6; color: #333; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }\nheader { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 1rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }\n.header-container { display: flex; justify-content: center; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }\n.logo h1 { font-size: 2rem; color: white; letter-spacing: 3px; }\n.logo span { color: var(--accent); font-weight: 300; letter-spacing: 1px; }\n.nav-tabs { display: flex; justify-content: center; max-width: 1200px; margin: 2rem auto; padding: 0 20px; gap: 1rem; flex-wrap: wrap; }\n.nav-tab { display: flex; align-items: center; gap: 10px; padding: 12px 25px; background: white; color: var(--primary); border-radius: 10px; text-decoration: none; font-weight: 600; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid transparent; }\n.nav-tab:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.15); border-color: var(--git-color); }\n.nav-tab.active { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; border-color: var(--git-color); }\n.hero { background: linear-gradient(135deg, var(--git-color), #6e5494); color: white; padding: 4rem 0; text-align: center; position: relative; overflow: hidden; }\n.hero:before { content: \'\'; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: url(\'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.1" d="M0,96L48,112C96,128,192,160,288,186.7C384,213,480,235,576,213.3C672,192,768,128,864,128C960,128,1056,192,1152,192C1248,192,1344,128,1392,96L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>\'); background-size: cover; background-position: center; }\n.hero-content { max-width: 800px; margin: 0 auto; padding: 0 20px; position: relative; z-index: 1; }\n.hero h2 { font-size: 2.8rem; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }\n.hero p { font-size: 1.3rem; margin-bottom: 2.5rem; }\n.upload-form { max-width: 600px; margin: 0 auto; }\n.upload-form input[type=file] { display: block; width: 100%; padding: 1rem; background: rgba(255,255,255,0.15); border: 2px dashed rgba(255,255,255,0.4); border-radius: 12px; color: white; cursor: pointer; margin-bottom: 1.5rem; transition: all 0.3s; }\n.upload-form input[type=file]:hover { border-color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.25); }\n.upload-form input[type=file]::file-selector-button { background: white; color: var(--git-color); border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; margin-right: 15px; cursor: pointer; }\n.form-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }\n.form-row select, .form-row input[type=number] { flex: 1; min-width: 140px; padding: 12px 16px; border-radius: 10px; border: 2px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.15); color: white; font-size: 0.95rem; cursor: pointer; }\n.form-row select option { background: var(--primary); color: white; }\n.form-row input[type=number]::placeholder { color: rgba(255,255,255,0.6); }\n.form-row input[type=number] { cursor: text; }\n.opt-group { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; justify-content: center; }\n.opt-group label { display: flex; align-items: center; gap: 8px; color: white; font-size: 0.95rem; cursor: pointer; padding: 8px 16px; background: rgba(255,255,255,0.1); border-radius: 8px; transition: all 0.3s; }\n.opt-group label:hover { background: rgba(255,255,255,0.2); }\n.opt-group input[type=checkbox] { width: 18px; height: 18px; cursor: pointer; accent-color: var(--accent); }\n.upload-btn { background: white; color: var(--git-color); border: none; padding: 14px 40px; border-radius: 10px; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.3s; width: 100%; }\n.upload-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }\n.upload-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }\n.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }\n.section-title { text-align: center; margin: 3rem 0 2rem; color: var(--dark); position: relative; }\n.section-title:after { content: \'\'; display: block; width: 80px; height: 4px; background: var(--git-color); margin: 10px auto; border-radius: 2px; }\n.content-section { margin-bottom: 2rem; padding: 2.5rem; border-radius: 15px; background-color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: transform 0.3s, box-shadow 0.3s; }\n.content-section:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }\n.content-section h2 { color: var(--dark); margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--git-color); display: inline-block; }\n.result-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 1.5rem; max-height: 60vh; overflow-y: auto; font-family: \'Courier New\', monospace; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 1rem 0; }\n.result-actions { display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; }\n.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border-radius: 10px; font-weight: 600; text-decoration: none; transition: all 0.3s; border: none; cursor: pointer; font-size: 1rem; }\n.btn-primary { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; }\n.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }\n.btn-secondary { background: white; color: var(--primary); border: 2px solid var(--primary); }\n.btn-secondary:hover { background: var(--primary); color: white; }\n.flash { padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; font-weight: 500; }\n.flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }\n.flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }\n.download-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }\n.download-table th { background: var(--primary); color: white; padding: 12px 15px; text-align: left; font-weight: 600; }\n.download-table td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; }\n.download-table tr:hover { background: #f1f5f9; }\n.tip-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-left: 6px solid #ffd700; padding: 2rem; margin: 2rem 0; border-radius: 12px; color: white; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3); position: relative; overflow: hidden; }\n.tip-box:before { content: \'\'; position: absolute; top: -50%; right: -50%; width: 100%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%); transform: rotate(45deg); }\n.tip-box h4 { color: #ffd700; margin-bottom: 1rem; display: flex; align-items: center; gap: 12px; font-size: 1.3rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }\n.tip-box p { font-size: 1.1rem; line-height: 1.7; margin-bottom: 0; text-shadow: 1px 1px 1px rgba(0,0,0,0.1); }\n.tip-icon { font-size: 1.5rem; }\n.formats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1.5rem; }\n.format-card { background: var(--light); padding: 1.2rem; border-radius: 10px; text-align: center; font-weight: 600; color: var(--dark); font-size: 0.95rem; transition: all 0.3s; }\n.format-card:hover { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; transform: translateY(-2px); }\n.loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(12,31,51,0.92); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; }\n.loading-overlay.show { display: flex; }\n.spinner { width: 60px; height: 60px; border: 5px solid rgba(255,255,255,0.2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }\n@keyframes spin { to { transform: rotate(360deg); } }\n.loading-overlay p { color: white; font-size: 1.4rem; margin-top: 2rem; font-weight: 500; }\n.loading-overlay small { color: rgba(255,255,255,0.6); margin-top: 0.5rem; font-size: 0.9rem; }\n.home-icon { position: fixed; top: 20px; right: 20px; width: 50px; height: 50px; background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; text-decoration: none; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: all 0.3s ease; border: 2px solid white; }\n.home-icon:hover { background: linear-gradient(135deg, #e74c3c, var(--git-color)); transform: scale(1.1) translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); text-decoration: none; color: white; }\n@media (max-width: 768px) { .header-container { flex-direction: column; text-align: center; } .nav-tabs { flex-direction: column; align-items: center; } .nav-tab { width: 100%; max-width: 300px; justify-content: center; } .hero h2 { font-size: 2rem; } .hero { padding: 3rem 0; } .content-section { padding: 1.5rem; } .result-actions { flex-direction: column; } .home-icon { width: 45px; height: 45px; font-size: 18px; top: 15px; right: 15px; } .logo h1 { font-size: 1.4rem; } .form-row { flex-direction: column; } .opt-group { flex-direction: column; align-items: center; } }\n@media (max-width: 480px) { .hero h2 { font-size: 1.5rem; } .hero p { font-size: 1rem; } .logo h1 { font-size: 1.2rem; } .home-icon { width: 40px; height: 40px; font-size: 16px; top: 12px; right: 12px; } }\n</style>\n</head>\n<body>\n<div class="loading-overlay" id="loading-overlay">\n    <div class="spinner"></div>\n    <p>⏳ Processing your file...</p>\n    <small>This may take a moment for large documents</small>\n</div>\n<header>\n    <div class="header-container">\n        <div class="logo">\n            <h1>OCR <span>Solutions</span></h1>\n        </div>\n    </div>\n</header>\n<a href="/" class="home-icon" title="Home">🏠</a>\n<div class="nav-tabs">\n    <a href="/" class="nav-tab {{ \'active\' if active == \'upload\' else \'\' }}">📄 Upload</a>\n    <a href="/downloads" class="nav-tab {{ \'active\' if active == \'downloads\' else \'\' }}">📦 Downloads</a>\n</div>\n<div class="container">\n{% for cat, msg in flashes %}\n<div class="flash {{ cat }}">{{ msg }}</div>\n{% endfor %}\n</div>\n'

CLOSING = "<script>\n(function() {\n    var form = document.getElementById('upload-form');\n    if (form) {\n        form.addEventListener('submit', function() {\n            document.getElementById('loading-overlay').classList.add('show');\n        });\n    }\n})();\n</script>\n</body>\n</html>\n"


import os
import re
import json
import tempfile
import threading
import time
from io import BytesIO
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, send_file, jsonify
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import requests

MEGA_AVAILABLE = False
try:
    from mega import Mega
    MEGA_AVAILABLE = True
except ImportError:
    Mega = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

results = {}
download_history = {}
progress_store = {}

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".csv", ".tsv", ".md", ".json", ".xml"}
OFFICE_EXTS = {".docx", ".xlsx"}
SUPPORTED_EXTS = IMG_EXTS | {".pdf"} | TEXT_EXTS | OFFICE_EXTS

LANG_OPTIONS = {
    "auto": "Auto Detect",
    "tam+eng": "Tamil + English",
    "tam": "Tamil", "eng": "English", "hin": "Hindi",
    "tel": "Telugu", "mal": "Malayalam", "kan": "Kannada",
    "guj": "Gujarati", "ben": "Bengali", "mar": "Marathi",
    "urd": "Urdu", "san": "Sanskrit",
}

MEGA_EMAIL = os.environ.get("MEGA_EMAIL", "")
MEGA_PASSWORD = os.environ.get("MEGA_PASSWORD", "")
KEEPALIVE_URL = os.environ.get("KEEPALIVE_URL", "")
_keepalive_started = False
_mega_client = None
_mega_lock = threading.Lock()


def get_mega():
    global _mega_client
    if not MEGA_AVAILABLE or not MEGA_EMAIL or not MEGA_PASSWORD:
        return None
    if _mega_client is not None:
        return _mega_client
    with _mega_lock:
        if _mega_client is not None:
            return _mega_client
        try:
            _mega_client = Mega().login(MEGA_EMAIL, MEGA_PASSWORD)
        except Exception:
            _mega_client = None
    return _mega_client


def mega_upload_text(text, remote_name):
    m = get_mega()
    if m is None:
        return None
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            tmp = f.name
        file = m.upload(tmp, dest_filename=remote_name)
        return m.get_link(file)
    except Exception:
        return None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def start_keepalive():
    global _keepalive_started
    if _keepalive_started or not KEEPALIVE_URL:
        return
    _keepalive_started = True
    def _ping():
        while True:
            try:
                requests.get(KEEPALIVE_URL, timeout=10)
            except Exception:
                pass
            time.sleep(300)
    t = threading.Thread(target=_ping, daemon=True)
    t.start()


@app.before_request
def _init_background():
    start_keepalive()


def detect_language(text):
    tamil = len(re.findall(r"[\u0B80-\u0BFF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    if tamil > latin * 2:
        return "Tamil"
    elif tamil > latin / 2:
        return "Tamil + English"
    elif latin > 0:
        return "English"
    return "Unknown"


def ocr_pdf(filepath, lang="tam+eng", dpi=300, start_page=1, end_page=None,
            progress_key=None, mega_cp=False):
    pages = []
    page_num = max(1, start_page)
    last_mega_cp = 0

    if progress_key and progress_key in progress_store:
        cp = progress_store[progress_key]
        page_num = cp["page"] + 1
        pages = list(cp["texts"])

    while True:
        if end_page is not None and page_num > end_page:
            break
        try:
            images = convert_from_path(filepath, dpi=dpi, first_page=page_num, last_page=page_num)
            if not images:
                break
            text = pytesseract.image_to_string(images[0], lang=lang)
            images[0].close()
            if text.strip():
                pages.append("--- Page %d ---\n%s" % (page_num, text))

            if progress_key:
                progress_store[progress_key] = {"page": page_num, "texts": list(pages)}

            if mega_cp and progress_key and (page_num - last_mega_cp) >= 10:
                cp_text = "\n\n".join(pages)
                mega_upload_text(
                    json.dumps({"page": page_num, "text": cp_text}, ensure_ascii=False),
                    "checkpoint_%s.json" % progress_key
                )
                last_mega_cp = page_num

            page_num += 1
        except Exception:
            break

    if progress_key:
        progress_store.pop(progress_key, None)

    return "\n\n".join(pages)


def ocr_image(filepath, lang="tam+eng"):
    with Image.open(filepath) as img:
        text = pytesseract.image_to_string(img, lang=lang)
    return text


def extract_docx_text(filepath):
    if DocxDocument is None:
        return ""
    doc = DocxDocument(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_xlsx_text(filepath):
    if load_workbook is None:
        return ""
    wb = load_workbook(filepath, read_only=True, data_only=True)
    lines = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            vals = [str(c) for c in row if c is not None]
            if vals:
                lines.append("\t".join(vals))
    wb.close()
    return "\n".join(lines)


def read_text_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_text(filepath, ext, lang="tam+eng", start_page=1, end_page=None,
                 progress_key=None, mega_cp=False):
    if ext == ".pdf":
        return ocr_pdf(filepath, lang, start_page=start_page, end_page=end_page,
                       progress_key=progress_key, mega_cp=mega_cp)
    elif ext in IMG_EXTS:
        return ocr_image(filepath, lang)
    elif ext == ".docx":
        return extract_docx_text(filepath)
    elif ext == ".xlsx":
        return extract_xlsx_text(filepath)
    elif ext in TEXT_EXTS:
        return read_text_file(filepath)
    return ""


def build_lang_options(selected):
    opts = ""
    for val, label in LANG_OPTIONS.items():
        sel = " selected" if val == selected else ""
        opts += "<option value=\"%s\"%s>%s</option>" % (val, sel, label)
    return opts


def build_formats_cards():
    formats = [
        "PDF Documents", "PNG / JPEG / WEBP", "TIFF / BMP / GIF",
        "Word (DOCX)", "Excel (XLSX)", "CSV / TXT / JSON",
    ]
    return "".join("<div class=\"format-card\">%s</div>" % f for f in formats)


def build_opt_checkbox(name, label, checked=True):
    chk = " checked" if checked else ""
    return "<label><input type=\"checkbox\" name=\"%s\"%s> %s</label>" % (name, chk, label)


def mega_status():
    if not MEGA_AVAILABLE:
        return "not_installed"
    if MEGA_EMAIL and MEGA_PASSWORD:
        return "configured"
    return "no_creds"


def render_page(title, content, active, flashes=None):
    if flashes is None:
        flashes = []
    return render_template_string(HEADER + content + CLOSING, title=title, active=active, flashes=flashes)


@app.route("/progress/<session_id>")
def get_progress(session_id):
    info = progress_store.get(session_id)
    if info is None:
        return jsonify({"found": False})
    return jsonify({"found": True, "page": info.get("page", 0), "has_text": bool(info.get("texts", []))})


@app.route("/", methods=["GET", "POST"])
def index():
    result_html = None
    filename = ""
    session_id = ""
    word_count = 0
    detected_lang = ""
    mega_link = ""

    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Please select a file to upload.", "error")
            return redirect("/")

        ext = os.path.splitext(f.filename.lower())[1]
        lang = request.form.get("lang", "tam+eng")
        start_page = request.form.get("start_page", "1")
        end_page = request.form.get("end_page", "")
        save_mega = request.form.get("save_mega") == "on"

        if ext not in SUPPORTED_EXTS:
            flash("Unsupported file type: " + ext, "error")
            return redirect("/")

        sp = max(1, int(start_page)) if start_page.isdigit() else 1
        ep = int(end_page) if end_page.isdigit() else None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                f.save(tmp.name)
                tmppath = tmp.name

            ocr_lang = "tam+eng" if lang == "auto" else lang
            session_id = os.urandom(8).hex()
            progress_key = session_id if ext == ".pdf" else None

            text = extract_text(tmppath, ext, lang=ocr_lang, start_page=sp, end_page=ep,
                                progress_key=progress_key, mega_cp=save_mega)
            os.unlink(tmppath)

            if not text.strip():
                flash("No text could be extracted.", "error")
                return redirect("/")

            if lang == "auto":
                detected_lang = detect_language(text)

            results[session_id] = text
            filename = f.filename
            word_count = len(text.split())

            if session_id not in download_history:
                download_history[session_id] = []
            download_history[session_id].insert(0, {
                "filename": filename,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "words": word_count,
            })

            if save_mega:
                link = mega_upload_text(text, "ocr_%s_%s.txt" % (session_id, filename))
                if link:
                    mega_link = link

            detected_html = ""
            if detected_lang:
                detected_html = "<p style=\"color:#666;margin-bottom:1rem;\">Detected language: <strong>%s</strong></p>" % detected_lang

            mega_html = ""
            if mega_link:
                mega_html = """<div class="result-actions" style="margin-top:1rem;">
    <a href="%s" target="_blank" class="btn btn-primary" style="background:linear-gradient(135deg,#c43c3c,#e74c3c);">🌐 Download from Mega</a>
</div>
<p style="color:#666;font-size:0.85rem;margin-top:0.5rem;">Saved to Mega Cloud ✓</p>""" % mega_link

            result_html = """<div class="hero">
    <div class="hero-content">
        <h2>✓ Text Extracted Successfully</h2>
        <p>%(wc)s words • %(fn)s</p>
        <a href="/" class="upload-btn" style="display:inline-block;width:auto;padding:12px 30px;text-decoration:none;">🔄 Process Another</a>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>📄 %(fn)s</h2>
        <p style="color:#666;margin-bottom:1rem;">%(wc)s words extracted</p>
        %(det)s
        <div class="result-box">%(txt)s</div>
        <div class="result-actions">
            <a href="/download/%(sid)s" class="btn btn-primary">📥 Download .txt</a>
            <a href="/" class="btn btn-secondary">🔄 Process Another</a>
        </div>
        %(mega)s
    </div>
</div>""" % {"wc": word_count, "fn": filename, "sid": session_id, "txt": text, "det": detected_html, "mega": mega_html}

        except Exception as e:
            flash("Error processing file: " + str(e), "error")
            return redirect("/")

    if not result_html:
        lang_sel = build_lang_options("tam+eng")
        formats_cards = build_formats_cards()

        mega_checks = ""
        ms = mega_status()
        if ms == "configured":
            mega_checks = build_opt_checkbox("save_mega", "Save to Mega Cloud", True)

        extra = ""
        if mega_checks:
            extra = '<div class="opt-group">' + mega_checks + '</div>'

        content = """<div class="hero">
    <div class="hero-content">
        <h2>Extract Text from Any Document</h2>
        <p>Upload PDFs, images, Word, Excel, or text files — get Tamil + English OCR in seconds</p>
        <form method="post" enctype="multipart/form-data" class="upload-form" id="upload-form">
            <input type="file" name="file" id="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp,.gif,.docx,.xlsx,.csv,.txt" required>
            <div class="form-row">
                <select name="lang" id="lang">%s</select>
                <input type="number" name="start_page" placeholder="From page" min="1" value="1" title="Start page (PDF only)">
                <input type="number" name="end_page" placeholder="To page (auto)" min="1" title="End page, leave empty for all pages">
            </div>
            %s
            <button type="submit" class="upload-btn">🔍 Extract Text</button>
        </form>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>💡 How It Works</h2>
        <p>Upload any supported file and our engine extracts text for you. PDFs and images use Tesseract OCR, while Office and text files are read directly.</p>
        <div class="tip-box">
            <h4><span class="tip-icon">⚡</span> Pro Tip</h4>
            <p>For best OCR results, use high-resolution images (300 DPI+). Enable \"Save to Mega Cloud\" to get a share link. The server stays alive automatically during long processing.</p>
        </div>
    </div>
    <div class="content-section">
        <h2>📦 Supported Formats</h2>
        <div class="formats-grid">%s</div>
    </div>
</div>""" % (lang_sel, extra, formats_cards)
    else:
        content = result_html

    return render_page("Upload & Extract Text", content, "upload")


@app.route("/downloads")
def downloads():
    all_items = []
    for sid, items in download_history.items():
        for item in items:
            all_items.append((sid, item))
    all_items.sort(key=lambda x: x[1]["date"], reverse=True)

    if all_items:
        rows = ""
        for sid, item in all_items:
            rows += """<tr>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td><a href="/download/%s" class="btn btn-primary" style="padding:6px 16px;font-size:0.85rem;">📥 Download</a></td>
            </tr>""" % (item["filename"], item["date"], item["words"], sid)
        content = """<div class="container">
    <div class="section-title"><h2>📦 Download History</h2></div>
    <div class="content-section">
        <table class="download-table">
            <thead><tr><th>File Name</th><th>Date</th><th>Words</th><th>Action</th></tr></thead>
            <tbody>%s</tbody>
        </table>
    </div>
</div>""" % rows
    else:
        content = """<div class="container">
    <div class="section-title"><h2>📦 Download History</h2></div>
    <div class="content-section" style="text-align:center;padding:4rem 2rem;">
        <p style="font-size:1.2rem;color:#666;">No downloads yet.</p>
        <p style="margin-top:1rem;"><a href="/" class="btn btn-primary">📄 Upload a file</a></p>
    </div>
</div>"""
    return render_page("Downloads", content, "downloads")


@app.route("/download/<session_id>")
def download_file(session_id):
    text = results.get(session_id)
    if text is None:
        flash("Download not found or expired.", "error")
        return redirect("/")
    return send_file(
        BytesIO(text.encode("utf-8")),
        mimetype="text/plain",
        as_attachment=True,
        download_name="ocr_result.txt",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
