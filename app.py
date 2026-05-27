"""OCR Solutions – Background OCR with progress tracking, Mega cloud, keepalive"""

import os
import re
import json
import tempfile
import threading
import time
from io import BytesIO
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, send_file, jsonify
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
import pytesseract
import requests

HTML_HEADER = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>OCR Solutions – {{ title }}</title>\n<style>\n* { margin: 0; padding: 0; box-sizing: border-box; font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif; }\n:root { --primary: #0c1f33; --secondary: #125683; --accent: #7f89d4; --light: #ecf0f1; --dark: #2c3e50; --success: #27ae60; --git-color: #e24124; }\nbody { line-height: 1.6; color: #333; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }\nheader { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 0.8rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }\n.header-container { display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }\n.logo h1 { font-size: 1.6rem; color: white; letter-spacing: 2px; }\n.logo span { color: var(--accent); font-weight: 300; letter-spacing: 1px; }\n.header-nav { display: flex; gap: 0.8rem; }\n.header-nav a { display: flex; align-items: center; gap: 6px; padding: 8px 18px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.95rem; transition: all 0.3s; color: rgba(255,255,255,0.8); }\n.header-nav a:hover { background: rgba(255,255,255,0.15); color: white; }\n.header-nav a.active { background: var(--git-color); color: white; }\n.page-title { text-align: center; margin: 2.5rem 0 1.5rem; color: var(--dark); }\n.page-title:after { content: \'\'; display: block; width: 80px; height: 4px; background: var(--git-color); margin: 10px auto; border-radius: 2px; }\n.container { max-width: 900px; margin: 0 auto; padding: 0 20px; }\n.card { margin-bottom: 2rem; padding: 2rem; border-radius: 15px; background: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }\n.card h2 { color: var(--dark); margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--git-color); display: inline-block; font-size: 1.3rem; }\n.doc-types { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.2rem; }\n.doc-type-btn { padding: 10px 18px; border-radius: 10px; border: 2px solid #dee2e6; background: white; color: var(--dark); font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 6px; }\n.doc-type-btn:hover { border-color: var(--accent); background: #f0f2ff; }\n.doc-type-btn.active { background: var(--git-color); color: white; border-color: var(--git-color); }\n.file-upload-area { border: 2px dashed #dee2e6; border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 1.2rem; cursor: pointer; transition: all 0.3s; position: relative; }\n.file-upload-area:hover { border-color: var(--accent); background: #f8f9ff; }\n.file-upload-area.has-file { border-color: var(--success); background: #f0fff4; }\n.file-upload-area input[type=file] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }\n.file-upload-area .upload-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }\n.file-upload-area p { color: #666; font-size: 0.95rem; }\n.file-upload-area .file-name { font-weight: 600; color: var(--success); margin-top: 0.3rem; }\n.form-row { display: flex; gap: 1rem; margin-bottom: 1.2rem; flex-wrap: wrap; }\n.form-row select, .form-row input[type=number] { flex: 1; min-width: 120px; padding: 11px 14px; border-radius: 8px; border: 2px solid #dee2e6; font-size: 0.95rem; background: white; color: #333; }\n.form-row select:focus, .form-row input:focus { outline: none; border-color: var(--accent); }\n.form-row label { display: flex; align-items: center; gap: 8px; color: #555; font-size: 0.9rem; white-space: nowrap; }\n.upload-btn { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; border: none; padding: 14px 30px; border-radius: 10px; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.3s; width: 100%; display: flex; align-items: center; justify-content: center; gap: 10px; }\n.upload-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }\n.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }\n.tip-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-left: 6px solid #ffd700; padding: 1.5rem; border-radius: 12px; color: white; box-shadow: 0 8px 25px rgba(102,126,234,0.3); position: relative; overflow: hidden; }\n.tip-box h4 { color: #ffd700; margin-bottom: 1rem; display: flex; align-items: center; gap: 10px; font-size: 1.1rem; }\n.tip-box p { font-size: 1rem; line-height: 1.6; }\n.formats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.8rem; margin-top: 1rem; }\n.format-card { background: var(--light); padding: 1rem; border-radius: 8px; text-align: center; font-weight: 600; color: var(--dark); font-size: 0.9rem; }\n.progress-page { text-align: center; padding: 1rem 0; }\n.task-id { font-family: monospace; background: #f0f0f0; padding: 4px 12px; border-radius: 6px; font-size: 0.9rem; color: #666; display: inline-block; margin-bottom: 0.5rem; }\n.progress-filename { font-size: 1.2rem; font-weight: 600; color: var(--dark); margin-bottom: 0.3rem; }\n.progress-status { display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 1.5rem 0; }\n.progress-stat { text-align: center; }\n.progress-stat .value { font-size: 1.5rem; font-weight: 700; color: var(--primary); }\n.progress-stat .label { font-size: 0.85rem; color: #888; }\n.progress-bar-bg { width: 100%; height: 24px; background: #e9ecef; border-radius: 12px; overflow: hidden; margin: 1rem 0; }\n.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--git-color), #e74c3c); border-radius: 12px; transition: width 0.5s; }\n.flash { padding: 0.8rem 1.2rem; border-radius: 8px; margin-bottom: 1rem; font-weight: 500; }\n.flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }\n.flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }\n.download-table { width: 100%; border-collapse: collapse; }\n.download-table th { background: var(--primary); color: white; padding: 10px 12px; text-align: left; font-weight: 600; font-size: 0.9rem; }\n.download-table td { padding: 10px 12px; border-bottom: 1px solid #dee2e6; font-size: 0.9rem; }\n.download-table tr:hover { background: #f1f5f9; }\n.download-table .status-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }\n.download-table .status-badge.processing { background: #fff3cd; color: #856404; }\n.download-table .status-badge.completed { background: #d4edda; color: #155724; }\n.download-table .status-badge.failed { background: #f8d7da; color: #721c24; }\n.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; border-radius: 8px; font-weight: 600; text-decoration: none; transition: all 0.3s; border: none; cursor: pointer; font-size: 0.9rem; }\n.btn-primary { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; }\n.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }\n.btn-secondary { background: white; color: var(--primary); border: 2px solid var(--primary); }\n.btn-secondary:hover { background: var(--primary); color: white; }\n.section-title { font-size: 1.1rem; font-weight: 700; color: var(--dark); margin: 1.5rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid var(--accent); display: inline-block; }\n.empty-state { text-align: center; padding: 3rem; color: #999; }\n.empty-state p { font-size: 1.1rem; margin-bottom: 1rem; }\n@media (max-width: 768px) { .header-container { flex-direction: column; gap: 0.5rem; } .header-nav a { font-size: 0.85rem; padding: 6px 12px; } .form-row { flex-direction: column; } .doc-types { justify-content: center; } .progress-status { gap: 1rem; } .logo h1 { font-size: 1.3rem; } }\n</style>\n</head>\n<body>\n<header>\n    <div class="header-container">\n        <div class="logo"><h1>OCR <span>Solutions</span></h1></div>\n        <nav class="header-nav">\n            <a href="/" class="{{ \'active\' if active == \'upload\' else \'\' }}">&#128228; Upload</a>\n            <a href="/downloads" class="{{ \'active\' if active == \'downloads\' else \'\' }}">&#128230; Downloads</a>\n        </nav>\n    </div>\n</header>\n<div class="container">\n{% for cat, msg in flashes %}\n<div class="flash {{ cat }}">{{ msg }}</div>\n{% endfor %}\n</div>\n'

HTML_CLOSING = '</body>\n</html>\n'

import os
import re
import json
import tempfile
import threading
import time
from io import BytesIO
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, send_file, jsonify
from pdf2image import convert_from_path, pdfinfo_from_path
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

tasks = {}
results = {}
tasks_order = []
tasks_lock = threading.Lock()
MEGA_EMAIL = os.environ.get("MEGA_EMAIL", "")
MEGA_PASSWORD = os.environ.get("MEGA_PASSWORD", "")
KEEPALIVE_URL = os.environ.get("KEEPALIVE_URL", "")
_keepalive_started = False
_mega_client = None
_mega_lock = threading.Lock()

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".csv", ".tsv", ".md", ".json", ".xml"}
OFFICE_EXTS = {".docx", ".xlsx"}
SUPPORTED_EXTS = IMG_EXTS | {".pdf"} | TEXT_EXTS | OFFICE_EXTS

