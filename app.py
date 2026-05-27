import os
import re
import tempfile
from io import BytesIO
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, send_file
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

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
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

results = {}
download_history = []

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"}
TEXT_EXTS = {".txt", ".csv", ".tsv", ".md", ".json", ".xml"}
OFFICE_EXTS = {".docx", ".xlsx"}
SUPPORTED_EXTS = IMG_EXTS | {".pdf"} | TEXT_EXTS | OFFICE_EXTS

LANG_OPTIONS = {
    "auto": "Auto Detect",
    "tam+eng": "Tamil + English",
    "tam": "Tamil",
    "eng": "English",
    "hin": "Hindi",
    "tel": "Telugu",
    "mal": "Malayalam",
    "kan": "Kannada",
    "guj": "Gujarati",
    "ben": "Bengali",
    "mar": "Marathi",
    "urd": "Urdu",
    "san": "Sanskrit",
}

FORMATS_DISPLAY = [
    ("PDF Documents", "pdf"),
    ("PNG / JPEG / WEBP", "image"),
    ("TIFF / BMP / GIF", "image"),
    ("Word (DOCX)", "office"),
    ("Excel (XLSX)", "office"),
    ("CSV / TXT / JSON", "text"),
]

HEADER = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OCR Solutions – {{ title }}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
:root { --primary: #0c1f33; --secondary: #125683; --accent: #7f89d4; --light: #ecf0f1; --dark: #2c3e50; --success: #27ae60; --git-color: #e24124; }
body { line-height: 1.6; color: #333; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }
header { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 1rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.header-container { display: flex; justify-content: center; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.logo h1 { font-size: 2rem; color: white; letter-spacing: 3px; }
.logo span { color: var(--accent); font-weight: 300; letter-spacing: 1px; }
.nav-tabs { display: flex; justify-content: center; max-width: 1200px; margin: 2rem auto; padding: 0 20px; gap: 1rem; flex-wrap: wrap; }
.nav-tab { display: flex; align-items: center; gap: 10px; padding: 12px 25px; background: white; color: var(--primary); border-radius: 10px; text-decoration: none; font-weight: 600; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid transparent; }
.nav-tab:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.15); border-color: var(--git-color); }
.nav-tab.active { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; border-color: var(--git-color); }
.hero { background: linear-gradient(135deg, var(--git-color), #6e5494); color: white; padding: 4rem 0; text-align: center; position: relative; overflow: hidden; }
.hero:before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.1" d="M0,96L48,112C96,128,192,160,288,186.7C384,213,480,235,576,213.3C672,192,768,128,864,128C960,128,1056,192,1152,192C1248,192,1344,128,1392,96L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>'); background-size: cover; background-position: center; }
.hero-content { max-width: 800px; margin: 0 auto; padding: 0 20px; position: relative; z-index: 1; }
.hero h2 { font-size: 2.8rem; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
.hero p { font-size: 1.3rem; margin-bottom: 2.5rem; }
.upload-form { max-width: 600px; margin: 0 auto; }
.upload-form input[type=file] { display: block; width: 100%; padding: 1rem; background: rgba(255,255,255,0.15); border: 2px dashed rgba(255,255,255,0.4); border-radius: 12px; color: white; cursor: pointer; margin-bottom: 1.5rem; transition: all 0.3s; }
.upload-form input[type=file]:hover { border-color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.25); }
.upload-form input[type=file]::file-selector-button { background: white; color: var(--git-color); border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; margin-right: 15px; cursor: pointer; }
.form-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.form-row select, .form-row input[type=number] { flex: 1; min-width: 140px; padding: 12px 16px; border-radius: 10px; border: 2px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.15); color: white; font-size: 0.95rem; cursor: pointer; }
.form-row select option { background: var(--primary); color: white; }
.form-row input[type=number]::placeholder { color: rgba(255,255,255,0.6); }
.form-row input[type=number] { cursor: text; }
.upload-btn { background: white; color: var(--git-color); border: none; padding: 14px 40px; border-radius: 10px; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.3s; width: 100%; }
.upload-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.upload-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.section-title { text-align: center; margin: 3rem 0 2rem; color: var(--dark); position: relative; }
.section-title:after { content: ''; display: block; width: 80px; height: 4px; background: var(--git-color); margin: 10px auto; border-radius: 2px; }
.content-section { margin-bottom: 2rem; padding: 2.5rem; border-radius: 15px; background-color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: transform 0.3s, box-shadow 0.3s; }
.content-section:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }
.content-section h2 { color: var(--dark); margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--git-color); display: inline-block; }
.result-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 1.5rem; max-height: 60vh; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 1rem 0; }
.result-actions { display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border-radius: 10px; font-weight: 600; text-decoration: none; transition: all 0.3s; border: none; cursor: pointer; font-size: 1rem; }
.btn-primary { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.btn-secondary { background: white; color: var(--primary); border: 2px solid var(--primary); }
.btn-secondary:hover { background: var(--primary); color: white; }
.flash { padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; font-weight: 500; }
.flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.download-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.download-table th { background: var(--primary); color: white; padding: 12px 15px; text-align: left; font-weight: 600; }
.download-table td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; }
.download-table tr:hover { background: #f1f5f9; }
.tip-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-left: 6px solid #ffd700; padding: 2rem; margin: 2rem 0; border-radius: 12px; color: white; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3); position: relative; overflow: hidden; }
.tip-box:before { content: ''; position: absolute; top: -50%; right: -50%; width: 100%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%); transform: rotate(45deg); }
.tip-box h4 { color: #ffd700; margin-bottom: 1rem; display: flex; align-items: center; gap: 12px; font-size: 1.3rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
.tip-box p { font-size: 1.1rem; line-height: 1.7; margin-bottom: 0; text-shadow: 1px 1px 1px rgba(0,0,0,0.1); }
.tip-icon { font-size: 1.5rem; }
.formats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
.format-card { background: var(--light); padding: 1.2rem; border-radius: 10px; text-align: center; font-weight: 600; color: var(--dark); font-size: 0.95rem; transition: all 0.3s; }
.format-card:hover { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; transform: translateY(-2px); }
.loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(12,31,51,0.92); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; }
.loading-overlay.show { display: flex; }
.spinner { width: 60px; height: 60px; border: 5px solid rgba(255,255,255,0.2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-overlay p { color: white; font-size: 1.4rem; margin-top: 2rem; font-weight: 500; }
.loading-overlay small { color: rgba(255,255,255,0.6); margin-top: 0.5rem; font-size: 0.9rem; }
.home-icon { position: fixed; top: 20px; right: 20px; width: 50px; height: 50px; background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; text-decoration: none; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: all 0.3s ease; border: 2px solid white; }
.home-icon:hover { background: linear-gradient(135deg, #e74c3c, var(--git-color)); transform: scale(1.1) translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); text-decoration: none; color: white; }
@media (max-width: 768px) { .header-container { flex-direction: column; text-align: center; } .nav-tabs { flex-direction: column; align-items: center; } .nav-tab { width: 100%; max-width: 300px; justify-content: center; } .hero h2 { font-size: 2rem; } .hero { padding: 3rem 0; } .content-section { padding: 1.5rem; } .result-actions { flex-direction: column; } .home-icon { width: 45px; height: 45px; font-size: 18px; top: 15px; right: 15px; } .logo h1 { font-size: 1.4rem; } .form-row { flex-direction: column; } }
@media (max-width: 480px) { .hero h2 { font-size: 1.5rem; } .hero p { font-size: 1rem; } .logo h1 { font-size: 1.2rem; } .home-icon { width: 40px; height: 40px; font-size: 16px; top: 12px; right: 12px; } }
</style>
</head>
<body>
<div class="loading-overlay" id="loading-overlay">
    <div class="spinner"></div>
    <p>⏳ Processing your file...</p>
    <small>This may take a moment for large documents</small>
</div>
<header>
    <div class="header-container">
        <div class="logo">
            <h1>OCR <span>Solutions</span></h1>
        </div>
    </div>
</header>
<a href="/" class="home-icon" title="Home">&#127968;</a>
<div class="nav-tabs">
    <a href="/" class="nav-tab {{ 'active' if active == 'upload' else '' }}">&#128196; Upload</a>
    <a href="/downloads" class="nav-tab {{ 'active' if active == 'downloads' else '' }}">&#128230; Downloads</a>
</div>
<div class="container">
{% for cat, msg in flashes %}
<div class="flash {{ cat }}">{{ msg }}</div>
{% endfor %}
</div>
"""

CLOSING = r"""
<script>
document.getElementById('upload-form')?.addEventListener('submit', function(e) {
    document.getElementById('loading-overlay').classList.add('show');
});
</script>
</body>
</html>
"""


def detect_language(text):
    tamil = len(re.findall(r'[\u0B80-\u0BFF]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))
    if tamil > latin * 2:
        return "Tamil"
    elif tamil > latin / 2:
        return "Tamil + English"
    elif latin > 0:
        return "English"
    return "Unknown"


def ocr_pdf(filepath, lang="tam+eng", dpi=300, start_page=1, end_page=None):
    pages = []
    page_num = max(1, start_page)
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
                pages.append(f"--- Page {page_num} ---\n{text}")
            page_num += 1
        except Exception:
            break
    return "\n\n".join(pages)


def ocr_image(filepath, lang="tam+eng"):
    with Image.open(filepath) as img:
        text = pytesseract.image_to_string(img, lang=lang)
    return text


def extract_docx_text(filepath):
    if DocxDocument is None:
        return "[python-docx not installed. Install with: pip install python-docx]"
    doc = DocxDocument(filepath)
    lines = []
    for para in doc.paragraphs:
        if para.text.strip():
            lines.append(para.text)
    return "\n".join(lines)


def extract_xlsx_text(filepath):
    if load_workbook is None:
        return "[openpyxl not installed. Install with: pip install openpyxl]"
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


def extract_text(filepath, ext, lang="tam+eng", start_page=1, end_page=None):
    if ext == ".pdf":
        return ocr_pdf(filepath, lang, start_page=start_page, end_page=end_page)
    elif ext in IMG_EXTS:
        return ocr_image(filepath, lang)
    elif ext == ".docx":
        return extract_docx_text(filepath)
    elif ext == ".xlsx":
        return extract_xlsx_text(filepath)
    elif ext in TEXT_EXTS:
        return read_text_file(filepath)
    return ""


def render_page(title, content, active, flashes=None):
    if flashes is None:
        flashes = []
    return render_template_string(HEADER + content + CLOSING, title=title, active=active, flashes=flashes)


def build_lang_options(selected):
    opts = ""
    for val, label in LANG_OPTIONS.items():
        sel = " selected" if val == selected else ""
        opts += f"<option value=\"{val}\"{sel}>{label}</option>"
    return opts


def build_formats_display():
    cards = ""
    for name, icon in FORMATS_DISPLAY:
        cards += f"<div class=\"format-card\">{name}</div>"
    return cards


@app.route("/", methods=["GET", "POST"])
def index():
    result_html = None
    filename = ""
    session_id = ""
    word_count = 0
    detected_lang = ""

    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Please select a file to upload.", "error")
            return redirect("/")

        ext = os.path.splitext(f.filename.lower())[1]
        lang = request.form.get("lang", "tam+eng")
        start_page = request.form.get("start_page", "1")
        end_page = request.form.get("end_page", "")

        if ext not in SUPPORTED_EXTS:
            flash(f"Unsupported file type: {ext}", "error")
            return redirect("/")

        sp = max(1, int(start_page)) if start_page.isdigit() else 1
        ep = int(end_page) if end_page.isdigit() else None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                f.save(tmp.name)
                tmppath = tmp.name

            ocr_lang = lang
            if lang == "auto":
                ocr_lang = "tam+eng"

            text = extract_text(tmppath, ext, lang=ocr_lang, start_page=sp, end_page=ep)
            os.unlink(tmppath)

            if not text.strip():
                flash("No text could be extracted. The file may be empty or unreadable.", "error")
                return redirect("/")

            if lang == "auto":
                detected_lang = detect_language(text)

            session_id = os.urandom(8).hex()
            results[session_id] = text
            filename = f.filename
            word_count = len(text.split())

            download_history.insert(0, {
                "id": session_id,
                "filename": filename,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "words": word_count,
            })

            detected_html = ""
            if detected_lang:
                detected_html = f"<p style=\"color:#666;margin-bottom:1rem;\">Detected language: <strong>{detected_lang}</strong></p>"

            result_html = f"""
<div class="hero">
    <div class="hero-content">
        <h2>&#10003; Text Extracted Successfully</h2>
        <p>{word_count} words &#8226; {filename}</p>
        <a href="/" class="upload-btn" style="display:inline-block;width:auto;padding:12px 30px;text-decoration:none;">&#128260; Process Another</a>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>&#128196; {filename}</h2>
        <p style="color:#666;margin-bottom:1rem;">{word_count} words extracted</p>
        {detected_html}
        <div class="result-box">{text}</div>
        <div class="result-actions">
            <a href="/download/{session_id}" class="btn btn-primary">&#128229; Download .txt</a>
            <a href="/" class="btn btn-secondary">&#128260; Process Another</a>
        </div>
    </div>
</div>
"""
        except Exception as e:
            flash(f"Error processing file: {e}", "error")
            return redirect("/")

    if not result_html:
        lang_sel = build_lang_options("tam+eng")
        formats_cards = build_formats_display()
        content = f"""
<div class="hero">
    <div class="hero-content">
        <h2>Extract Text from Any Document</h2>
        <p>Upload PDFs, images, Word, Excel, or text files &mdash; get Tamil + English OCR in seconds</p>
        <form method="post" enctype="multipart/form-data" class="upload-form" id="upload-form">
            <input type="file" name="file" id="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp,.gif,.docx,.xlsx,.csv,.txt" required>
            <div class="form-row">
                <select name="lang" id="lang">{lang_sel}</select>
                <input type="number" name="start_page" placeholder="From page" min="1" value="1" title="Start page (PDF only)">
                <input type="number" name="end_page" placeholder="To page (auto)" min="1" title="End page, leave empty for all pages">
            </div>
            <button type="submit" class="upload-btn">&#128269; Extract Text</button>
        </form>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>&#128161; How It Works</h2>
        <p>Upload any supported file and our engine extracts text for you. PDFs and images use Tesseract OCR, while Office and text files are read directly.</p>
        <div class="tip-box">
            <h4><span class="tip-icon">&#9889;</span> Pro Tip</h4>
            <p>For best OCR results, use high-resolution images (300 DPI+). Select "Auto Detect" to automatically identify Tamil or English text. Use page range fields to process specific PDF pages.</p>
        </div>
    </div>
    <div class="content-section">
        <h2>&#128230; Supported Formats</h2>
        <div class="formats-grid">{formats_cards}</div>
    </div>
</div>
"""
    else:
        content = result_html

    return render_page("Upload & Extract Text", content, "upload")


@app.route("/downloads")
def downloads():
    if download_history:
        rows = ""
        for item in download_history:
            rows += f"""<tr>
                <td>{item['filename']}</td>
                <td>{item['date']}</td>
                <td>{item['words']}</td>
                <td><a href="/download/{item['id']}" class="btn btn-primary" style="padding:6px 16px;font-size:0.85rem;">&#128229; Download</a></td>
            </tr>"""
        content = f"""
<div class="container">
    <div class="section-title"><h2>&#128230; Download History</h2></div>
    <div class="content-section">
        <table class="download-table">
            <thead><tr><th>File Name</th><th>Date</th><th>Words</th><th>Action</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
</div>
"""
    else:
        content = """
<div class="container">
    <div class="section-title"><h2>&#128230; Download History</h2></div>
    <div class="content-section" style="text-align:center;padding:4rem 2rem;">
        <p style="font-size:1.2rem;color:#666;">No downloads yet.</p>
        <p style="margin-top:1rem;"><a href="/" class="btn btn-primary">&#128196; Upload a file</a></p>
    </div>
</div>
"""
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
