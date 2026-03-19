"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
import logging
import asyncio
import numpy as np
import time
import httpx
from typing import List, Optional, AsyncGenerator, Dict, Any
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from openai import AsyncOpenAI
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload
from app.schemas.rag import RagQuery, ThinkingBudget
from app.core.config import settings
from app.core.models import Chunk, TocItem, Document

logger = logging.getLogger(__name__)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算余弦相似度"""
    arr1 = np.array(v1)
    arr2 = np.array(v2)
    norm1 = np.linalg.norm(arr1); norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0: return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))

class RAGEngine:
    """
    【工业级加固版】RAG 核心引擎
    特性：云端优先 Reranker、非阻塞加载、Batch 路径查询、自适应推理预算。
    """

    def __init__(self):
        self.llm_client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.AI_TIMEOUT
        )
        # Reranker 配置
        self._reranker = None
        self._reranker_loading = False
        self._reranker_failed = False
        self._executor = ThreadPoolExecutor(max_workers=2)
        # 探测云端 Reranker 是否可用
        self.cloud_rerank_enabled = settings.EMBEDDING_API_KEY is not None and "siliconflow" in settings.EMBEDDING_BASE_URL.lower()

    async def _rerank_cloud(self, query: str, documents: List[str]) -> List[float]:
        """☁️ 通过 SiliconFlow API 执行云端重排序"""
        url = "https://api.siliconflow.cn/v1/rerank"
        headers = {
            "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "BAAI/bge-reranker-v2-m3",
            "query": query,
            "documents": documents,
            "top_n": len(documents),
            "return_documents": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # SiliconFlow 的返回格式通常是 [{"index": 0, "relevance_score": 0.9}, ...]
                # 我们需要按照输入的原始顺序还原分数
                scores = [0.0] * len(documents)
                for res in data.get("results", []):
                    scores[res["index"]] = res["relevance_score"]
                return scores
        except Exception as e:
            logger.error(f"☁️ Cloud Rerank failed: {e}")
            return []

    async def _get_reranker(self):
        """非阻塞式本地 Reranker 加载 (带熔断器与测试保护)"""
        # 1. 优先使用云端，不加载本地模型
        if self.cloud_rerank_enabled:
            return "cloud"

        # 2. 测试模式严禁下载
        import os
        if os.getenv("TEST_MODE") == "True":
            logger.warning("🧪 TEST_MODE: Skipping heavy Reranker load.")
            return None

        if self._reranker_failed: return None
        if self._reranker is not None: return self._reranker
        if self._reranker_loading:
            await asyncio.sleep(0.2)
            return self._reranker

        self._reranker_loading = True
        try:
            def _load():
                from sentence_transformers import CrossEncoder
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"🚀 [INIT] Loading Local Reranker on {device}...")
                return CrossEncoder("BAAI/bge-reranker-v2-m3", device=device)

            loop = asyncio.get_event_loop()
            self._reranker = await asyncio.wait_for(
                loop.run_in_executor(self._executor, _load),
                timeout=60.0
            )
            return self._reranker
        except Exception as e:
            logger.error(f"❌ Local Reranker load failed: {e}")
            self._reranker_failed = True
            return None
        finally:
            self._reranker_loading = False

    async def _classify_query_complexity(self, query: str) -> ThinkingBudget:
        """
        🚀 极速启发式意图分类 (0 延迟，0 成本)
        基于关键字和长度判断问题复杂度，为 AUTO 模式定级。
        """
        complex_keywords = ["对比", "总结", "分析", "冲突", "为什么", "原因", "演进", "区别", "优缺点", "权衡", "瓶颈"]
        
        # 1. 如果问题很长，通常意味着条件苛刻
        if len(query) > 50:
            return ThinkingBudget.DEEP
            
        # 2. 如果包含复杂关键字，触发深度推理
        for kw in complex_keywords:
            if kw in query:
                return ThinkingBudget.DEEP
                
        # 3. 如果是特定实体的询问（如“xxx是谁”，“什么是yyy”）
        simple_keywords = ["是谁", "什么是", "多少", "在哪里", "第几页"]
        for kw in simple_keywords:
            if kw in query:
                return ThinkingBudget.FAST
                
        return ThinkingBudget.BALANCED

    async def search(self, query: str, document_id: UUID, 
                     budget: ThinkingBudget = ThinkingBudget.AUTO, 
                     session = None) -> Dict[str, Any]:
        """自适应检索实现"""
        start_time = time.time()
        
        # 1. 如果是 AUTO，先进行预分类
        actual_budget = budget
        if budget == ThinkingBudget.AUTO:
            actual_budget = await self._classify_query_complexity(query)
            logger.info(f"🤖 AUTO Mode: Query classified as [{actual_budget.value}]")
        
        params_map = {
            ThinkingBudget.FAST: {"limit": 3, "rerank": False, "routing": False},
            ThinkingBudget.BALANCED: {"limit": 5, "rerank": True, "routing": True},
            ThinkingBudget.DEEP: {"limit": 10, "rerank": True, "routing": True}
        }
        cfg = params_map.get(actual_budget, params_map[ThinkingBudget.BALANCED])
        
        from app.services.rag.embedding import embedding_service
        query_vec = (await embedding_service.get_embeddings([query]))[0]
        vec_str = "[" + ",".join(map(str, query_vec)) + "]"

        # 2. 章节路由
        relevant_ids = []
        if cfg["routing"]:
            relevant_ids = await self._get_relevant_chapters(query_vec, document_id, session)

        # 3. SQL 召回
        limit = cfg["limit"]
        sql_params = {"doc_id": document_id, "vec": vec_str, "t_ids": relevant_ids, "limit": limit * 2}
        sql = text("""
            SELECT id, content, page_number, toc_item_id, 
                   (embedding <=> :vec) * (CASE WHEN toc_item_id = ANY(:t_ids) THEN 0.7 ELSE 1.0 END) as distance
            FROM chunk WHERE document_id = :doc_id ORDER BY distance ASC LIMIT :limit
        """)
        raw_res = await session.execute(sql, sql_params)
        raw_chunks = raw_res.all()

        if not raw_chunks: 
            return {
                "chunks": [], 
                "metrics": {"latency_ms": int((time.time()-start_time)*1000), "budget": actual_budget.value, "status": "empty"}
            }

        # 4. 批量路径注入
        needed_toc_ids = list(set([c.toc_item_id for c in raw_chunks if c.toc_item_id]))
        path_map = await self._get_toc_paths_batch(needed_toc_ids, session)

        # 5. 智能重排序 (Reranking)
        final_chunks = []
        rerank_type = "none"
        if cfg["rerank"]:
            reranker_inst = await self._get_reranker()
            scores = []
            
            if reranker_inst == "cloud":
                rerank_type = "cloud"
                scores = await self._rerank_cloud(query, [c.content for c in raw_chunks])
            elif reranker_inst is not None:
                rerank_type = "local"
                pairs = [[query, c.content] for c in raw_chunks]
                loop = asyncio.get_event_loop()
                scores = await loop.run_in_executor(None, lambda: reranker_inst.predict(pairs))
            
            if scores:
                scored = sorted(zip(raw_chunks, scores), key=lambda x: x[1], reverse=True)[:limit]
                for c, s in scored:
                    final_chunks.append({
                        "content": c.content, "page": c.page_number, "toc_id": str(c.toc_item_id),
                        "full_path": path_map.get(c.toc_item_id, "未知章节"), "score": float(s)
                    })
                
                # 🚀 SOTA: SkewRoute 动态升级逻辑
                # 如果最高分低于 0.4，说明现有证据极度匮乏或矛盾，强制升级为 DEEP (如果它还不是)
                if budget == ThinkingBudget.AUTO and actual_budget != ThinkingBudget.DEEP and final_chunks:
                    top_score = final_chunks[0]["score"]
                    if top_score < 0.4:
                        logger.info(f"⚠️ Top score {top_score:.2f} is too low. Upgrading budget to DEEP.")
                        actual_budget = ThinkingBudget.DEEP
        
        if not final_chunks: # 降级或 FAST 模式
            for c in raw_chunks[:limit]:
                final_chunks.append({
                    "content": c.content, "page": c.page_number, "toc_id": str(c.toc_item_id),
                    "full_path": path_map.get(c.toc_item_id, "未知章节"), "score": 1-c.distance
                })

        return {
            "chunks": final_chunks,
            "metrics": {
                "latency_ms": int((time.time()-start_time)*1000), 
                "budget": actual_budget.value, 
                "rerank": rerank_type
            }
        }

    async def _get_relevant_chapters(self, query_vec, document_id, session):
        stmt = select(TocItem).where(TocItem.document_id == document_id)
        res = await session.execute(stmt); items = res.scalars().all()
        if not items: return []
        from app.services.rag.embedding import embedding_service
        title_vecs = await embedding_service.get_embeddings([i.title for i in items])
        scored = sorted([(i.id, cosine_similarity(query_vec, v)) for i, v in zip(items, title_vecs)], key=lambda x:x[1], reverse=True)
        return [id for id, s in scored[:3] if s > 0.35]

    async def embed_text(self, text: str) -> List[float]:
        """🚀 [SUPPORT] 单文本向量化接口，供 MCP 工具复用"""
        from app.services.rag.embedding import embedding_service
        vecs = await embedding_service.get_embeddings([text])
        return vecs[0]

    async def embed_text_batch(self, texts: List[str]) -> List[List[float]]:
        """🚀 [SUPPORT] 批量文本向量化接口，供超级智库 (RAPTOR) 复用"""
        from app.services.rag.embedding import embedding_service
        return await embedding_service.get_embeddings(texts)

    async def chat_stream(self, request: RagQuery, session=None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🚀 [SAP-9.0] 终极版阅脊引擎流：
        1. 自动热索引 (JIT Indexing)
        2. HMAC 激活 (Multi-Agent Fusion for DEEP mode)
        """
        yield {"type": "status", "content": f"正在启动阅脊自适应引擎 [初始模式: {request.thinking_budget.value}]..."}
        
        try:
            # --- 🛡️ 架构师防御：自动热索引检测 ---
            c_check = await session.execute(select(Chunk).where(Chunk.document_id == request.document_id).limit(1))
            if not c_check.scalars().first():
                yield {"type": "status", "content": "⚠️ 该文档尚未向量化，正在启动热索引引擎 (预计 30-60s)..."}
                from app.services.ai_pipeline import run_document_analysis_workflow
                # 阻塞执行直到索引完成
                await run_document_analysis_workflow(str(request.document_id))
                yield {"type": "status", "content": "✅ 热索引构建完成，继续执行逻辑检索..."}

            # 1. 深度检索 (这里会经历 SkewRoute 的动态预算调整)
            res = await self.search(request.query, request.document_id, budget=request.thinking_budget, session=session)
            chunks = res["chunks"]
            final_budget_str = res['metrics']['budget']
            
            if not chunks:
                yield {"type": "status", "content": "⚠️ 未能找到精准证据，正在尝试利用全局模型能力回答..."}
            else:
                yield {"type": "status", "content": f"检索完成 ({res['metrics']['latency_ms']}ms)。最终执行模式升级为: [{final_budget_str}]。"}

            # 2. 逻辑分支：激活 HMAC 还是 普通生成
            if final_budget_str == "deep":
                yield {"type": "status", "content": "🧠 问题极具深度，已唤醒 HMAC 多智能体辩论与冲突检测..."}
                from app.services.aggregator import knowledge_aggregator
                
                # 转换格式适配聚合器
                doc_data = [
                    {
                        "title": c["full_path"],
                        "summary": c["content"],
                        "source": f"P{c['page']}",
                        "page_range": [c["page"], c["page"]]
                    } for c in chunks
                ]
                
                # 执行 HMAC 深度熔炼
                fused_report = await knowledge_aggregator.synthesize_domain_knowledge(request.query, doc_data)
                
                # 流式模拟输出 (因为聚合器目前返回的是全量文本)
                for char in fused_report:
                    yield {"type": "message", "content": char}
                    if char in ["。", "！", "\n"]: await asyncio.sleep(0.01) # 增加呼吸感
            
            else:
                # BALANCED / FAST 模式：标准生成
                context = "\n\n".join([f"【证据 {i+1} | {c['full_path']} | P{c['page']}】\n{c['content']}" for i, c in enumerate(chunks)])
                sys_prompt = f"你是一个专业的阅脊助手。请基于以下参考片段精准回答，引用时请标注路径。\n\n【参考片段】:\n{context}"
                
                yield {"type": "status", "content": "正在进行逻辑熔炼并生成专业回答..."}
                stream = await self.llm_client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": request.query}],
                    stream=True, temperature=0.1
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield {"type": "message", "content": chunk.choices[0].delta.content}
                        
        except Exception as e:
            logger.error(f"Engine CRITICAL Error: {e}")
            yield {"type": "error", "content": f"阅脊核心异常: {str(e)}"}

rag_engine = RAGEngine()
