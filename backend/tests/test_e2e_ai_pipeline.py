import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.splitter_semantic import SemanticSplitter
from app.services.rag.retriever import HybridRetriever

def test_e2e_pipeline():
    print("\n===============================================")
    print("   StructuRAG AI Pipeline E2E Test (Mock)   ")
    print("===============================================")

    # 1. 初始化组件
    print("\n[Step 1] Initializing Models (this may take a while)...")
    start_time = time.time()
    
    # 使用较宽松的阈值，确保测试文本能被切开
    splitter = SemanticSplitter(threshold=0.4) 
    retriever = HybridRetriever()
    
    print(f"Models loaded in {time.time() - start_time:.2f}s")

    # 2. 准备模拟长文档文本 (混合了不同主题)
    # 主题 1: 关于 StructuRAG 的介绍
    # 主题 2: 关于 深度学习的基础知识
    # 主题 3: 关于 咖啡制作教程
    raw_text = (
        "StructuRAG is a specialized RAG engine for long documents. "
        "It uses a TOC-driven approach to maintain context. "
        "Unlike traditional RAG, it respects the document hierarchy. "
        "Deep learning models require vast amounts of data for training. "
        "Neural networks are composed of layers of nodes. "
        "Backpropagation is the key algorithm for optimization. "
        "To brew a great cup of coffee, use freshly ground beans. "
        "Water temperature should be around 93 degrees Celsius. "
        "Pour water slowly over the grounds for even extraction."
    )

    print(f"\n[Step 2] Processing Text ({len(raw_text)} chars)...")

    # 3. 执行语义切片
    chunks = splitter.split_text(raw_text)
    print(f" -> Generated {len(chunks)} Semantic Chunks:")
    for i, c in enumerate(chunks):
        print(f"    Chunk {i+1}: {c[:50]}...")

    # 4. 建立索引
    print("\n[Step 3] Building Hybrid Index...")
    retriever.build_index(chunks)

    # 5. 执行检索测试
    # 测试 Query: 针对 StructuRAG 的具体问题
    query = "How does StructuRAG handle context?"
    print(f"\n[Step 4] Searching for: '{query}'")

    results = retriever.search(query, top_k=1)
    
    if results:
        top_result = results[0]
        print(f" -> Top Result: '{top_result}'")
        
        # 验证逻辑: 结果必须包含 StructuRAG 相关内容
        if "StructuRAG" in top_result and "context" in top_result:
            print("\n✅ TEST PASSED: AI Pipeline logic is sound.")
        else:
            print("\n❌ TEST FAILED: Retrieved irrelevant chunk.")
    else:
        print("\n❌ TEST FAILED: No results found.")

if __name__ == "__main__":
    test_e2e_pipeline()
