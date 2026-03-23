import numpy as np
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

class SemanticRouter:
    """
    SpineDoc 语义路由器 (CLI 增强版)
    负责将查询和文档节点映射到高维语义空间，实现跨文档的主题对齐。
    """
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL
        )
        self.model = settings.EMBEDDING_MODEL_NAME

    async def get_embedding(self, text: str) -> np.ndarray:
        """调用 Embedding API 将文本转化为向量"""
        try:
            # 简单清洗
            text = text.replace("\n", " ")
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            # 兜底返回零向量
            return np.zeros(settings.EMBEDDING_DIMENSION or 1024)

    def cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    async def align_themes(self, target_topic: str, candidates: List[Dict[str, Any]], threshold: float = 0.45) -> List[Dict[str, Any]]:
        """
        跨文档主题对齐：在多个文档候选项中寻找与目标主题语义最接近的节点。
        """
        query_vec = await self.get_embedding(target_topic)
        matches = []
        
        for item in candidates:
            # 组合标题和摘要进行语义判定
            semantic_content = f"{item.get('title', '')} {item.get('summary', '')}"
            item_vec = await self.get_embedding(semantic_content)
            score = self.cosine_similarity(query_vec, item_vec)
            
            if score >= threshold:
                item["alignment_score"] = score
                matches.append(item)
        
        # 按相关性排序
        return sorted(matches, key=lambda x: x["alignment_score"], reverse=True)