DOC_TYPES = {
    "pdf": {"label": "PDF", "icon": "\U0001F4C4", "exts": [".pdf"]},
    "image": {"label": "Images", "icon": "\U0001F5BC", "exts": list(IMG_EXTS)},
    "word": {"label": "Word", "icon": "\U0001F4DD", "exts": [".docx"]},
    "excel": {"label": "Excel", "icon": "\U0001F4CA", "exts": [".xlsx"]},
    "data": {"label": "Data Files", "icon": "\U0001F4CB", "exts": list(TEXT_EXTS)},
}

LANG_OPTIONS = {
    "auto": "Auto Detect",
    "tam+eng": "Tamil + English",
    "tam": "Tamil", "eng": "English", "hin": "Hindi",
    "tel": "Telugu", "mal": "Malayalam", "kan": "Kannada",
    "guj": "Gujarati", "ben": "Bengali", "mar": "Marathi",
    "urd": "Urdu", "san": "Sanskrit",
}


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


def calculate_eta(task):
    elapsed = time.time() - task["start_time"]
    pages_done = task["current_page"]
    total = task["total_pages"]
    if total <= 0 or pages_done <= 0 or elapsed <= 0:
        return ""
    pages_per_sec = pages_done / elapsed
    remaining = (total - pages_done) / pages_per_sec if pages_per_sec > 0 else 0
    if remaining < 60:
        return f"{int(remaining)}s"
    elif remaining < 3600:
        return f"{int(remaining//60)}m {int(remaining%60)}s"
    else:
        return f"{int(remaining//3600)}h {int((remaining%3600)//60)}m"


