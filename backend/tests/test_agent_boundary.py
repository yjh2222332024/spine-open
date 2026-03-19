import pytest
import os
import fitz
import logging
from app.agents.nodes.classifier import classifier_node
from app.agents.state import DocumentState

# 开启日志输出到控制台，以便测试时能看到我们刚加的监控日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

@pytest.fixture
def setup_corrupted_pdf(tmp_path):
    """制造一个损坏的 PDF 文件"""
    file_path = tmp_path / "corrupted.pdf"
    file_path.write_text("This is not a real PDF. This is garbage data.")
    return str(file_path)

@pytest.fixture
def setup_empty_pdf(tmp_path):
    """制造一个合法的但是大小为 0 字节的空文件 (模拟网络截断)"""
    file_path = tmp_path / "empty.pdf"
    file_path.write_bytes(b"")  # 直接写入 0 字节
    return str(file_path)

def test_boundary_file_not_found():
    """边界 1：文件根本不存在"""
    state = DocumentState(file_path="/path/that/does/not/exist.pdf")
    result = classifier_node(state)
    
    assert "processing_errors" in result
    assert "File path not found" in result["processing_errors"][0]

def test_boundary_corrupted_pdf(setup_corrupted_pdf):
    """边界 2：文件损坏或非 PDF 格式"""
    state = DocumentState(file_path=setup_corrupted_pdf)
    result = classifier_node(state)
    
    assert "processing_errors" in result
    assert "Corrupted PDF" in result["processing_errors"][0] or "failed" in result["processing_errors"][0]

def test_boundary_empty_pdf(setup_empty_pdf):
    """边界 3：网络截断导致的 0 字节空文件"""
    state = DocumentState(file_path=setup_empty_pdf)
    result = classifier_node(state)
    
    assert "processing_errors" in result
    # PyMuPDF 底层直接拒绝 0 字节文件，抛出 FileDataError
    assert "empty file" in result["processing_errors"][0] or "failed" in result["processing_errors"][0]

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
