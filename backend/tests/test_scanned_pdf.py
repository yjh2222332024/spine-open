"""
Test OCR behavior with scanned PDF (image-only PDF)

This test verifies what happens when:
1. PDF has no embedded TOC
2. PDF has no text layer (scanned PDF)
3. OCR engine is unavailable
"""

import fitz
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ocr_service import ocr_service
from app.services.parser import hybrid_parser

def create_scanned_pdf(path: str):
    """
    Create a test PDF that simulates a scanned PDF:
    - No embedded TOC
    - No text layer (only images)
    """
    doc = fitz.open()

    # Add a page with some text (this creates a text layer)
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Chapter 1: Introduction")
    page1.insert_text((50, 80), "Chapter 2: Background")
    page1.insert_text((50, 110), "Section 2.1: History")

    # Now let's convert text to image to simulate scanned PDF
    # Render page to image, then create new page with image
    pix = page1.get_pixmap(dpi=150)

    # Save to temporary file
    temp_img = "temp_img.png"
    pix.save(temp_img)

    # Create new document with image only
    doc2 = fitz.open()
    page = doc2.new_page()
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
    page.insert_image(rect, filename=temp_img)

    doc2.save(path)
    doc2.close()
    doc.close()

    # Cleanup temp image
    if os.path.exists(temp_img):
        os.remove(temp_img)

def check_pdf_structure(file_path: str):
    """
    Analyze PDF structure to determine type
    """
    print("\n" + "=" * 60)
    print("PDF Structure Analysis")
    print("=" * 60)

    doc = fitz.open(file_path)

    # Check 1: Has embedded TOC?
    raw_toc = doc.get_toc(simple=True)
    has_toc = len(raw_toc) > 0
    print(f"[1] Has embedded TOC: {has_toc}")
    if has_toc:
        print(f"    TOC entries: {len(raw_toc)}")

    # Check 2: Has text layer?
    page = doc[0]
    text = page.get_text()
    has_text = len(text.strip()) > 0
    print(f"[2] Has text layer: {has_text}")
    if has_text:
        print(f"    Text length: {len(text)} characters")
        print(f"    Text preview: {text[:100]}...")

    doc.close()

    return {
        "has_toc": has_toc,
        "has_text": has_text
    }

def test_scanned_pdf_processing():
    """
    Test how the system handles a scanned PDF
    """
    print("=" * 60)
    print("SCANNED PDF PROCESSING TEST")
    print("=" * 60)

    # Create test PDF
    test_pdf = "test_scanned.pdf"
    print(f"\n[Step 1] Creating test scanned PDF: {test_pdf}")
    create_scanned_pdf(test_pdf)

    # Analyze structure
    print("\n[Step 2] Analyzing PDF structure...")
    structure = check_pdf_structure(test_pdf)

    # Determine expected mode
    print("\n[Step 3] Determining expected processing mode...")
    if structure["has_toc"]:
        expected_mode = "Metadata Mode"
    elif structure["has_text"]:
        expected_mode = "Visual Mode (Font Analysis)"
    else:
        expected_mode = "OCR Mode (Scanned PDF)"

    print(f"    Expected mode: {expected_mode}")

    # Process with HybridParser
    print("\n[Step 4] Processing with HybridParser...")
    print("-" * 60)

    toc = hybrid_parser.extract_toc(test_pdf)

    print("-" * 60)
    print(f"\n[Step 5] Results:")
    print(f"    TOC entries found: {len(toc)}")

    if toc:
        print("    Sample entries:")
        for i, entry in enumerate(toc[:5]):
            print(f"      [{i}] Level {entry['level']}: {entry['title']} (page {entry['page']})")
    else:
        print("    [WARN] No TOC entries extracted!")

    # Analyze what happened
    print("\n[Step 6] Analysis:")
    if structure["has_toc"]:
        print("    -> Used Metadata Mode (from embedded TOC)")
    elif structure["has_text"]:
        print("    -> Used Visual Mode (font analysis)")
    else:
        print("    -> Should use OCR Mode, but:")
        if ocr_service.engine:
            print("      [PASS] OCR engine available")
            print("      OCR-based TOC extraction would work")
        else:
            print("      [FAIL] OCR engine NOT available!")
            print("      System returns empty list (partial degradation)")
            print("\n    [WARN]  IMPACT:")
            print("    - Scanned PDFs cannot be processed")
            print("    - Users will get empty TOC")
            print("    - System functionality degraded for this use case")

    # Cleanup
    if os.path.exists(test_pdf):
        os.remove(test_pdf)
        print(f"\n[Cleanup] Removed test file: {test_pdf}")

    print("\n" + "=" * 60)

