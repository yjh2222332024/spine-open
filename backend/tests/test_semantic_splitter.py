import sys
import os

# 路径设置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.splitter_semantic import SemanticSplitter

def test_semantic_splitting():
    print("\n--- Testing SemanticSplitter (Topic-based Chunking) ---")
    
    # 模拟一段包含两个不同话题的长文本
    long_text = (
        "StructuRAG is a high-performance RAG system designed for document analysis. "
        "It focuses on hierarchical parsing and context-aware chunking to improve accuracy. "
        "The system uses FastAPI for the backend and Flutter for the mobile app. "
        # 话题转换 ->
        "Global warming is causing rising sea levels and extreme weather patterns worldwide. "
        "Scientists agree that reducing carbon emissions is critical to mitigate the impact. "
        "Renewable energy sources like solar and wind power are key solutions for a sustainable future."
    )

    try:
        # 1. 初始化语义切片器
        splitter = SemanticSplitter(threshold=0.4) # 设低一点，让话题转换更明显
        
        # 2. 执行切片
        print("\nSplitting text...")
        chunks = splitter.split_text(long_text, min_chunk_len=50)
        
        print(f"Total Chunks generated: {len(chunks)}")
        
        # 3. 验证切片内容
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"  Content: {chunk}")

        # 预期结果：应该能识别出两个不同话题，将其切分为两个主要块
        if len(chunks) >= 2:
            print("\nVerification: Success! Multi-topic detection seems to be working.")
        else:
            print("\nVerification: Warning. Only one chunk generated. Threshold might be too low.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    test_semantic_splitting()