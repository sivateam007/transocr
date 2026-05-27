"""OCR Solutions — Background OCR with progress tracking, Mega cloud, keepalive, JSON persistence"""

import os
import re
import json
import tempfile
import threading
import time
import gc
import uuid
import logging
import shutil
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _CTimeoutError

from flask import Flask, flash, redirect, render_template_string, request, send_file, jsonify
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
import pytesseract
import requests

gc.set_threshold(100, 5, 2)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import asyncio
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = lambda f: f

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

BATCH_SIZE = 1
CHECKPOINT_INTERVAL = 5
MEGA_LOGIN_TIMEOUT = 30
CONVERT_TIMEOUT = 120
OCR_TIMEOUT = 300

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

tasks = {}
results = {}
tasks_order = []
tasks_lock = threading.Lock()

MEGA_EMAIL = os.environ.get("MEGA_EMAIL", "")
MEGA_PASSWORD = os.environ.get("MEGA_PASSWORD", "")
KEEPALIVE_URL = os.environ.get("KEEPALIVE_URL", "")

_active_tasks = 0
_keepalive_lock = threading.Lock()
_keepalive_thread = None

_mega_client = None
_mega_lock = threading.Lock()

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress_tracker.json")
_last_save_time = 0

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

HTML_HEADER = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OCR Solutions - {{ title }}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
:root { --primary: #0c1f33; --secondary: #125683; --accent: #7f89d4; --light: #ecf0f1; --dark: #2c3e50; --success: #27ae60; --git-color: #e24124; }
body { line-height: 1.6; color: #333; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }
header { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 0.8rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.header-container { display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.logo h1 { font-size: 1.6rem; color: white; letter-spacing: 2px; }
.logo span { color: var(--accent); font-weight: 300; letter-spacing: 1px; }
.header-nav { display: flex; gap: 0.8rem; }
.header-nav a { display: flex; align-items: center; gap: 6px; padding: 8px 18px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.95rem; transition: all 0.3s; color: rgba(255,255,255,0.8); }
.header-nav a:hover { background: rgba(255,255,255,0.15); color: white; }
.header-nav a.active { background: var(--git-color); color: white; }
.page-title { text-align: center; margin: 2.5rem 0 1.5rem; color: var(--dark); }
.page-title:after { content: ''; display: block; width: 80px; height: 4px; background: var(--git-color); margin: 10px auto; border-radius: 2px; }
.container { max-width: 900px; margin: 0 auto; padding: 0 20px; }
.card { margin-bottom: 2rem; padding: 2rem; border-radius: 15px; background: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
.card h2 { color: var(--dark); margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--light); }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 10px 24px; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; text-decoration: none; transition: all 0.3s; }
.btn-primary { background: linear-gradient(135deg, var(--secondary), var(--accent)); color: white; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(18,86,131,0.4); }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover { transform: translateY(-2px); }
.btn-danger { background: var(--git-color); color: white; }
.btn-danger:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(226,65,36,0.4); }
.btn-sm { padding: 6px 14px; font-size: 0.85rem; }
.doc-types { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 1.5rem; justify-content: center; }
.doc-type-btn { flex: 1; min-width: 100px; padding: 12px 8px; border: 2px solid #dee2e6; border-radius: 10px; background: white; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: all 0.3s; text-align: center; }
.doc-type-btn:hover { border-color: var(--accent); background: #f0f2ff; }
.doc-type-btn.active { border-color: var(--git-color); background: #fff0ee; color: var(--git-color); }
.file-upload-area { border: 2px dashed #ccc; border-radius: 12px; padding: 2.5rem; text-align: center; transition: all 0.3s; margin-bottom: 1.2rem; cursor: pointer; }
.file-upload-area:hover { border-color: var(--accent); background: #f8f9ff; }
.file-upload-area.has-file { border-color: var(--success); background: #f0fff4; }
.file-upload-area .upload-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.file-upload-area p { color: #888; font-size: 0.95rem; }
.file-name { margin-top: 0.5rem; font-weight: 600; color: var(--dark); word-break: break-all; }
#file-input { display: none; }
.form-row { display: flex; gap: 10px; margin-bottom: 1rem; flex-wrap: wrap; align-items: center; }
.form-row select, .form-row input[type=number] { flex: 1; min-width: 120px; padding: 10px 14px; border: 2px solid #dee2e6; border-radius: 8px; font-size: 0.95rem; background: white; }
.form-row select:focus, .form-row input:focus { outline: none; border-color: var(--accent); }
.form-row label { display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--dark); cursor: pointer; }
.form-row input[type=checkbox] { width: 18px; height: 18px; accent-color: var(--secondary); }
.upload-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, var(--secondary), var(--accent)); color: white; border: none; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.upload-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(18,86,131,0.4); }
.formats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px,1fr)); gap: 10px; }
.format-card { padding: 12px; background: var(--light); border-radius: 8px; text-align: center; font-weight: 600; color: var(--dark); font-size: 0.9rem; }
.tip-box { background: #fff8e1; border-left: 4px solid #ffc107; padding: 1rem 1.5rem; border-radius: 8px; }
.tip-icon { font-size: 1.2rem; }
.progress-page .task-id { font-size: 0.8rem; color: #999; margin-bottom: 5px; word-break: break-all; }
.progress-filename { font-size: 1.2rem; font-weight: 700; color: var(--dark); margin-bottom: 1.5rem; word-break: break-all; }
.progress-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 12px; margin-bottom: 1.5rem; }
.progress-stat { text-align: center; padding: 10px; background: var(--light); border-radius: 10px; }
.progress-stat .value { font-size: 1.3rem; font-weight: 700; color: var(--dark); }
.progress-stat .label { font-size: 0.75rem; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
.progress-bar-bg { height: 14px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 1rem 0; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--secondary), var(--accent)); border-radius: 10px; transition: width 1s ease; }
.progress-actions { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 1.5rem; }
.status-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
.status-badge.processing { background: #fff3cd; color: #856404; }
.status-badge.completed { background: #d4edda; color: #155724; }
.status-badge.failed { background: #f8d7da; color: #721c24; }
.status-badge.interrupted { background: #e2e3e5; color: #383d41; }
.section-title { margin: 1.5rem 0 1rem; padding-bottom: 8px; border-bottom: 2px solid var(--light); color: var(--dark); }
.download-table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
.download-table th { background: var(--light); color: var(--dark); padding: 10px 12px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; }
.download-table td { padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 0.9rem; word-break: break-all; }
.download-table tr:hover { background: #f8f9fa; }
.download-table .actions { white-space: nowrap; }
.flash-msg { padding: 12px 20px; margin-bottom: 1rem; border-radius: 8px; font-weight: 600; }
.flash-msg.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.flash-msg.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
/* Preview modal */
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
.modal-overlay.active { display: flex; }
.modal-content { background: white; border-radius: 12px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto; padding: 2rem; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
.modal-content h3 { margin-bottom: 1rem; }
.modal-content pre { background: #f5f5f5; padding: 1rem; border-radius: 8px; font-size: 0.85rem; white-space: pre-wrap; word-break: break-word; max-height: 50vh; overflow-y: auto; }
.modal-close { float: right; background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #999; }
.modal-close:hover { color: #333; }
@media (max-width:600px) { .header-container { flex-direction: column; gap: 8px; } .doc-type-btn { min-width: 70px; font-size: 0.75rem; padding: 10px 4px; } .form-row { flex-direction: column; } .progress-status { grid-template-columns: repeat(3, 1fr); } }
</style>
</head>
<body>
<header>
<div class="header-container">
<div class="logo"><h1>OCR <span>Solutions</span></h1></div>
<nav class="header-nav">
<a href="/" class="{{ 'active' if active == 'upload' else '' }}">\U0001F4C1 Upload</a>
<a href="/downloads" class="{{ 'active' if active == 'downloads' else '' }}">\U0001F4E6 My Downloads</a>
</nav>
</div>
</header>
{% for f in flashes %}
<div class="flash-msg {{ f[1] }}">{{ f[0] }}</div>
{% endfor %}
'''

HTML_CLOSING = '\n</body>\n</html>\n'


def _get_memory_mb():
    try:
        if os.name == 'posix':
            with open('/proc/self/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


def _save_progress(force=False):
    global _last_save_time
    now = time.time()
    if not force and now - _last_save_time < 2:
        return
    serializable = {}
    with tasks_lock:
        for tid, task in tasks.items():
            d = dict(task)
            d.pop('filepath', None)
            serializable[tid] = d
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, default=str, ensure_ascii=False)
        _last_save_time = now
    except Exception as e:
        logger.error(f"Save progress failed: {e}")


def _load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Load progress failed: {e}")
        return {}


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


def mega_call(m, method_name, *args, timeout=MEGA_LOGIN_TIMEOUT, **kwargs):
    fn = getattr(m, method_name)
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(fn, *args, **kwargs)
        return future.result(timeout=timeout)
    except _CTimeoutError:
        logger.warning(f"Mega.{method_name} timed out after {timeout}s")
        raise
    finally:
        pool.shutdown(wait=False)


def init_mega():
    email = os.environ.get("MEGA_EMAIL", "")
    password = os.environ.get("MEGA_PASSWORD", "")
    if not email or not password:
        return None
    try:
        mega = Mega()
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(mega.login, email, password)
            return future.result(timeout=MEGA_LOGIN_TIMEOUT)
        finally:
            pool.shutdown(wait=False)
    except Exception as e:
        logger.error(f"Mega login failed: {e}")
        return None


def ensure_mega_folder(m, folder_name):
    try:
        folder = mega_call(m, "find", folder_name, timeout=15)
    except Exception:
        return None
    if folder:
        return folder[0] if isinstance(folder, (list, tuple)) else folder
    try:
        result = mega_call(m, "create_folder", folder_name, timeout=15)
        return result.get(folder_name)
    except Exception:
        return None


def upload_checkpoint(m, task_id, output_path, metadata):
    folder_name = "ocr-checkpoints"
    folder_handle = ensure_mega_folder(m, folder_name)
    if not folder_handle:
        return False
    try:
        old_ckpt = mega_call(m, "find", f"{folder_name}/{task_id}.checkpoint", timeout=15)
        if old_ckpt:
            mega_call(m, "delete", old_ckpt[0] if isinstance(old_ckpt, (list, tuple)) else old_ckpt)
    except Exception:
        pass
    try:
        old_out = mega_call(m, "find", f"{folder_name}/{task_id}_output.txt", timeout=15)
        if old_out:
            mega_call(m, "delete", old_out[0] if isinstance(old_out, (list, tuple)) else old_out)
    except Exception:
        pass
    ckpt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(metadata, ckpt_file)
    ckpt_file.close()
    try:
        mega_call(m, "upload", ckpt_file.name, dest=folder_handle, dest_filename=f"{task_id}.checkpoint", timeout=120)
    except Exception as e:
        logger.error(f"Checkpoint metadata upload failed: {e}")
        os.unlink(ckpt_file.name)
        return False
    os.unlink(ckpt_file.name)
    try:
        mega_call(m, "upload", output_path, dest=folder_handle, dest_filename=f"{task_id}_output.txt", timeout=120)
    except Exception as e:
        logger.error(f"Checkpoint output upload failed: {e}")
        return False
    logger.info(f"Checkpoint saved for task {task_id} at page {metadata.get('last_page')}")
    return True


def cleanup_checkpoints(m, task_id):
    folder_name = "ocr-checkpoints"
    try:
        old_ckpt = mega_call(m, "find", f"{folder_name}/{task_id}.checkpoint", timeout=15)
        if old_ckpt:
            mega_call(m, "delete", old_ckpt[0] if isinstance(old_ckpt, (list, tuple)) else old_ckpt)
    except Exception:
        pass
    try:
        old_out = mega_call(m, "find", f"{folder_name}/{task_id}_output.txt", timeout=15)
        if old_out:
            mega_call(m, "delete", old_out[0] if isinstance(old_out, (list, tuple)) else old_out)
    except Exception:
        pass


def upload_to_mega(local_file_path, remote_filename):
    if not os.path.exists(local_file_path):
        return None
    m = init_mega()
    if not m:
        return None
    try:
        folder = mega_call(m, "find", "ocr-outputs", timeout=15)
    except Exception:
        return None
    if not folder:
        try:
            folder_node = mega_call(m, "create_folder", "ocr-outputs", timeout=15)
            dest = folder_node.get("ocr-outputs")
        except Exception:
            return None
    else:
        dest = folder[0] if isinstance(folder, (list, tuple)) else folder
    if not dest:
        return None
    try:
        file_node = mega_call(m, "upload", local_file_path, dest=dest, timeout=120)
        link = mega_call(m, "get_upload_link", file_node, timeout=30)
        return link
    except Exception as e:
        logger.error(f"Mega upload failed: {e}")
        return None


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


def _ensure_keepalive():
    global _active_tasks, _keepalive_thread
    with _keepalive_lock:
        _active_tasks += 1
        if _keepalive_thread is None or not _keepalive_thread.is_alive():
            _keepalive_thread = threading.Thread(target=_keepalive_loop, daemon=True)
            _keepalive_thread.start()


def _release_keepalive():
    global _active_tasks
    with _keepalive_lock:
        _active_tasks -= 1
        if _active_tasks < 0:
            _active_tasks = 0


def _keepalive_loop():
    render_url = KEEPALIVE_URL
    local_url = f"http://localhost:{os.environ.get('PORT', 10000)}"
    while True:
        with _keepalive_lock:
            if _active_tasks <= 0:
                break
        success = False
        if render_url:
            try:
                requests.get(f"{render_url}/health", timeout=15)
                success = True
            except Exception:
                pass
        if not success:
            try:
                requests.get(f"{local_url}/health", timeout=5)
                success = True
            except Exception:
                pass
        time.sleep(60)


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
    start_offset = task.get("processing_start_page", 1)
    if total <= 0 or pages_done <= 0 or elapsed <= 0:
        return ""
    relative_done = max(0, pages_done - start_offset + 1)
    if relative_done <= 0:
        return ""
    pages_per_sec = relative_done / elapsed
    remaining = max(0, total - relative_done) / pages_per_sec if pages_per_sec > 0 else 0
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
            no_more_pages = False
            while True:
                if task.get("cancelled"):
                    task["status"] = "cancelled"
                    task["error"] = "Cancelled by user"
                    _save_progress(force=True)
                    return

                if end_page is not None and page_num > end_page:
                    break

                if no_more_pages:
                    break

                gc.collect()
                mem = _get_memory_mb()
                if mem > 400:
                    logger.warning(f"Task {task_id}: RSS {mem}MB > 400MB, forcing GC")
                    gc.collect()
                    gc.collect()

                images = None
                timed_out = False
                try:
                    pool = ThreadPoolExecutor(max_workers=1)
                    try:
                        future = pool.submit(convert_from_path, filepath, dpi=300, first_page=page_num, last_page=page_num)
                        images = future.result(timeout=CONVERT_TIMEOUT)
                    except _CTimeoutError:
                        logger.warning(f"Task {task_id}: Convert timeout on page {page_num}, skipping")
                        timed_out = True
                    finally:
                        pool.shutdown(wait=False)

                    if task.get("cancelled"):
                        task["status"] = "cancelled"
                        task["error"] = "Cancelled by user"
                        _save_progress(force=True)
                        return

                    if timed_out:
                        page_num += 1
                        continue

                    if images is None or len(images) == 0:
                        no_more_pages = True
                        break

                    page_text = pytesseract.image_to_string(images[0], lang=ocr_lang)
                    images[0].close()
                    del images
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    task["current_page"] = page_num
                    task["progress"] = int((page_num / task["total_pages"]) * 100) if task["total_pages"] > 0 else min(page_num, 99)
                    task["eta"] = calculate_eta(task)

                    if save_mega and (page_num - last_mega_cp) >= 10:
                        cp_text = "\n\n".join(text_parts)
                        mega_upload_text(cp_text, f"checkpoint_{task_id}_p{page_num}.txt")
                        last_mega_cp = page_num

                    _save_progress()

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

        if task.get("cancelled"):
            task["status"] = "cancelled"
            task["error"] = "Cancelled by user"
            _save_progress(force=True)
            return

        if text.strip():
            if lang == "auto":
                task["detected_language"] = detect_language(text)
            task["word_count"] = len(text.split())
            results[task_id] = text
            task["status"] = "completed"
            output_path = task.get("output_path")
            if output_path:
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                except Exception:
                    pass

            if save_mega:
                link = mega_upload_text(text, f"ocr_{task_id}.txt")
                if link:
                    task["mega_link"] = link
        else:
            task["status"] = "failed"
            task["error"] = "No text could be extracted"

        _save_progress(force=True)

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
        _save_progress(force=True)
    finally:
        _release_keepalive()
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
    tp = task["total_pages"]
    display_total = tp if tp > 0 else "?"
    return jsonify({
        "found": True,
        "task_id": task["task_id"],
        "filename": task["filename"],
        "status": task["status"],
        "progress": task["progress"],
        "current_page": task["current_page"],
        "total_pages": tp,
        "display_total": str(display_total),
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
    task_id = task["task_id"]
    status_icon = "\u23F3" if task["status"] in ("processing", "queued") else ("\u2705" if task["status"] == "completed" else "\u274C")
    status_text = task["status"].title()
    eta_text = task.get("eta", "")
    detected = task.get("detected_language", "")
    word_count = task["word_count"]
    pct = task["progress"]
    mega_link = task.get("mega_link", "")

    extra = ""
    if task["status"] == "completed":
        extra = f'''<div class="progress-actions">
            <a href="/download/{task_id}" class="btn btn-primary btn-sm">\U0001F4E5 Download .txt</a>
            <a href="/" class="btn btn-secondary btn-sm">\U0001F504 Process Another</a>
        </div>'''
        if mega_link:
            extra += f'''<p style="margin-top:0.8rem;text-align:center;"><a href="{mega_link}" target="_blank" style="color:var(--accent);font-weight:600;">\U0001F310 Download from Mega Cloud</a></p>'''
        if detected:
            extra += f'<p style="color:#666;margin-top:0.5rem;text-align:center;">Detected language: <strong>{detected}</strong></p>'
        if word_count:
            extra += f'<p style="color:#666;text-align:center;">{word_count} words extracted</p>'
    elif task["status"] == "failed":
        extra = f'''<p style="color:#721c24;text-align:center;">Error: {task.get("error", "Unknown error")}</p>
            <div class="progress-actions">
                <a href="/" class="btn btn-primary btn-sm">\U0001F504 Try Again</a>
                <button class="btn btn-secondary btn-sm" onclick="retryTask('{task_id}')">\U0001F504 Retry</button>
            </div>'''
    elif task["status"] == "cancelled":
        extra = f'''<p style="color:#856404;text-align:center;">Task was cancelled.</p>
            <div class="progress-actions">
                <a href="/" class="btn btn-primary btn-sm">\U0001F504 Upload Again</a>
            </div>'''

    cancel_btn = ""
    if task["status"] in ("processing", "queued"):
        cancel_btn = '''<div class="progress-actions">
            <button class="btn btn-danger btn-sm" onclick="cancelTask()">\u2716 Cancel</button>
            <a href="/downloads" class="btn btn-secondary btn-sm">\U0001F4E6 My Downloads</a>
        </div>'''

    polling_js = ""
    if task["status"] in ("processing", "queued"):
        polling_js = f'''<script>
        function poll() {{
            fetch("/progress/{task_id}").then(function(r){{return r.json()}}).then(function(d){{
                if(d.found && (d.status==="processing"||d.status==="queued")){{
                    var p=d.progress||0;
                    document.querySelector(".progress-bar-fill").style.width=p+"%";
                    document.querySelectorAll(".progress-stat")[1].querySelector(".value").textContent=p+"%";
                    document.querySelectorAll(".progress-stat")[2].querySelector(".value").textContent=(d.current_page||0)+"/"+(d.display_total||"?")
                    document.querySelectorAll(".progress-stat")[4].querySelector(".value").textContent=d.eta||"";
                    setTimeout(poll,2000);
                }} else if(d.found && (d.status==="completed"||d.status==="failed"||d.status==="cancelled")){{
                    location.reload();
                }}
            }});
        }}
        function cancelTask() {{
            fetch("/cancel/{task_id}",{{method:"POST"}}).then(function(r){{return r.json()}}).then(function(d){{
                location.reload();
            }});
        }}
        poll();
        </script>'''

    return f'''<div class="container progress-page">
        <div class="card">
            <div class="task-id">Task: {task_id}</div>
            <div class="progress-filename">{task["filename"]}</div>
            <div class="progress-status">
                <div class="progress-stat"><div class="value">{status_icon}</div><div class="label">Status</div></div>
                <div class="progress-stat"><div class="value">{pct}%</div><div class="label">Progress</div></div>
                <div class="progress-stat"><div class="value">{task["current_page"]}/{task["total_pages"] if task["total_pages"] > 0 else "?"}</div><div class="label">Pages</div></div>
                <div class="progress-stat"><div class="value">{task.get("language_display","")}</div><div class="label">Language</div></div>
                <div class="progress-stat"><div class="value">{eta_text}</div><div class="label">ETA</div></div>
            </div>
            <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{pct}%"></div></div>
            {cancel_btn}
            {extra}
        </div>
    </div>
    {polling_js}'''


@app.route("/cancel/<task_id>", methods=['POST'])
def cancel_task(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        if task["status"] not in ("processing", "queued", "starting"):
            return jsonify({"error": "Task is not running"}), 400
        task["cancelled"] = True
    return jsonify({"status": "cancelling"}), 200


@app.route("/retry/<task_id>", methods=['POST'])
def retry_task(task_id):
    with tasks_lock:
        old = tasks.get(task_id)
        if not old:
            return jsonify({"error": "Task not found"}), 404
        if old.get("status") not in ("failed", "cancelled"):
            return jsonify({"error": "Only failed or cancelled tasks can be retried"}), 400
        filename = old.get("filename", "input.pdf")
        ext = old.get("ext", ".pdf")
        lang = old.get("language", "auto")
        start_page = old.get("start_page", 1)
        end_page = old.get("end_page", None)

    new_id = os.urandom(8).hex()
    new_task = {
        "task_id": new_id,
        "filename": filename,
        "ext": ext,
        "language": lang,
        "status": "queued",
        "progress": 0,
        "current_page": 0,
        "total_pages": 0,
        "word_count": 0,
        "detected_language": old.get("detected_language", ""),
        "language_display": old.get("language_display", LANG_OPTIONS.get(lang, lang)),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "eta": "",
        "start_time": time.time(),
        "mega_link": "",
        "start_page": start_page,
        "end_page": end_page,
    }

    with tasks_lock:
        tasks[new_id] = new_task
        tasks_order.insert(0, new_id)

    flash("Retry task created. Please upload the file again.", "info")
    return redirect(f"/task/{new_id}")


@app.route("/preview/<task_id>")
def preview_text(task_id):
    text = results.get(task_id)
    if text is None:
        task = tasks.get(task_id)
        output_path = task.get("output_path") if task else None
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read(2000)
                return jsonify({"text": text[:2000]})
            except Exception:
                pass
        return jsonify({"text": "Preview not available."})
    return jsonify({"text": text[:2000]})


@app.route("/health")
def health():
    try:
        version = pytesseract.get_tesseract_version()
        langs = pytesseract.get_languages()
        return {"status": "healthy", "tesseract_version": str(version), "languages_available": langs}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500


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
    cancelled = [t for t in all_tasks if t["status"] == "cancelled"]
    failed = [t for t in all_tasks if t["status"] == "failed"]

    parts = []

    if processing:
        rows = ""
        for t in processing:
            pct = t["progress"]
            tid = t["task_id"]
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td>\u23F3 {pct}%</td>
                <td><span class="status-badge processing">\u23F3 Processing</span></td>
                <td>{t.get("eta","")}</td>
                <td class="actions"><a href="/task/{tid}" class="btn btn-primary btn-sm">View</a></td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">\u23F3 Processing</h3>
            <div style="overflow-x:auto;"><table class="download-table"><thead><tr><th>File</th><th>Progress</th><th>Status</th><th>ETA</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table></div>''')

    if completed:
        rows = ""
        for t in completed:
            tid = t["task_id"]
            mega_link = t.get("mega_link", "")
            dl = f'<a href="/download/{tid}" class="btn btn-primary btn-sm">\U0001F4E5 Download</a>'
            if mega_link:
                dl += f' <a href="{mega_link}" target="_blank" class="btn btn-secondary btn-sm">\U0001F310 Mega</a>'
            dl += f' <button class="btn btn-secondary btn-sm" onclick="previewText(\'{tid}\')">\U0001F50D Preview</button>'
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td>{t["word_count"]}</td>
                <td><span class="status-badge completed">\u2705 Completed</span></td>
                <td class="actions">{dl}</td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">\u2705 Completed</h3>
            <div style="overflow-x:auto;"><table class="download-table"><thead><tr><th>File</th><th>Words</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table></div>''')

    if failed:
        rows = ""
        for t in failed:
            tid = t["task_id"]
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td><span class="status-badge failed">\u274C Failed</span></td>
                <td style="color:#721c24;font-size:0.85rem;">{t.get("error","")[:50]}</td>
                <td class="actions">
                    <a href="/task/{tid}" class="btn btn-secondary btn-sm">Details</a>
                    <button class="btn btn-primary btn-sm" onclick="retryTask('{tid}')">\U0001F504 Retry</button>
                </td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">\u274C Failed</h3>
            <div style="overflow-x:auto;"><table class="download-table"><thead><tr><th>File</th><th>Status</th><th>Error</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table></div>''')

    if cancelled:
        rows = ""
        for t in cancelled:
            tid = t["task_id"]
            rows += f'''<tr>
                <td>{t["filename"]}</td>
                <td><span class="status-badge interrupted">\u23F8 Cancelled</span></td>
                <td></td>
                <td class="actions">
                    <button class="btn btn-primary btn-sm" onclick="retryTask('{tid}')">\U0001F504 Retry</button>
                </td>
            </tr>'''
        parts.append(f'''<h3 class="section-title">\u23F8 Cancelled</h3>
            <div style="overflow-x:auto;"><table class="download-table"><thead><tr><th>File</th><th>Status</th><th>Error</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody></table></div>''')

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
        </div>
        <div id="preview-modal" class="modal-overlay">
            <div class="modal-content">
                <button class="modal-close" onclick="closePreview()">&times;</button>
                <h3>\U0001F50D Preview</h3>
                <pre id="preview-text">Loading...</pre>
            </div>
        </div>
        <script>
        function previewText(tid) {{
            document.getElementById("preview-text").textContent = "Loading...";
            document.getElementById("preview-modal").classList.add("active");
            fetch("/preview/"+tid).then(function(r){{return r.json()}}).then(function(d){{
                document.getElementById("preview-text").textContent = d.text || "No preview available.";
            }});
        }}
        function closePreview() {{
            document.getElementById("preview-modal").classList.remove("active");
        }}
        document.getElementById("preview-modal").addEventListener("click", function(e) {{
            if(e.target === this) closePreview();
        }});
        function retryTask(tid) {{
            if(!confirm("Create a retry task for this file?")) return;
            fetch("/retry/"+tid, {{method:"POST"}}).then(function(r){{
                if(r.redirected) {{ window.location.href = r.url; }}
                else {{ location.reload(); }}
            }});
        }}
        </script>'''

    return render_page("Downloads", content, "downloads")


@app.route("/download/<task_id>")
def download_file(task_id):
    text = results.get(task_id)
    if text is None:
        task = tasks.get(task_id)
        output_path = task.get("output_path") if task else None
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception:
                pass
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
            "start_page": sp,
            "end_page": ep,
            "cancelled": False,
        }

        if ext == ".pdf" and (MEGA_AVAILABLE and MEGA_EMAIL and MEGA_PASSWORD):
            try:
                output_dir = tempfile.mkdtemp()
                output_path = os.path.join(output_dir, f"ocr_{task_id}.txt")
                task["output_path"] = output_path
            except Exception:
                pass

        with tasks_lock:
            tasks[task_id] = task
            tasks_order.insert(0, task_id)
        _save_progress()

        t = threading.Thread(
            target=process_task,
            args=(task_id, tmppath, ext, lang, sp, ep, save_mega),
            daemon=True,
        )
        t.start()
        _ensure_keepalive()

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
                fileInput.click();
            }});
        }});
        fileArea.addEventListener("click",function(){{
            fileInput.click();
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


@app.errorhandler(413)
def too_large(e):
    flash("File too large. Maximum size is 200MB.", "error")
    return redirect("/")


def _startup_resume():
    time.sleep(5)
    with app.app_context():
        saved = _load_progress()
        restored = 0
        with tasks_lock:
            for tid, data in saved.items():
                if tid not in tasks:
                    data["status"] = "interrupted" if data.get("status") not in ("completed", "failed") else data["status"]
                    if "cancelled" in data and data.get("cancelled"):
                        data["status"] = "cancelled"
                    data["start_time"] = time.time()
                    data["eta"] = ""
                    data["mega_link"] = data.get("mega_link", "")
                    tasks[tid] = data
                    tasks_order.append(tid)
                    restored += 1
        if restored:
            _save_progress(force=True)
            logger.info(f"Startup: restored {restored} tasks from {PROGRESS_FILE}")


def _cleanup_loop():
    while True:
        time.sleep(3600)
        try:
            now = time.time()
            to_delete = []
            with tasks_lock:
                for tid, task in tasks.items():
                    if task.get("status") == "completed" and "created_at" in task:
                        try:
                            ct = datetime.strptime(task["created_at"], "%Y-%m-%d %H:%M").timestamp()
                            if now - ct > 86400:
                                to_delete.append(tid)
                        except Exception:
                            pass
            for tid in to_delete:
                with tasks_lock:
                    tasks.pop(tid, None)
                    results.pop(tid, None)
                    if tid in tasks_order:
                        tasks_order.remove(tid)
            if to_delete:
                _save_progress()
                logger.info(f"Cleanup: removed {len(to_delete)} old completed tasks")
        except Exception:
            pass


threading.Thread(target=_startup_resume, daemon=True).start()
threading.Thread(target=_cleanup_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
