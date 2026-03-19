import pytest
import os
from app.agents.nodes.ocr_worker import ocr_worker_node
from app.agents.state import DocumentState, DocumentType

def test_ocr_worker_scanned_pdf():
    # 测试扫描件
    test_pdf = "backend/temp_uploads/cd568458-b938-453b-acf5-be9bc47a6fad.pdf"
    
    if not os.path.exists(test_pdf):
        pytest.skip("Scanned PDF not found.")

    state = DocumentState(
        file_path=test_pdf,
        document_type=DocumentType.SCANNED,
        instructions=[],
        raw_toc=[]
    )
    
    result = ocr_worker_node(state)
    
    print(f"\nOCR Worker Result for Scanned PDF:")
    print(f"Visual Items Found: {len(result.get('raw_toc', []))}")
    print(f"Confidence: {result.get('confidence_score')}")
    print(f"Instructions: {result.get('instructions')}")

    assert "raw_toc" in result
    assert result["current_node"] == "ocr_worker"

if __name__ == "__main__":
    test_ocr_worker_scanned_pdf()
