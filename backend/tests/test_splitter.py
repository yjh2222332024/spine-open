import sys
import os
import fitz
from uuid import uuid4

# 路径设置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.splitter import context_splitter

def test_context_aware_splitting():
    print("\n--- Testing ContextAwareSplitter ---")
    
    # 1. 准备模拟数据
    # 我们使用之前测试过的 PDF 文件
    target_pdf = "temp_uploads/cd568458-b938-453b-acf5-be9bc47a6fad.pdf"
    if not os.path.exists(target_pdf):
        print("Error: Test PDF not found.")
        return

    # 模拟目录数据 (基于之前的解析结果)
    mock_toc = [
        {"id": str(uuid4()), "title": "Abstract", "page": 1, "level": 1},
        {"id": str(uuid4()), "title": "1 Introduction", "page": 1, "level": 1},
        {"id": str(uuid4()), "title": "2 Overview", "page": 2, "level": 1},
    ]

    doc = fitz.open(target_pdf)
    
    try:
        # 2. 执行切片
        chunks = context_splitter.split_by_toc(doc, mock_toc)
        
        print(f"Total Chunks generated: {len(chunks)}")
        
        # 3. 验证前几个 Chunk
        for i, chunk in enumerate(chunks[:5]):
            print(f"\nChunk {i+1}:")
            print(f"  Title: {chunk['metadata']['title']}")
            print(f"  Page Range: {chunk['metadata']['page_start']} - {chunk['metadata']['page_end']}")
            # 打印内容的前 100 个字符，确认 Prefix 注入
            print(f"  Content Preview: {chunk['content'][:150]}...")

        # 验证最后一个内容是否正确关联到章节
        last_chunk = chunks[-1]
        print(f"\nLast Chunk Metadata: {last_chunk['metadata']}")

    finally:
        doc.close()

if __name__ == "__main__":
    test_context_aware_splitting()