def test_real_scanned_pdf():
    """
    Test with actual uploaded PDFs to see if they are scanned
    """
    print("\n" + "=" * 60)
    print("TEST REAL UPLOADED PDFs")
    print("=" * 60)

    test_files = [
        "temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf",
        "temp_uploads/cd568458-b938-453b-acf5-be9bc47a6fad.pdf"
    ]

    for test_pdf in test_files:
        if not os.path.exists(test_pdf):
            print(f"\n[SKIP] {os.path.basename(test_pdf)} - File not found")
            continue

        print(f"\n[Analyze] {os.path.basename(test_pdf)}")
        structure = check_pdf_structure(test_pdf)

        if structure["has_toc"]:
            print(f"    -> Type: Native PDF with embedded TOC")
            print(f"    -> Processing: Metadata Mode (no OCR needed)")
        elif structure["has_text"]:
            print(f"    -> Type: Native PDF without TOC")
            print(f"    -> Processing: Visual Mode (no OCR needed)")
        else:
            print(f"    -> Type: Scanned PDF (image-only)")
            print(f"    -> Processing: OCR Mode (REQUIRED but UNAVAILABLE)")
            print(f"    -> Impact: Cannot extract TOC from this PDF")

    print("\n" + "=" * 60)

def main():
    """
    Run all tests
    """
    print("\n" + "=" * 60)
    print("SCANNED PDF COMPATIBILITY TEST")
    print("=" * 60)
    print("\nThis test suite verifies:")
    print("  1. How system handles scanned PDFs (no text layer)")
    print("  2. What happens when OCR is unavailable")
    print("  3. Real impact on user experience")
    print("\n" + "=" * 60)

    # Test 1: Simulated scanned PDF
    test_scanned_pdf_processing()

    # Test 2: Analyze real uploaded PDFs
    test_real_scanned_pdf()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 60)

    print("\nCurrent OCR Engine Status:")
    print(f"  Available: {ocr_service.engine is not None}")
    print(f"  Mode: {'GPU' if ocr_service.use_gpu else 'CPU'}")

    print("\nScanned PDF Support:")
    if ocr_service.engine:
        print("  [PASS] OCR engine available")
        print("  [PASS] Scanned PDFs can be processed")
    else:
        print("  [FAIL] OCR engine unavailable")
        print("  [FAIL] Scanned PDFs CANNOT be processed")
        print("\n  User Impact:")
        print("  - Users uploading scanned PDFs will get empty TOC")
        print("  - System cannot analyze scanned documents")
        print("  - This is a significant functional gap")

    print("\nRecommended Actions:")
    print("\n  Option 1: Resolve PaddleOCR DLL Conflict")
    print("    - Install compatible PyTorch GPU version")
    print("    - Or use PyTorch CPU version with PaddlePaddle CPU")
    print("    - Pros: Full PaddleOCR features (tables, formulas)")
    print("    - Cons: Complex dependency management")

    print("\n  Option 2: Switch to RapidOCR")
    print("    - Install: pip install rapidocr-onnxruntime")
    print("    - No PyTorch dependency, lighter weight")
    print("    - Pros: Easy setup, no DLL conflicts")
    print("    - Cons: Fewer features than PaddleOCR")

    print("\n  Option 3: Accept Limited Scanned PDF Support")
    print("    - Document clearly that scanned PDFs are not supported")
    print("    - Add error message when no TOC can be extracted")
    print("    - Pros: No technical debt")
    print("    - Cons: Reduced functionality")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