def process_task(task_id, filepath, ext, lang, start_page, end_page, save_mega):
    task = tasks.get(task_id)
    if not task:
        return
    try:
        task["status"] = "processing"
        task["start_time"] = time.time()
        ocr_lang = "tam+eng" if lang == "auto" else lang
        task["language_display"] = LANG_OPTIONS.get(lang, lang)
        text_parts = []
        mega_cp = save_mega
        last_mega_cp = 0

        if ext == ".pdf":
            try:
                info = pdfinfo_from_path(filepath)
                task["total_pages"] = info["pages"]
            except Exception:
                task["total_pages"] = 0

            page_num = max(1, start_page)
            while True:
                if end_page is not None and page_num > end_page:
                    break
                try:
                    images = convert_from_path(filepath, dpi=300, first_page=page_num, last_page=page_num)
                    if not images:
                        break
                    page_text = pytesseract.image_to_string(images[0], lang=ocr_lang)
                    images[0].close()
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    task["current_page"] = page_num
                    task["progress"] = int((page_num / task["total_pages"]) * 100) if task["total_pages"] > 0 else 0
                    task["eta"] = calculate_eta(task)

                    if save_mega and (page_num - last_mega_cp) >= 10:
                        cp_text = "\n\n".join(text_parts)
                        mega_upload_text(cp_text, f"checkpoint_{task_id}_p{page_num}.txt")
                        last_mega_cp = page_num

                    page_num += 1
                except Exception:
                    break
            text = "\n\n".join(text_parts)
            task["progress"] = 100
        elif ext in IMG_EXTS:
            with Image.open(filepath) as img:
                text = pytesseract.image_to_string(img, lang=ocr_lang)
            task["current_page"] = 1
            task["total_pages"] = 1
            task["progress"] = 100
        elif ext == ".docx":
            if DocxDocument:
                doc = DocxDocument(filepath)
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            else:
                text = ""
            task["progress"] = 100
        elif ext == ".xlsx":
            if load_workbook:
                wb = load_workbook(filepath, read_only=True, data_only=True)
                lines = []
                for ws in wb.worksheets:
                    for row in ws.iter_rows(values_only=True):
                        vals = [str(c) for c in row if c is not None]
                        if vals:
                            lines.append("\t".join(vals))
                wb.close()
                text = "\n".join(lines)
            else:
                text = ""
            task["progress"] = 100
        elif ext in TEXT_EXTS:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            task["progress"] = 100
        else:
            text = ""
            task["progress"] = 100

        if text.strip():
            if lang == "auto":
                task["detected_language"] = detect_language(text)
            task["word_count"] = len(text.split())
            results[task_id] = text
            task["status"] = "completed"

            if save_mega:
                link = mega_upload_text(text, f"ocr_{task_id}.txt")
                if link:
                    task["mega_link"] = link
        else:
            task["status"] = "failed"
            task["error"] = "No text could be extracted"

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
    finally:
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass


