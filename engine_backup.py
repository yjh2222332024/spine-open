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

    async def compare_documents(self, topic: str, doc_ids: List[str], progress_callback=None) -> str:
        """
        🚀 跨文档协同融合 (V3.5 高并发加速版)
        """
        if progress_callback: progress_callback(f"正在全库检索主题: {topic}...")
        
        # 1. 智能预筛选 (Heuristic Pre-Filtering)
        # 提取主题关键词，缩小 LLM 摘要的范围，避免 136 次调用的 Token 爆炸
        topic_keywords = [k.upper() for k in re.split(r"[\s\W]+", topic) if len(k) > 2]
        
        all_section_tasks = []
        
        for d_id in doc_ids:
            doc = self.get_document(d_id)
            if not doc: continue
            
            # 仅对标题中包含关键词或前 3 个核心章节进行分析
            relevant_sections = []
            for item in doc["toc"]:
                title_upper = item["title"].upper()
                if any(k in title_upper for k in topic_keywords) or item.get("level", 1) == 1:
                    relevant_sections.append(item)
            
            # 限制单文档分析上限，防止过度消耗
            relevant_sections = relevant_sections[:5] 
            
            with fitz.open(doc["path"]) as pdf:
                for sec in relevant_sections:
                    try:
                        content = pdf[sec['page']-1].get_text("text")[:2500]
                        # 核心改进：创建异步任务，但不立即执行，稍后 gather
                        all_section_tasks.append(self._summarize_and_label(
                            d_id, doc["filename"], sec["title"], content, sec["page"]
                        ))
                    except: continue

        if not all_section_tasks:
            return "未发现相关的章节可供分析。"

        # 2. 并发蒸馏 (Parallel Distillation)
        if progress_callback: progress_callback(f"正在并发透析 {len(all_section_tasks)} 个核心节点...")
        all_candidates = await asyncio.gather(*all_section_tasks)
        # 过滤掉失败项
        all_candidates = [c for c in all_candidates if c]

        # 3. 横向对齐
        if progress_callback: progress_callback(f"正在针对 '{topic}' 执行跨文档语义对齐...")
        matches = await self.router.align_themes(topic, all_candidates)
        
        if not matches: return "未能找到语义相关的章节进行对比。"

        # 4. 对比合成
        if progress_callback: progress_callback(f"正在对齐 {len(matches)} 个共鸣点并生成大典综述...")
        context_block = "\n\n".join([f"来源: {m['filename']}\n章节: {m['title']}\n摘要: {m['summary']}" for m in matches])
        
        synthesis_prompt = (
            f"你是一位顶级架构师。请针对以下来自不同文档的摘要，生成关于主题 '{topic}' 的‘多文档深度对比综述’。\n"
            f"必须包含: 1.跨文档共识 2.关键[冲突]或指标差异 3.互补的洞察。\n\n资料库:\n{context_block}"
        )

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        resp = await client.chat.completions.create(model=settings.LLM_MODEL_NAME, messages=[{"role": "user", "content": synthesis_prompt}], temperature=0.4)
        return resp.choices[0].message.content

    async def _summarize_and_label(self, doc_id, filename, title, content, page):
        """异步摘要包装器"""
        try:
            summary = await self.summarizer.summarize_section(title, content)
            return {
                "doc_id": doc_id, "filename": filename,
                "title": title, "summary": summary, "page": page
            }
        except:
            return None

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
