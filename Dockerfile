FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tam \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytesseract pdf2image Pillow flask

COPY app.py /app/app.py
WORKDIR /app

ENV PORT=10000
EXPOSE 10000

CMD ["python", "app.py"]
