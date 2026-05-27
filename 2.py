import argparse
import os
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("pdf_path")
parser.add_argument("output_path")
parser.add_argument("--lang", default="tam", help="Tesseract language code (e.g., tam for Tamil)")
args = parser.parse_args()

# Set tesseract path if not in system PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

images = convert_from_path(args.pdf_path, dpi=300)
with open(args.output_path, "w", encoding="utf-8") as f:
    for i, img in enumerate(images):
        print(f"Processing page {i+1}...")
        text = pytesseract.image_to_string(img, lang=args.lang)
        f.write(f"--- Page {i+1} ---\n")
        f.write(text)
        f.write("\n\n")
print("Done.")
