import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.retriever import HybridRetriever
from app.services.rag.splitter_semantic import SemanticSplitter

def calculate_metrics(results, ground_truth_substring):
    """
    计算单个 Query 的 Hit 和 RR (Reciprocal Rank)
    """
    try:
        # 找到包含 Ground Truth 的结果的排名 (0-based)
        rank = -1
        for i, res in enumerate(results):
            if ground_truth_substring in res:
                rank = i
                break
        
        hit = 1 if rank != -1 else 0
        rr = 1.0 / (rank + 1) if rank != -1 else 0.0
        return hit, rr
    except Exception:
        return 0, 0.0

def run_benchmark():
    print("\n===============================================")
    print("   StructuRAG Retrieval Benchmark (Member A)   ")
    print("===============================================")

    # 1. 初始化
    print("\n[Step 1] Initializing Engine...")
    splitter = SemanticSplitter(threshold=0.4)
    retriever = HybridRetriever() # 默认使用 SOTA 模型

    # 2. 准备语料库 (模拟长文档知识点)
    # 包含：技术原理、食谱、历史、专有名词
    raw_text = (
        "StructuRAG uses a TOC-driven architecture to solving context loss. "
        "The HybridParser extracts metadata and visual styles from PDFs. "
        "SemanticSplitter cuts text based on cosine similarity breakpoints. "
        "Deep learning relies on backpropagation for gradient descent. "
        "To cook pasta, boil water with salt for 10 minutes. "
        "The Apollo 11 mission landed on the moon in 1969. "
        "Project Alpha-8822 requires level 5 security clearance. "
        "The capital of France is Paris, known for the Eiffel Tower."
    )
    
    chunks = splitter.split_text(raw_text)
    print(f"\n[Step 2] Indexing {len(chunks)} Semantic Chunks...")
    retriever.build_index(chunks)

    # 3. 定义测试集 (Query -> 期待命中的关键词)
    test_set = [
        ("How does StructuRAG solve context loss?", "TOC-driven"),
        ("What extracts visual styles?", "HybridParser"),
        ("What algorithm does semantic splitting use?", "cosine similarity"),
        ("How to cook pasta?", "boil water"),
        ("When did Apollo 11 land?", "1969"),
        ("What is the code for Project Alpha?", "Alpha-8822"), # 混合检索大考
        ("Where is the Eiffel Tower?", "Paris")
    ]

    print(f"\n[Step 3] Running Evaluation on {len(test_set)} Queries...")
    
    hits = []
    rrs = []

    for query, truth in test_set:
        print(f"\nQ: '{query}'")
        # 检索 Top-3
        results = retriever.search(query, top_k=3)
        
        # 打印 Top-1 方便调试
        top_1_preview = results[0][:50] + "..." if results else "None"
        print(f"  -> Top 1: {top_1_preview}")
        
        hit, rr = calculate_metrics(results, truth)
        hits.append(hit)
        rrs.append(rr)
        
        status = "✅" if hit else "❌"
        print(f"  -> {status} (Rank: {int(1/rr) if rr > 0 else 'N/A'}, Truth: '{truth}')")

    # 4. 计算整体指标
    mrr = np.mean(rrs)
    hit_rate = np.mean(hits)

    print("\n===============================================")
    print(f"   FINAL SCORE CARD (Target: MRR > 0.8)   ")
    print("===============================================")
    print(f"Hit Rate @ 3:  {hit_rate:.2%}")
    print(f"MRR (Mean Reciprocal Rank): {mrr:.4f}")
    
    if mrr > 0.8:
        print("\n🚀 RESULT: SOTA Level Performance achieved!")
    else:
        print("\n⚠️ RESULT: Optimization needed.")

if __name__ == "__main__":
    run_benchmark()
