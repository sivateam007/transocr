#!/usr/bin/env bash
set -e

# Install system deps: tesseract-ocr + Indian language packs
apt-get update -qq && apt-get install -y -qq \
  tesseract-ocr \
  tesseract-ocr-tam tesseract-ocr-hin tesseract-ocr-mal \
  tesseract-ocr-tel tesseract-ocr-kan tesseract-ocr-ben \
  tesseract-ocr-guj tesseract-ocr-pan tesseract-ocr-mar \
  tesseract-ocr-eng tesseract-ocr-ara 2>&1 | tail -5

# Install pycryptodome first (builds fine on Python 3.14)
pip install pycryptodome

# Install mega.py without its broken pycrypto dependency
# We set MEGA_USE_CRYPTO_DOME so mega.py uses pycryptodome instead
MEGA_USE_CRYPTO_DOME=1 pip install --no-deps mega.py

# Install remaining dependencies
pip install -r requirements.txt
