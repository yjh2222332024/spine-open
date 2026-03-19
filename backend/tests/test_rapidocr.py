"""
Test RapidOCR basic functionality
"""
from rapidocr_onnxruntime import RapidOCR

# Initialize RapidOCR
ocr = RapidOCR()

# Test with a simple image
import fitz
import numpy as np

# Create a test page with text
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "Chapter 1: Introduction")
page.insert_text((50, 80), "Chapter 2: Background")

# Convert to image
pix = page.get_pixmap(dpi=150)
w, h = pix.width, pix.height
img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape((h, w, pix.n))

# OCR the image
result, elapse = ocr(img_data)

print("RapidOCR Test:")
print(f"Processing time: {elapse}")
print(f"Result type: {type(result)}")
print(f"Result: {result}")

if result:
    print(f"Number of text regions: {len(result)}")
    for item in result:
        print(f"  Item: {item}")
else:
    print("No text detected")

doc.close()