def render_page(title, content, active, flashes=None):
    if flashes is None:
        flashes = []
    return render_template_string(HTML_HEADER + content + HTML_CLOSING, title=title, active=active, flashes=flashes)


@app.route("/progress/<task_id>")
def progress_api(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"found": False})
    return jsonify({
        "found": True,
        "task_id": task["task_id"],
        "filename": task["filename"],
        "status": task["status"],
        "progress": task["progress"],
        "current_page": task["current_page"],
        "total_pages": task["total_pages"],
        "language_display": task.get("language_display", ""),
        "detected_language": task.get("detected_language", ""),
        "word_count": task["word_count"],
        "eta": task.get("eta", ""),
        "error": task.get("error", ""),
        "mega_link": task.get("mega_link", ""),
    })


@app.route("/task/<task_id>")
def task_page(task_id):
    task = tasks.get(task_id)
    if not task:
        flash("Task not found", "error")
        return redirect("/")
    return render_page(f"Processing - {task['filename']}", build_task_html(task), "upload")


def build_task_html(task):
    status_icon = "\u23F3" if task["status"] == "processing" else ("\u2705" if task["status"] == "completed" else "\u274C")
    status_text = task["status"].title()
    eta_text = task.get("eta", "")
    detected = task.get("detected_language", "")
    word_count = task["word_count"]
    pct = task["progress"]
    mega_link = task.get("mega_link", "")

    extra = ""
    if task["status"] == "completed":
        extra = f'''<div style="margin-top:1.5rem;display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
            <a href="/download/{task_id}" class="btn btn-primary">\U0001F4E5 Download .txt</a>
            <a href="/" class="btn btn-secondary">\U0001F504 Process Another</a>
        </div>'''
        if mega_link:
            extra += f'''<p style="margin-top:0.8rem;"><a href="{mega_link}" target="_blank" style="color:var(--accent);font-weight:600;">\U0001F310 Download from Mega Cloud</a></p>'''
        if detected:
            extra += f'<p style="color:#666;margin-top:0.5rem;">Detected language: <strong>{detected}</strong></p>'
        if word_count:
            extra += f'<p style="color:#666;">{word_count} words extracted</p>'
    elif task["status"] == "failed":
        extra = f'''<p style="color:#721c24;">Error: {task.get("error", "Unknown error")}</p>
            <div style="margin-top:1rem;"><a href="/" class="btn btn-primary">\U0001F504 Try Again</a></div>'''

    return f'''<div class="container progress-page">
        <div class="card">
            <div class="task-id">Task: {task_id}</div>
            <div class="progress-filename">{task["filename"]}</div>
            <div class="progress-status">
                <div class="progress-stat"><div class="value">{status_icon}</div><div class="label">Status</div></div>
                <div class="progress-stat"><div class="value">{pct}%</div><div class="label">Progress</div></div>
                <div class="progress-stat"><div class="value">{task["current_page"]}/{task["total_pages"]}</div><div class="label">Pages</div></div>
                <div class="progress-stat"><div class="value">{task.get("language_display","")}</div><div class="label">Language</div></div>
                <div class="progress-stat"><div class="value">{eta_text}</div><div class="label">ETA</div></div>
            </div>
            <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{pct}%"></div></div>
            {extra}
        </div>
    </div>
    <script>
    {'''(
    function poll() {
        fetch("/progress/'"'"' + task_id + "'"'"').then(r=>r.json()).then(d=>{
            if(d.found && (d.status==="processing"||d.status==="queued")){
                var p=d.progress||0;
                document.querySelector(".progress-bar-fill").style.width=p+"%";
                document.querySelectorAll(".progress-stat")[1].querySelector(".value").textContent=p+"%";
                document.querySelectorAll(".progress-stat")[2].querySelector(".value").textContent=(d.current_page||0)+"/"+(d.total_pages||0);
                document.querySelectorAll(".progress-stat")[4].querySelector(".value").textContent=d.eta||"";
                setTimeout(poll,2000);
            } else if(d.found && d.status==="completed"){
                location.reload();
            } else if(d.found && d.status==="failed"){
                location.reload();
            }
        });
    }
    poll();
    )() if task["status"] in ("processing","queued") else ""'''}
    </script>'''


