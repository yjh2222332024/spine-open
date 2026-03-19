import sys
import os
import asyncio

# 路径设置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.retriever import HybridRetriever

def test_hybrid_search():
    print("\n--- Testing HybridRetriever (BM25 + Vector + RRF + Rerank) ---")
    
    # 1. 模拟一些文档块 (Chunks)
    chunks = [
        "The project is called StructuRAG, a tool for deep document analysis.",
        "Bo Hui is a researcher at Johns Hopkins University studying LLM security.",
        "Prompt Leaking attacks aim to extract system prompts from LLM applications.",
        "Computer Vision uses convolutional neural networks for image processing.",
        "RRF (Reciprocal Rank Fusion) is used to combine results from different retrievers.",
        "FastAPI is a modern web framework for building APIs with Python 3.12."
    ]

    try:
        # 2. 初始化检索器
        # 注意：这里会尝试下载模型，如果本地没有的话
        retriever = HybridRetriever(
            embedding_model_name="all-MiniLM-L6-v2", 
            rerank_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2" # 使用更轻量的模型进行测试
        )
        
        # 3. 构建索引
        print("\nBuilding index...")
        retriever.build_index(chunks)
        
        # 4. 执行搜索
        query = "Who is Bo Hui and what does he study?"
        print(f"\nQuery: {query}")
        results = retriever.search(query, top_k=2)
        
        print("\nSearch Results:")
        for i, res in enumerate(results):
            print(f"  {i+1}. {res}")

        # 验证关键词匹配能力
        query_kw = "FastAPI Python"
        print(f"\nQuery (Keyword): {query_kw}")
        results_kw = retriever.search(query_kw, top_k=1)
        print(f"  Result: {results_kw[0] if results_kw else 'No match'}")

    except Exception as e:
        print(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    test_hybrid_search()