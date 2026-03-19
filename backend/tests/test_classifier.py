import pytest
import os
from app.agents.nodes.classifier import classifier_node
from app.agents.state import DocumentState, DocumentType

def test_classifier_with_real_pdf():
    # 寻找一个存在的 PDF 文件进行测试
    test_pdf = "backend/temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf"
    
    # 兼容性处理：如果上面的路径不对，尝试当前目录下的 1.md (虽然不是 PDF，但能测试错误处理)
    if not os.path.exists(test_pdf):
         # 如果测试环境没有那个 PDF，我们创建一个极简的空 state 验证逻辑健壮性
         state = DocumentState(file_path="non_existent.pdf")
         result = classifier_node(state)
         assert "processing_errors" in result
         return

    state = DocumentState(file_path=test_pdf)
    result = classifier_node(state)
    
    print(f"\nTest Result for {test_pdf}:")
    print(f"Type: {result.get('document_type')}")
    print(f"Confidence: {result.get('confidence_score')}")
    print(f"Pages: {result.get('total_pages')}")
    
    assert "document_type" in result
    assert result["total_pages"] > 0
    assert isinstance(result["document_type"], DocumentType)

if __name__ == "__main__":
    test_classifier_with_real_pdf()
