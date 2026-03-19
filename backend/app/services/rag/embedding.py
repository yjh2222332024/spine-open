"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List
import logging
import asyncio
import os
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    【架构师级：智能双模 Embedding 服务】
    
    1. 云端模式: 接入 SiliconFlow 等兼容 OpenAI 协议的供应商 (推荐，免模型下载)。
    2. 本地模式: 降级使用 SentenceTransformer (涉及 700MB+ 模型下载)。
    """
    
    def __init__(self):
        self.cloud_enabled = settings.EMBEDDING_API_KEY is not None
        self.local_model = None
        
        if self.cloud_enabled:
            logger.info(f"☁️ Using Cloud Embedding (Provider: {settings.EMBEDDING_BASE_URL})")
            self.client = AsyncOpenAI(
                api_key=settings.EMBEDDING_API_KEY,
                base_url=settings.EMBEDDING_BASE_URL,
                timeout=settings.AI_TIMEOUT
            )
        else:
            logger.warning("⚠️ No Embedding API Key found. Will attempt to load local model (Heavy Download)...")

    async def _get_local_model(self):
        """延迟加载本地模型，防止启动时阻塞"""
        if self.local_model is None:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"🚀 Loading local model on {device}...")
                self.local_model = SentenceTransformer("BAAI/bge-base-zh-v1.5", device=device)
            except Exception as e:
                logger.error(f"❌ Failed to load local model: {e}")
                raise
        return self.local_model

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        根据配置自动切换云端或本地获取向量，支持自动分批处理。
        """
        if not texts:
            return []

        # 🚀 工业级分批处理逻辑
        BATCH_SIZE = 32
        all_embeddings = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i + BATCH_SIZE]
            batch_embeds = await self._process_batch(batch_texts)
            all_embeddings.extend(batch_embeds)
            
        return all_embeddings

    async def _process_batch(self, texts: List[str]) -> List[List[float]]:
        """处理单批次向量化，增加强制截断与错误隔离"""
        # 🚀 架构师级防护：全局强制截断所有文本，确保不超 API Token 限制
        safe_texts = [t[:500] for t in texts]

        if self.cloud_enabled:
            try:
                response = await self.client.embeddings.create(
                    model=settings.EMBEDDING_MODEL_NAME,
                    input=safe_texts
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error(f"☁️ Cloud Embedding Error: {e}")
                # 云端报错后根据环境决定是否降级
        
        # 🛡️ 工业级兜底：在测试环境下，禁止阻塞性的模型下载
        if os.getenv(" TEST_MODE") == "True":
            logger.warning("🧪 TEST_MODE: Skip local model fallback to avoid network stalls.")
            return [[0.0] * 768] * len(texts)

        # 正常本地逻辑
        model = await self._get_local_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, lambda: model.encode(safe_texts, normalize_embeddings=True))
        return embeddings.tolist()

# 导出全局单例
embedding_service = EmbeddingService()
