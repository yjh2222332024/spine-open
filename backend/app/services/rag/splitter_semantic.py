"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

class SemanticSplitter:
    """
    语义感知切片器 (Deep Semantic Splitter)
    
    不按字数切，按“意思”切。
    使用 Sentence-Transformers 计算句子间的语义相似度，
    当相似度低于阈值时，认为话题发生了转换，进行切分。
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.5):
        """
        Args:
            model_name: HuggingFace 模型名称 (推荐 all-MiniLM-L6-v2，小而快)。
            threshold: 相似度阈值 (0-1)。越低切得越少，越高切得越碎。
        """
        print(f"Loading Semantic Model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

    def split_text(self, text: str, min_chunk_len: int = 100) -> List[str]:
        """
        对长文本进行语义切片。
        min_chunk_len: 最小字符数，防止切得太碎导致丢失上下文。
        """
        # 1. 句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return sentences

        # 2. 计算 Embeddings
        embeddings = self.model.encode(sentences)

        # 3. 计算相邻句子的相似度
        breaks = []
        current_chunk_len = 0
        for i in range(len(embeddings) - 1):
            current_chunk_len += len(sentences[i])
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            
            # 只有当相似度低 且 当前累积长度达到最小值时，才允许切分
            if sim < self.threshold and current_chunk_len >= min_chunk_len:
                breaks.append(i + 1)
                current_chunk_len = 0
        
        # 4. 根据断点组装 Chunks
        chunks = []
        start_idx = 0
        for end_idx in breaks:
            chunk = " ".join(sentences[start_idx:end_idx])
            chunks.append(chunk)
            start_idx = end_idx
        
        last_chunk = " ".join(sentences[start_idx:])
        if last_chunk:
            chunks.append(last_chunk)

        return chunks

# 单例导出 (注意：模型加载可能较慢，建议懒加载或启动时加载)
# semantic_splitter = SemanticSplitter() 
