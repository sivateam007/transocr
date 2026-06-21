#!/usr/bin/env bash
set -e

# Install system deps: tesseract-ocr + language packs + poppler (for pdf2image)
apt-get update -qq 2>&1 || true
apt-get install -y -qq \
  tesseract-ocr \
  tesseract-ocr-tam tesseract-ocr-hin tesseract-ocr-mal \
  tesseract-ocr-tel tesseract-ocr-kan tesseract-ocr-ben \
  tesseract-ocr-guj tesseract-ocr-pan tesseract-ocr-mar \
  tesseract-ocr-eng tesseract-ocr-ara poppler-utils 2>&1 || echo "apt-get returned non-zero; continuing..."

echo "=== tesseract location ==="
which tesseract 2>&1 || echo "which: not found"
echo "=== tesseract version ==="
tesseract --version 2>&1 | head -3 || echo "tesseract command failed"

# Install Python dependencies
pip install -r requirements.txt

# Install mega.py (cloud storage) without --no-deps to avoid pulling pycrypto conflict
pip install mega.py==1.0.8 --no-deps
