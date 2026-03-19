"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer
import numpy as np

class HybridRetriever:
    """
    混合检索器 (Hybrid Retriever)
    
    Pipeline:
    1. Sparse Retrieval (BM25): 关键词匹配，捕捉专有名词。
    2. Dense Retrieval (Vector): 语义匹配，捕捉隐含意图。
    3. Reranking (Cross-Encoder): 对混合结果进行深度语义打分，去噪。
    """

    def __init__(self, embedding_model_name="all-MiniLM-L6-v2", rerank_model_name="BAAI/bge-reranker-v2-m3"):
        print(f"Loading Retrieval Models (Reranker: {rerank_model_name})...")
        self.embedder = SentenceTransformer(embedding_model_name)
        # Cross-Encoder 用于重排序，它输入两个句子，输出相似度得分
        self.reranker = CrossEncoder(rerank_model_name)
        
        # 内存索引 (Production环境应使用 ES/Qdrant)
        self.bm25 = None
        self.documents = [] # 存储原始文本
        self.vectors = None

    def build_index(self, chunks: List[str]):
        """
        构建内存索引 (MVP专用)
        """
        self.documents = chunks
        
        # 1. 构建 BM25 索引 (分词)
        tokenized_corpus = [doc.split(" ") for doc in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # 2. 构建向量索引
        self.vectors = self.embedder.encode(chunks)
        print(f"Index built for {len(chunks)} documents.")

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        执行混合检索 + RRF 融合 + 重排序
        """
        if not self.documents:
            return []

        # Step 1: BM25 检索 (召回前 20)
        tokenized_query = query.split(" ")
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_n = np.argsort(bm25_scores)[::-1][:20]
        
        # Step 2: 向量检索 (召回前 20)
        query_vec = self.embedder.encode(query)
        # Cosine Similarity (假设向量已归一化，使用点积即可)
        vec_scores = np.dot(self.vectors, query_vec)
        vec_top_n = np.argsort(vec_scores)[::-1][:20]
        
        # Step 3: RRF (Reciprocal Rank Fusion) 融合
        # 这种方式不依赖于具体的 Score 分值，只看相对排名
        rrf_scores = {}
        k = 60 # RRF 算法常数，用于平滑低排名项

        # 累加 BM25 排名权重
        for rank, idx in enumerate(bm25_top_n):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)

        # 累加向量检索排名权重
        for rank, idx in enumerate(vec_top_n):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)

        # 按 RRF 得分降序排列，取前 20 个作为 Rerank 的输入
        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        candidate_indices = [idx for idx, score in sorted_rrf[:20]]
        candidates = [self.documents[idx] for idx in candidate_indices]
        
        if not candidates:
            return []

        # Step 4: Reranking (Cross-Encoder 深度打分)
        # 将 (Query, Doc) 对输入模型，获取精准的相关性分数
        pairs = [[query, doc] for doc in candidates]
        rerank_scores = self.reranker.predict(pairs)
        
        # 获取最终 Top-K 结果
        final_top_indices_local = np.argsort(rerank_scores)[::-1][:top_k]
        
        return [candidates[idx] for idx in final_top_indices_local]

# 单例导出
# hybrid_retriever = HybridRetriever()
