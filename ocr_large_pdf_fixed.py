#!/usr/bin/env python3
"""
OCR a large PDF (Tamil) page by page – robust version that does not need pdfinfo.
Processes pages sequentially until no more pages are found.
"""

import argparse
import os
import sys
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def main():
    parser = argparse.ArgumentParser(
        description="Extract Tamil text from a large PDF using Tesseract OCR (page by page, no page count needed)."
    )
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("output_path", help="Path to the output text file")
    parser.add_argument("--lang", default="tam", help="Tesseract language code (default: 'tam' for Tamil)")
    parser.add_argument("--poppler_path", help="Path to poppler's bin folder (if not in system PATH)")
    parser.add_argument("--tesseract_path", help="Path to tesseract executable (if not in system PATH)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rendering (default: 300)")
    parser.add_argument("--start_page", type=int, default=1, help="First page to process (1‑based, default: 1)")
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
        print("Tesseract found.")
    except Exception as e:
        print(f"Error: Tesseract not found. Please install Tesseract or provide correct --tesseract_path.")
        print(f"Details: {e}")
        sys.exit(1)

    # Check if poppler path exists (if provided)
    if args.poppler_path and not os.path.isdir(args.poppler_path):
        print(f"Warning: Poppler path '{args.poppler_path}' does not exist. Will rely on system PATH.")

    print(f"Processing PDF: {args.pdf_path}")
    print(f"Starting from page {args.start_page}")
    print(f"Output will be saved to: {args.output_path}")
    print("-" * 50)

    page_num = args.start_page
    with open(args.output_path, "w", encoding="utf-8") as out_f:
        while True:
            print(f"Attempting page {page_num}...", end=" ", flush=True)
            try:
                # Attempt to convert only the current page
                images = convert_from_path(
                    args.pdf_path,
                    dpi=args.dpi,
                    first_page=page_num,
                    last_page=page_num,
                    poppler_path=args.poppler_path
                )

                # If no image returned, we've reached the end of the PDF
                if not images:
                    print("no more pages – done.")
                    break

                # Perform OCR on the page image
                img = images[0]
                text = pytesseract.image_to_string(img, lang=args.lang)

                # Write to file with a page separator
                out_f.write(f"--- Page {page_num} ---\n")
                out_f.write(text)
                out_f.write("\n\n")
                out_f.flush()
                print("done.")
                page_num += 1  # move to next page

            except Exception as e:
                # If an exception occurs, it might be because the page doesn't exist
                # or some other error. We'll treat it as end of PDF and stop.
                print(f"ERROR: {e}")
                print("Stopping processing.")
                break

    print(f"\nOCR completed. Output saved to: {args.output_path}")

if __name__ == "__main__":
    main()