@app.route("/downloads")
def downloads():
    all_tasks = []
    with tasks_lock:
        for tid in tasks_order:
            t = tasks.get(tid)
            if t:
                all_tasks.append(t)

    processing = [t for t in all_tasks if t["status"] in ("processing", "queued")]
    completed = [t for t in all_tasks if t["status"] == "completed"]
    failed = [t for t in all_tasks if t["status"] == "failed"]

    parts = []

    if processing:
        rows = ""
        for t in processing:
            pct = t["progress"]
            tid = t["task_id"]
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td>{"\u23F3"} {pct}%</td>
                <td><span class="status-badge processing">{"\u23F3"} Processing</span></td>
                <td><a href="/task/{tid}" class="btn btn-primary" style="padding:5px 14px;font-size:0.85rem;">View</a></td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">{"\u23F3"} Processing</h3>
            <table class="download-table"><thead><tr><th>File</th><th>Progress</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table>''')

    if completed:
        rows = ""
        for t in completed:
            tid = t["task_id"]
            mega_link = t.get("mega_link", "")
            dl = f'<a href="/download/{tid}" class="btn btn-primary" style="padding:5px 14px;font-size:0.85rem;">{"\U0001F4E5"} Download</a>'
            if mega_link:
                dl += f' <a href="{mega_link}" target="_blank" class="btn btn-secondary" style="padding:5px 10px;font-size:0.8rem;">{"\U0001F310"} Mega</a>'
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td>{t["word_count"]}</td>
                <td><span class="status-badge completed">{"\u2705"} Completed</span></td>
                <td>{dl}</td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">{"\u2705"} Completed</h3>
            <table class="download-table"><thead><tr><th>File</th><th>Words</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table>''')

    if failed:
        rows = ""
        for t in failed:
            tid = t["task_id"]
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td><span class="status-badge failed">{"\u274C"} Failed</span></td>
                <td style="color:#721c24;font-size:0.85rem;">{t.get("error","")[:50]}</td>
                <td><a href="/task/{tid}" class="btn btn-secondary" style="padding:5px 14px;font-size:0.85rem;">Details</a></td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">{"\u274C"} Failed</h3>
            <table class="download-table"><thead><tr><th>File</th><th>Status</th><th>Error</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table>''')

    if not parts:
        content = '''<div class="container">
            <div class="page-title"><h2>\U0001F4E6 Downloads</h2></div>
            <div class="card" style="text-align:center;padding:4rem 2rem;">
                <p style="font-size:1.2rem;color:#666;">No downloads yet.</p>
                <p style="margin-top:1rem;"><a href="/" class="btn btn-primary">\U0001F4C4 Upload a file</a></p>
            </div>
        </div>'''
    else:
        content = f'''<div class="container">
            <div class="page-title"><h2>\U0001F4E6 Downloads</h2></div>
            <div class="card">{"".join(parts)}</div>
        </div>'''

    return render_page("Downloads", content, "downloads")


@app.route("/download/<task_id>")
def download_file(task_id):
    text = results.get(task_id)
    if text is None:
        flash("Download not found or expired.", "error")
        return redirect("/downloads")
    task = tasks.get(task_id, {})
    base = task.get("filename", "ocr_result")
    name = os.path.splitext(base)[0] + ".txt"
    return send_file(
        BytesIO(text.encode("utf-8")),
        mimetype="text/plain",
        as_attachment=True,
        download_name=name,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Please select a file to upload.", "error")
            return redirect("/")

        ext = os.path.splitext(f.filename.lower())[1]
        lang = request.form.get("lang", "auto")
        start_page = request.form.get("start_page", "1")
        end_page = request.form.get("end_page", "")
        save_mega = request.form.get("save_mega") == "on"

        if ext not in SUPPORTED_EXTS:
            flash("Unsupported file type: " + ext, "error")
            return redirect("/")

        sp = max(1, int(start_page)) if start_page.isdigit() else 1
        ep = int(end_page) if end_page.isdigit() else None

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            f.save(tmp.name)
            tmppath = tmp.name
            tmp.close()
        except Exception as e:
            flash("Error saving file: " + str(e), "error")
            return redirect("/")

        task_id = os.urandom(8).hex()
        task = {
            "task_id": task_id,
            "filename": f.filename,
            "ext": ext,
            "language": lang,
            "status": "queued",
            "progress": 0,
            "current_page": 0,
            "total_pages": 0,
            "word_count": 0,
            "detected_language": "",
            "language_display": LANG_OPTIONS.get(lang, lang),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "eta": "",
            "start_time": time.time(),
            "mega_link": "",
        }

        with tasks_lock:
            tasks[task_id] = task
            tasks_order.insert(0, task_id)

        t = threading.Thread(
            target=process_task,
            args=(task_id, tmppath, ext, lang, sp, ep, save_mega),
            daemon=True,
        )
        t.start()

        return redirect(f"/task/{task_id}")

    lang_opts = ""
    for val, label in LANG_OPTIONS.items():
        sel = " selected" if val == "auto" else ""
        lang_opts += f'<option value="{val}"{sel}>{label}</option>'

    mega_checks = ""
    if MEGA_AVAILABLE and MEGA_EMAIL and MEGA_PASSWORD:
        mega_checks = '''<div class="form-row">
            <label><input type="checkbox" name="save_mega" checked> Save to Mega Cloud</label>
        </div>'''

    doc_btns = ""
    for key, dt in DOC_TYPES.items():
        active_cls = " active" if key == "pdf" else ""
        doc_btns += f'<button type="button" class="doc-type-btn{active_cls}" data-type="{key}" data-ext="{",".join(dt["exts"])}">{dt["icon"]} {dt["label"]}</button>'

    content = f'''<div class="container">
        <div class="page-title"><h2>\U0001F4C4 Upload Document</h2></div>
        <div class="card">
            <form method="post" enctype="multipart/form-data" id="upload-form">
                <div class="doc-types" id="doc-types">
                    {doc_btns}
                </div>
                <input type="hidden" name="doc_type" id="doc-type-input" value="pdf">
                <div class="file-upload-area" id="file-area">
                    <div class="upload-icon">\U0001F4C1</div>
                    <p>Click or drag file here</p>
                    <div class="file-name" id="file-name"></div>
                    <input type="file" name="file" id="file-input" accept=".pdf" required>
                </div>
                <div class="form-row">
                    <select name="lang" id="lang">{lang_opts}</select>
                    <input type="number" name="start_page" placeholder="From page" min="1" value="1">
                    <input type="number" name="end_page" placeholder="To (blank = all)" min="1">
                </div>
                {mega_checks}
                <button type="submit" class="upload-btn" id="submit-btn">\U0001F4E4 Upload &amp; Extract</button>
            </form>
        </div>
        <div class="card">
            <h2>\U0001F4A1 How It Works</h2>
            <p>Select a document type, upload your file, and our OCR engine extracts text in the background. You can close the page and come back later.</p>
            <div class="tip-box" style="margin-top:1.5rem;">
                <h4><span class="tip-icon">\u26A1</span> Pro Tip</h4>
                <p>Use Auto Detect for mixed Tamil + English documents. Set page range to process specific PDF pages. Enable Mega Cloud to get a shareable download link.</p>
            </div>
        </div>
        <div class="card">
            <h2>\U0001F4E6 Supported Formats</h2>
            <div class="formats-grid">
                <div class="format-card">PDF Documents</div>
                <div class="format-card">PNG / JPEG / WEBP</div>
                <div class="format-card">TIFF / BMP / GIF</div>
                <div class="format-card">Word (DOCX)</div>
                <div class="format-card">Excel (XLSX)</div>
                <div class="format-card">CSV / TXT / JSON</div>
            </div>
        </div>
    </div>
    <script>
    (function(){{
        var typeInput = document.getElementById("doc-type-input");
        var fileInput = document.getElementById("file-input");
        var fileArea = document.getElementById("file-area");
        var fileName = document.getElementById("file-name");
        var btns = document.querySelectorAll(".doc-type-btn");
        btns.forEach(function(b){{
            b.addEventListener("click",function(){{
                btns.forEach(function(x){{x.classList.remove("active")}});
                this.classList.add("active");
                typeInput.value = this.getAttribute("data-type");
                fileInput.accept = "." + this.getAttribute("data-ext").replace(/,/g, ",.");
                fileInput.value = "";
                fileName.textContent = "";
                fileArea.classList.remove("has-file");
            }});
        }});
        fileInput.addEventListener("change",function(){{
            if(this.files && this.files[0]){{
                fileName.textContent = this.files[0].name;
                fileArea.classList.add("has-file");
            }}
        }});
    }})();
    </script>'''

    return render_page("Upload", content, "upload")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
