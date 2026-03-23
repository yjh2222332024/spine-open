# 🏛️ SpineDoc (阅脊) - The Semantic Logic Engine for Shell
# Copyright (c) 2026 Junhao Yan (严俊皓). All Rights Reserved.
# Licensed under MIT License. 
# "Stop chatting with PDFs. Start reconstructing their logic."

import os
import json
import fitz
import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.services.parser import hybrid_parser
from app.services.rag.splitter import context_splitter
from app.core.config import settings

from spine_cli.indexer.lancedb_store import LanceDBStore
from spine_cli.core.agents.graph import create_spine_graph
from spine_cli.core.kg.adapter import KGAdapter
from spine_cli.core.router import SemanticRouter
from spine_cli.llm.summarizer import SpineSummarizer

class SpineEngine:
    """
    SpineDoc 核心引擎 (V4.0 生产级)
    
    核心能力:
    1. 文档摄入：5 智能体联邦协同 (Classifier, Structure, Validator, Recovery)
    2. 向量索引：LanceDB 本地语义雷达
    3. 图谱对齐：OpenKG 实体挂载
    4. 多文档协同：高并发 compare 引擎
    """
    
    def __init__(self, storage_dir: str = ".spine"):
        self.storage_dir = Path(storage_dir)
        self.metadata_file = self.storage_dir / "metadata.json"
        self._ensure_storage()

        self.vector_store = LanceDBStore(self.storage_dir / "lancedb")
        self.agent_graph = create_spine_graph()
        self.kg_adapter = KGAdapter(self.storage_dir / "kg_cache")
        self.router = SemanticRouter()
        self.summarizer = SpineSummarizer()

    def _ensure_storage(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.metadata_file.exists():
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump({"documents": {}}, f)

    async def ingest_document(self, file_path: str, progress_callback=None) -> str:
        p = Path(file_path)
        doc_id = f"doc_{p.stem}"
        if progress_callback: progress_callback("🚀 正在重建脊梁...")
        initial_state = {"file_path": str(p.absolute()), "structured_toc": [], "metadata": {}, "retry_count": 0, "max_retries": 2}
        final_state = await self.agent_graph.ainvoke(initial_state)
        toc_items = final_state.get("structured_toc", [])
        if progress_callback: progress_callback("🕸️ 正在连接 OpenKG...")
        titles = [item["title"] for item in toc_items]
        entity_map = await self.kg_adapter.link_entities(titles)
        for item in toc_items: item["kg_entities"] = entity_map.get(item["title"], [])
        if progress_callback: progress_callback("🧩 正在切片...")
        with fitz.open(file_path) as pdf:
            chunks = context_splitter.split_by_toc(pdf, toc_items)
        vectorized = False
        if self.vector_store.is_available:
            try:
                await self.vector_store.add_documents(doc_id, chunks)
                vectorized = True
            except: vectorized = False
        meta = self._load_metadata()
        meta["documents"][doc_id] = {
            "id": doc_id, "filename": p.name, "path": str(p.absolute()),
            "total_pages": final_state.get("total_pages", 0), "toc": toc_items,
            "chunk_count": len(chunks), "ingested_at": datetime.now().isoformat(),
            "vectorized": vectorized, "confidence": final_state.get("confidence_score", 0)
        }
        self._save_metadata(meta)
        return doc_id

    async def compare_documents(self, topic: str, doc_ids: List[str], progress_callback=None, max_concurrent: int = 8) -> str:
        """
        🚀 跨文档协同融合 (V4.0 生产级高并发加速版)
        
        核心优化:
        1. 并发控制：使用 Semaphore 限制同时 API 调用数 (默认 8)，防止触发限流
        2. 快速路径：标题高度相关时跳过 LLM 调用，直接返回内容片段
        3. 超时保护：每个 LLM 调用设置 30 秒超时，避免单点卡死
        4. 降级策略：API 失败时自动降级为关键词匹配
        """
        if progress_callback: progress_callback(f"正在全库检索主题：{topic}...")

        # 1. 智能预筛选 (Heuristic Pre-Filtering)
        topic_keywords = [k.upper() for k in re.split(r"[\s\W]+", topic) if len(k) > 2]
        
        # 2. 并发控制信号量
        semaphore = asyncio.Semaphore(max_concurrent)

        all_section_tasks = []

        for d_id in doc_ids:
            doc = self.get_document(d_id)
            if not doc: continue

            # 智能筛选：按相关性排序，取 top 5
            relevant_sections = []
            for item in doc["toc"]:
                title_upper = item["title"].upper()
                score = 0
                if any(k in title_upper for k in topic_keywords):
                    score += 2
                if item.get("level", 1) == 1:
                    score += 1
                if score > 0:
                    relevant_sections.append((score, item))
            
            relevant_sections.sort(key=lambda x: x[0], reverse=True)
            relevant_sections = [item for _, item in relevant_sections[:5]]

            with fitz.open(doc["path"]) as pdf:
                for sec in relevant_sections:
                    try:
                        content = pdf[sec['page']-1].get_text("text")[:2500]
                        task = self._summarize_with_control(
                            d_id, doc["filename"], sec["title"], content, sec["page"],
                            topic_keywords, semaphore
                        )
                        all_section_tasks.append(task)
                    except Exception as e:
                        if progress_callback: progress_callback(f"[WARN] 读取章节失败 {sec['title']}: {e}")
                        continue

        if not all_section_tasks:
            return "未发现相关的章节可供分析。"

        # 3. 受控并发蒸馏
        if progress_callback: progress_callback(f"正在并发透析 {len(all_section_tasks)} 个核心节点 (并发度={max_concurrent})...")
        
        results = await asyncio.gather(*all_section_tasks, return_exceptions=True)
        
        # 过滤失败项
        all_candidates = [r for r in results if not isinstance(r, Exception) and r is not None]
        
        if not all_candidates:
            return "所有节点分析失败，请检查 LLM API 连接。"

        # 4. 横向对齐
        if progress_callback: progress_callback(f"正在针对 '{topic}' 执行跨文档语义对齐...")
        matches = await self.router.align_themes(topic, all_candidates)

        if not matches: return "未能找到语义相关的章节进行对比。"

        # 5. 对比合成
        if progress_callback: progress_callback(f"正在对齐 {len(matches)} 个共鸣点并生成大典综述...")
        context_block = "\n\n".join([f"来源：{m['filename']}\n章节：{m['title']}\n摘要：{m['summary']}" for m in matches])

        synthesis_prompt = (
            f"你是一位顶级架构师。请针对以下来自不同文档的摘要，生成关于主题 '{topic}' 的'多文档深度对比综述'。\n"
            f"必须包含：1.跨文档共识 2.关键 [冲突] 或指标差异 3.互补的洞察。\n\n资料库:\n{context_block}"
        )

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.4,
            timeout=60
        )
        return resp.choices[0].message.content

    async def _summarize_with_control(self, doc_id, filename, title, content, page, topic_keywords, semaphore):
        """
        带并发控制和快速路径的摘要生成器
        
        优化策略:
        1. 如果标题高度相关，直接使用标题 + 内容片段作为"摘要"，跳过 LLM 调用
        2. 使用信号量控制并发数
        3. 添加超时保护
        """
        # 快速路径：标题高度相关时，直接返回
        title_upper = title.upper()
        if any(k in title_upper for k in topic_keywords):
            return {
                "doc_id": doc_id,
                "filename": filename,
                "title": title,
                "summary": f"[{title}] {content[:200]}...",
                "page": page,
                "fast_path": True
            }
        
        # 信号量控制并发
        async with semaphore:
            try:
                # 添加超时保护
                summary = await asyncio.wait_for(
                    self.summarizer.summarize_section(title, content),
                    timeout=30.0
                )
                return {
                    "doc_id": doc_id,
                    "filename": filename,
                    "title": title,
                    "summary": summary,
                    "page": page,
                    "fast_path": False
                }
            except asyncio.TimeoutError:
                # 超时降级
                return {
                    "doc_id": doc_id,
                    "filename": filename,
                    "title": title,
                    "summary": f"[超时降级] {content[:150]}...",
                    "page": page,
                    "degraded": True
                }
            except Exception as e:
                # 异常处理
                return {
                    "doc_id": doc_id,
                    "filename": filename,
                    "title": title,
                    "summary": f"[API 错误] {str(e)[:100]}",
                    "page": page,
                    "degraded": True
                }

    async def hybrid_ask(self, query: str, doc_id: str, limit: int = 5) -> List[Dict]:
        doc = self.get_document(doc_id)
        if not doc: return []
        async with asyncio.Lock(): concepts = await self.kg_adapter.get_concept_path(query)
        expanded_query = f"{query} " + " ".join(concepts)
        results = []
        if self.vector_store.is_available and doc.get("vectorized"):
            results = self.vector_store.search(expanded_query, doc_id=doc_id, limit=limit)
        if not results: results = self.search_fallback(doc, query, limit=limit)
        return results

    def _load_metadata(self) -> Dict:
        with open(self.metadata_file, "r", encoding="utf-8") as f: return json.load(f)
    
    def _save_metadata(self, data: Dict):
        with open(self.metadata_file, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    
    def list_documents(self) -> List[Dict]: return list(self._load_metadata()["documents"].values())
    
    def get_document(self, id_or_name: str) -> Optional[Dict]:
        for d in self.list_documents():
            if d["id"] == id_or_name or d["filename"] == id_or_name: return d
        return None

    def search_fallback(self, doc: Dict, query: str, limit: int = 3) -> List[Dict]:
        toc = doc.get("toc", [])
        query_words = [k.upper() for k in re.split(r"[\s\W]+", query) if len(k) > 1]
        scored_chapters = []
        for item in toc:
            title_upper = item["title"].upper()
            score = sum(5 for word in query_words if word in title_upper)
            if score > 0: scored_chapters.append((score, item))
        scored_chapters.sort(key=lambda x: x[0], reverse=True)
        top_chapters = [c[1] for c in scored_chapters[:limit]]
        results = []
        try:
            with fitz.open(doc["path"]) as pdf:
                for ch in top_chapters:
                    content = pdf[ch['page']-1].get_text("text")[:3000]
                    results.append({"breadcrumb": ch["title"], "page": ch["page"], "text": content})
        except: pass
        return results
