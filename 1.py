#!/usr/bin/env python3
"""
OCR a large PDF (Tamil) page by page using Tesseract.
Output file is updated after each page.
"""

import argparse
import os
import sys
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def main():
    parser = argparse.ArgumentParser(
        description="Extract Tamil text from a large PDF using Tesseract OCR (page by page)."
    )
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("output_path", help="Path to the output text file")
    parser.add_argument("--lang", default="tam", help="Tesseract language code (default: 'tam' for Tamil)")
    parser.add_argument("--poppler_path", help="Path to poppler's bin folder (if not in system PATH)")
    parser.add_argument("--tesseract_path", help="Path to tesseract executable (if not in system PATH)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rendering (default: 300)")
    parser.add_argument("--start_page", type=int, default=1, help="First page to process (1‑based, default: 1)")
    parser.add_argument("--end_page", type=int, default=None, help="Last page to process (inclusive, default: last page)")
    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    # Set Tesseract path if provided
    if args.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_path

    # Verify Tesseract is available
    try:
        pytesseract.get_tesseract_version()
    except Exception as e:
        print(f"Error: Tesseract not found. Please install Tesseract or provide correct --tesseract_path.")
        print(f"Details: {e}")
        sys.exit(1)

    # Get total number of pages using pdfinfo from poppler
    try:
        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(args.pdf_path, poppler_path=args.poppler_path)
        total_pages = info["pages"]
    except Exception as e:
        print(f"Error: Could not read PDF information. Is poppler installed?")
        print(f"Details: {e}")
        sys.exit(1)

    print(f"PDF has {total_pages} pages.")

    # Convert page range to 1‑based indices (pdf2image uses 1‑based)
    start = max(1, args.start_page)
    end = args.end_page if args.end_page is not None else total_pages
    end = min(end, total_pages)

    if start > end:
        print("Error: Invalid page range.")
        sys.exit(1)

    print(f"Processing pages {start} to {end}...")

    # Open output file and process pages one by one
    with open(args.output_path, "w", encoding="utf-8") as out_f:
        for page_num in range(start, end + 1):
            print(f"Page {page_num}...", end=" ", flush=True)
            try:
                # Render only the current page
                images = convert_from_path(
                    args.pdf_path,
                    dpi=args.dpi,
                    first_page=page_num,
                    last_page=page_num,
                    poppler_path=args.poppler_path
                )
                # images is a list with one image
                if not images:
                    raise RuntimeError("No image generated")
                img = images[0]

                # Perform OCR
                text = pytesseract.image_to_string(img, lang=args.lang)

                # Write to file with page separator
                out_f.write(f"--- Page {page_num} ---\n")
                out_f.write(text)
                out_f.write("\n\n")
                out_f.flush()
                print("done.")
            except Exception as e:
                print(f"ERROR: {e}")
                # Optionally write error marker
                out_f.write(f"--- Page {page_num} ---\n[OCR FAILED: {e}]\n\n")
                out_f.flush()
                # Continue with next page

    print(f"\nOCR completed. Output saved to: {args.output_path}")

if __name__ == "__main__":
    main()
