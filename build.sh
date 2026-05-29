#!/usr/bin/env bash
set -e

# Install system deps: tesseract-ocr + Indian language packs + poppler (for pdf2image)
# Try apt-get directly (Render build env runs as root), fall back to sudo
APT_CMD="apt-get"
if ! command -v apt-get &>/dev/null; then
  APT_CMD="sudo apt-get"
fi
$APT_CMD update -qq 2>&1 || true
$APT_CMD install -y -qq \
  tesseract-ocr \
  tesseract-ocr-tam tesseract-ocr-hin tesseract-ocr-mal \
  tesseract-ocr-tel tesseract-ocr-kan tesseract-ocr-ben \
  tesseract-ocr-guj tesseract-ocr-pan tesseract-ocr-mar \
  tesseract-ocr-eng tesseract-ocr-ara poppler-utils 2>&1 || echo "apt-get returned non-zero; continuing..."
echo "=== tesseract location ==="
which tesseract 2>&1 || echo "which: not found"
command -v tesseract 2>&1 || echo "command -v: not found"
ls -la /usr/bin/tesseract 2>&1 || echo "ls: not found at /usr/bin/tesseract"
echo "=== tesseract version ==="
tesseract --version 2>&1 | head -3 || echo "tesseract command failed"

# Install pycryptodome first (builds fine on Python 3.14)
pip install pycryptodome

# Install mega.py without its broken pycrypto dependency
# We set MEGA_USE_CRYPTO_DOME so mega.py uses pycryptodome instead
MEGA_USE_CRYPTO_DOME=1 pip install --no-deps mega.py

# Install remaining dependencies
pip install -r requirements.txt
