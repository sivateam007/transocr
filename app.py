import os
import tempfile
from io import BytesIO
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, send_file, url_for
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

results = {}
download_history = []

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
header { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 1rem 0; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.1); animation: slideDown 0.8s ease-out; }
@keyframes slideDown { from { transform: translateY(-100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.header-container { display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.logo { display: flex; align-items: center; gap: 15px; }
.logo-icon { font-size: 2rem; color: var(--accent); animation: pulse 2s infinite; }
@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
.logo h1 { font-size: 1.8rem; color: white; }
.logo span { color: var(--accent); }
.nav-tabs { display: flex; justify-content: center; max-width: 1200px; margin: 2rem auto; padding: 0 20px; gap: 1rem; flex-wrap: wrap; }
.nav-tab { display: flex; align-items: center; gap: 10px; padding: 12px 25px; background: white; color: var(--primary); border-radius: 10px; text-decoration: none; font-weight: 600; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid transparent; }
.nav-tab:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.15); border-color: var(--git-color); }
.nav-tab.active { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; border-color: var(--git-color); }
.hero { background: linear-gradient(135deg, var(--git-color), #6e5494); color: white; padding: 4rem 0; text-align: center; position: relative; overflow: hidden; }
.hero:before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.1" d="M0,96L48,112C96,128,192,160,288,186.7C384,213,480,235,576,213.3C672,192,768,128,864,128C960,128,1056,192,1152,192C1248,192,1344,128,1392,96L1440,64L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>'); background-size: cover; background-position: center; }
.hero-content { max-width: 800px; margin: 0 auto; padding: 0 20px; position: relative; z-index: 1; animation: fadeInUp 1s ease-out; }
@keyframes fadeInUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.hero h2 { font-size: 2.8rem; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
.hero p { font-size: 1.3rem; margin-bottom: 2.5rem; }
.upload-form { max-width: 600px; margin: 0 auto; }
.upload-form input[type=file] { display: block; width: 100%; padding: 1rem; background: rgba(255,255,255,0.15); border: 2px dashed rgba(255,255,255,0.4); border-radius: 12px; color: white; cursor: pointer; margin-bottom: 1.5rem; transition: all 0.3s; }
.upload-form input[type=file]:hover { border-color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.25); }
.upload-form input[type=file]::file-selector-button { background: white; color: var(--git-color); border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; margin-right: 15px; cursor: pointer; }
.upload-btn { background: white; color: var(--git-color); border: none; padding: 14px 40px; border-radius: 10px; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.3s; width: 100%; }
.upload-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.upload-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.section-title { text-align: center; margin: 3rem 0 2rem; color: var(--dark); position: relative; animation: fadeIn 1s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.section-title:after { content: ''; display: block; width: 80px; height: 4px; background: var(--git-color); margin: 10px auto; border-radius: 2px; animation: expandWidth 1s ease-out 0.5s both; }
@keyframes expandWidth { from { width: 0; } to { width: 80px; } }
.content-section { margin-bottom: 2rem; padding: 2.5rem; border-radius: 15px; background-color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: transform 0.3s, box-shadow 0.3s; animation: fadeInUp 0.8s ease-out; }
.content-section:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }
.content-section h2 { color: var(--dark); margin-bottom: 1.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--git-color); display: inline-block; }
.result-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 1.5rem; max-height: 60vh; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 1rem 0; }
.result-actions { display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border-radius: 10px; font-weight: 600; text-decoration: none; transition: all 0.3s; border: none; cursor: pointer; font-size: 1rem; }
.btn-primary { background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.btn-secondary { background: white; color: var(--primary); border: 2px solid var(--primary); }
.btn-secondary:hover { background: var(--primary); color: white; }
.flash { padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; font-weight: 500; animation: fadeIn 0.5s ease-out; }
.flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.download-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.download-table th { background: var(--primary); color: white; padding: 12px 15px; text-align: left; font-weight: 600; }
.download-table td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; }
.download-table tr:hover { background: #f1f5f9; }
.tip-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-left: 6px solid #ffd700; padding: 2rem; margin: 2rem 0; border-radius: 12px; color: white; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3); position: relative; overflow: hidden; animation: slideInLeft 0.8s ease-out; }
.tip-box:before { content: ''; position: absolute; top: -50%; right: -50%; width: 100%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%); transform: rotate(45deg); }
@keyframes slideInLeft { from { transform: translateX(-20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.tip-box h4 { color: #ffd700; margin-bottom: 1rem; display: flex; align-items: center; gap: 12px; font-size: 1.3rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
.tip-box p { font-size: 1.1rem; line-height: 1.7; margin-bottom: 0; text-shadow: 1px 1px 1px rgba(0,0,0,0.1); }
.tip-icon { font-size: 1.5rem; animation: bounce 2s infinite; }
@keyframes bounce { 0%,20%,50%,80%,100% { transform: translateY(0); } 40% { transform: translateY(-5px); } 60% { transform: translateY(-3px); } }
footer { background: linear-gradient(135deg, var(--primary), var(--dark)); color: white; padding: 3rem 0 2rem; margin-top: 4rem; }
.footer-content { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2.5rem; max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.footer-column h3 { margin-bottom: 1.5rem; color: var(--accent); font-size: 1.3rem; }
.footer-column ul { list-style: none; }
.footer-column ul li { margin-bottom: 0.8rem; }
.footer-column ul li a { color: #ddd; text-decoration: none; transition: all 0.3s; display: inline-block; }
.footer-column ul li a:hover { color: white; padding-left: 5px; }
.copyright { text-align: center; margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1); color: #aaa; }
.home-icon { position: fixed; top: 20px; right: 20px; width: 50px; height: 50px; background: linear-gradient(135deg, var(--git-color), #e74c3c); color: white; text-decoration: none; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: all 0.3s ease; border: 2px solid white; animation: pulse 2s infinite; }
.home-icon:hover { background: linear-gradient(135deg, #e74c3c, var(--git-color)); transform: scale(1.1) translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); text-decoration: none; color: white; }
@media (max-width: 768px) { .header-container { flex-direction: column; text-align: center; } .nav-tabs { flex-direction: column; align-items: center; } .nav-tab { width: 100%; max-width: 300px; justify-content: center; } .hero h2 { font-size: 2rem; } .hero { padding: 3rem 0; } .content-section { padding: 1.5rem; } .result-actions { flex-direction: column; } .home-icon { width: 45px; height: 45px; font-size: 18px; top: 15px; right: 15px; } .logo h1 { font-size: 1.4rem; } }
@media (max-width: 480px) { .hero h2 { font-size: 1.5rem; } .hero p { font-size: 1rem; } .logo h1 { font-size: 1.2rem; } .home-icon { width: 40px; height: 40px; font-size: 16px; top: 12px; right: 12px; } }
</style>
</head>
<body>
<header>
    <div class="header-container">
        <div class="logo">
            <div class="logo-icon">&#128214;</div>
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

FOOTER = r"""
<footer>
    <div class="footer-content">
        <div class="footer-column">
            <h3>OCR Solutions</h3>
            <p style="color:#ddd;">Extract Tamil and English text from PDFs and images using Tesseract OCR technology.</p>
        </div>
        <div class="footer-column">
            <h3>Quick Links</h3>
            <ul>
                <li><a href="/">Upload File</a></li>
                <li><a href="/downloads">Downloads</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h3>Supported Formats</h3>
            <ul>
                <li>PDF Documents</li>
                <li>PNG Images</li>
                <li>JPEG / JPG</li>
                <li>TIFF / BMP</li>
            </ul>
        </div>
    </div>
    <div class="copyright">
        <p>&copy; 2026 OCR Solutions. All rights reserved.</p>
    </div>
</footer>
</body>
</html>
"""


def ocr_pdf(filepath: str, dpi: int = 300) -> str:
    pages = []
    page_num = 1
    while True:
        try:
            images = convert_from_path(filepath, dpi=dpi, first_page=page_num, last_page=page_num)
            if not images:
                break
            text = pytesseract.image_to_string(images[0], lang="tam+eng")
            images[0].close()
            if text.strip():
                pages.append(f"--- Page {page_num} ---\n{text}")
            page_num += 1
        except Exception:
            break
    return "\n\n".join(pages)


def ocr_image(filepath: str) -> str:
    with Image.open(filepath) as img:
        text = pytesseract.image_to_string(img, lang="tam+eng")
    return text


def render_page(title, content, active, flashes=None):
    if flashes is None:
        flashes = []
    return render_template_string(HEADER + content + FOOTER, title=title, active=active, flashes=flashes)


@app.route("/", methods=["GET", "POST"])
def index():
    result_html = None
    filename = ""
    session_id = ""
    word_count = 0

    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Please select a file to upload.", "error")
            return redirect("/")

        ext = os.path.splitext(f.filename.lower())[1]
        img_exts = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}

        if ext != ".pdf" and ext not in img_exts:
            flash(f"Unsupported file type: {ext}. Please upload a PDF or image.", "error")
            return redirect("/")

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                f.save(tmp.name)
                tmppath = tmp.name

            text = ocr_pdf(tmppath) if ext == ".pdf" else ocr_image(tmppath)
            os.unlink(tmppath)

            if not text.strip():
                flash("No text could be extracted. The file may be empty or unreadable.", "error")
                return redirect("/")

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

            result_html = f"""
<div class="hero">
    <div class="hero-content">
        <h2>Text Extracted Successfully</h2>
        <p>{word_count} words found in {filename}</p>
        <a href="/" class="upload-btn" style="display:inline-block;width:auto;padding:12px 30px;text-decoration:none;">&#128260; Process Another</a>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>&#128196; {filename}</h2>
        <p style="color:#666;margin-bottom:1rem;">{word_count} words extracted</p>
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
        content = """
<div class="hero">
    <div class="hero-content">
        <h2>Extract Text from PDFs & Images</h2>
        <p>Upload your document and get Tamil + English text in seconds</p>
        <form method="post" enctype="multipart/form-data" class="upload-form" id="upload-form">
            <input type="file" name="file" id="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp" required>
            <button type="submit" class="upload-btn" id="submit-btn">&#128269; Extract Text</button>
        </form>
    </div>
</div>
<div class="container">
    <div class="content-section">
        <h2>&#128161; How It Works</h2>
        <p>Upload a PDF document or image file (PNG, JPG, TIFF, BMP) and our OCR engine will extract the text content for you.</p>
        <div class="tip-box">
            <h4><span class="tip-icon">&#9889;</span> Pro Tip</h4>
            <p>For best results, use high-resolution images (300 DPI or higher). PDFs with clear, scanned text work best with Tamil language recognition.</p>
        </div>
    </div>
</div>
<script>
document.getElementById('upload-form')?.addEventListener('submit', function() {
    document.getElementById('submit-btn').disabled = true;
    document.getElementById('submit-btn').textContent = '\\u23f3 Processing...';
});
</script>
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
