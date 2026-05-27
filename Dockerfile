FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tam \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-tel \
    tesseract-ocr-mal \
    tesseract-ocr-kan \
    tesseract-ocr-guj \
    tesseract-ocr-ben \
    tesseract-ocr-mar \
    tesseract-ocr-urd \
    tesseract-ocr-san \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytesseract pdf2image Pillow flask gunicorn \
    python-docx openpyxl

COPY app.py /app/app.py
WORKDIR /app

ENV PORT=10000
EXPOSE 10000

CMD gunicorn --bind 0.0.0.0:${PORT} app:app
