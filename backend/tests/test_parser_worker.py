import pytest
import os
from app.agents.nodes.parser_worker import parser_worker_node
from app.agents.state import DocumentState, DocumentType

def test_parser_worker_collaboration():
    # 测试一个已知的 Native PDF
    test_pdf = "backend/temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf"
    
    if not os.path.exists(test_pdf):
        pytest.skip("Test PDF not found.")

    state = DocumentState(
        file_path=test_pdf,
        instructions=[],
        structured_toc=[]
    )
    
    result = parser_worker_node(state)
    
    print(f"\nParser Worker Result for {test_pdf}:")
    print(f"Items Found: {len(result.get('structured_toc', []))}")
    print(f"Instructions Issued: {result.get('instructions')}")
    print(f"Confidence: {result.get('confidence_score')}")
    
    # 验证是否输出了结构化目录
    assert "structured_toc" in result
    # 验证是否输出了指令 (无论成功或失败)
    assert "instructions" in result

if __name__ == "__main__":
    test_parser_worker_collaboration()
