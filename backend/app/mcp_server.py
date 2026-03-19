"""
Spine-MCP Server (Open Source Edition)
======================================

开源版本 - 提供基础 RAG 检索和文档解析功能

功能列表:
- parse_document_spine: PDF 解析 +TOC 提取
- fast_track_analyze: 一键极速分析
- fetch_secure_physical_slice: 章节原文提取
- search_by_toc: 逻辑感知检索
- spine_chat: 端到端文档对话

Author: Yan Junhao (严俊皓)
Copyright (c) 2026 SpineDoc. All rights reserved.
License: MIT (Open Source)
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# MCP 依赖
try:
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.server.session import ServerSession
except ImportError:
    print("❌ MCP SDK not installed. Please run: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

# 项目路径
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# 核心服务（开源版本）
from app.services.parser import hybrid_parser
from app.services.rag.engine import rag_engine
from app.core.config import settings

# =============================================================================
# 配置
# =============================================================================

STORAGE_ROOT = os.getenv("SPINE_STORAGE_ROOT", str(BACKEND_ROOT / "storage"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 MCP 服务器
mcp = FastMCP(
    name="阅脊 (SpineDoc-OpenSource)",
    json_response=True
)

# 全局缓存
_document_cache: Dict[str, Any] = {}


# =============================================================================
# 数据模型
# =============================================================================

class SpineNodeOutput(BaseModel):
    """目录节点输出模型"""
    id: str = Field(description="节点唯一标识符")
    title: str = Field(description="章节/条款标题")
    level: int = Field(description="层级深度")
    page_range: List[int] = Field(description="页码物理范围 [起始页，结束页]")


class ParseDocumentResult(BaseModel):
    """解析结果模型"""
    success: bool = Field(description="是否解析成功")
    document_id: Optional[str] = Field(default=None, description="文档 ID")
    total_pages: int = Field(description="总页数")
    toc_tree: List[SpineNodeOutput] = Field(description="目录树结构")
    naive_tokens: int = Field(description="预估全量扫描 Token 消耗")
    message: str = Field(description="状态消息")


class FastTrackResult(BaseModel):
    """一键加速分析结果"""
    success: bool = Field(description="是否成功")
    document_id: str = Field(description="文档 ID")
    toc_tree: List[SpineNodeOutput] = Field(description="提取的完整文档逻辑脊梁 (TOC)")
    initial_content: str = Field(description="开篇前 3 页的物理原文采样内容")
    total_pages: int = Field(description="文档总页数")
    message: str = Field(description="AI 预判摘要")


class FetchSliceResult(BaseModel):
    """章节提取结果"""
    success: bool = Field(description="是否成功")
    content: str = Field(description="提取的原文内容")
    page_numbers: List[int] = Field(description="涉及的页码")
    chapter_title: str = Field(description="所属章节标题")
    char_count: int = Field(description="字符数")
    warning: Optional[str] = Field(default=None, description="警告信息")


class SearchByTocResult(BaseModel):
    """检索结果"""
    success: bool = Field(description="是否成功")
    answer: str = Field(description="检索摘要统计")
    relevant_chapters: List[Dict[str, Any]] = Field(description="命中的章节统计")
    source_chunks: List[Dict[str, Any]] = Field(description="原文片段")
    warning: Optional[str] = Field(default=None, description="警告信息")


class SpineChatResult(BaseModel):
    """对话结果"""
    success: bool = Field(description="是否成功")
    answer: str = Field(description="最终回答")
    status_history: List[str] = Field(description="分析过程状态记录")


# =============================================================================
# MCP 工具 - 开源版本（5 个核心工具）
# =============================================================================

@mcp.tool()
async def parse_document_spine(
    file_path: str,
    ctx: Context[ServerSession, None]
) -> ParseDocumentResult:
    """
    解析 PDF 并提取逻辑目录树 (脊梁)。
    
    支持:
    - 原生 PDF 元数据提取
    - 文本层目录嗅探
    - Body-Scan 锚点扫描
    """
    await ctx.info(f"开始提取逻辑脊梁：{file_path}")

    try:
        if not os.path.exists(file_path):
            return ParseDocumentResult(
                success=False, total_pages=0, toc_tree=[], 
                naive_tokens=0, message="文件不存在"
            )

        # 提取 TOC
        raw_toc = hybrid_parser.extract_toc(file_path)

        # 获取页数
        import fitz
        with fitz.open(file_path) as pdf:
            total_pages = len(pdf)
            naive_tokens = total_pages * 800

        if not raw_toc:
            return ParseDocumentResult(
                success=False, total_pages=total_pages, toc_tree=[],
                naive_tokens=naive_tokens, message="无法提取目录"
            )

        # 处理扫描件
        if raw_toc[0].get('id') == "SCANNED_PDF_DETECTED":
            return ParseDocumentResult(
                success=False, total_pages=total_pages, toc_tree=[],
                naive_tokens=naive_tokens,
                message="检测到扫描件 PDF（需要企业版 OCR 支持）"
            )

        # 构建 TOC 树
        toc_tree = []
        for item in raw_toc:
            node = SpineNodeOutput(
                id=item.get('id', f"node_{len(toc_tree)}"),
                title=item.get('title', '未命名章节'),
                level=item.get('level', 1),
                page_range=[item.get('page', 1), item.get('page', 1) + 5]
            )
            toc_tree.append(node)

        document_id = f"doc_{Path(file_path).stem}"
        _document_cache[document_id] = {
            "file_path": file_path,
            "toc_tree": toc_tree,
            "total_pages": total_pages
        }

        return ParseDocumentResult(
            success=True, document_id=document_id, total_pages=total_pages,
            toc_tree=toc_tree, naive_tokens=naive_tokens, message="解析成功"
        )
    except Exception as e:
        return ParseDocumentResult(
            success=False, total_pages=0, toc_tree=[],
            naive_tokens=0, message=str(e)
        )


@mcp.tool()
async def fast_track_analyze(
    file_path: str,
    ctx: Context[ServerSession, None]
) -> FastTrackResult:
    """
    长文档一键极速分析引擎。
    
    流程:
    1. 提取 TOC 脊梁
    2. 抓取前 3 页原文采样
    3. 返回结构化分析结果
    """
    await ctx.info(f"🚀 阅脊引擎启动分析：{file_path}")

    # 1. 提取脊梁
    parse_res = await parse_document_spine(file_path, ctx)
    if not parse_res.success:
        return FastTrackResult(
            success=False, document_id="", toc_tree=[],
            initial_content="", total_pages=0, message=parse_res.message
        )

    doc_id = parse_res.document_id

    # 2. 抓取前 3 页采样
    await ctx.info("正在进行开篇采样...")
    import fitz
    initial_text = []
    with fitz.open(file_path) as pdf:
        for i in range(min(3, len(pdf))):
            text = pdf[i].get_text("text")
            if text.strip():
                initial_text.append(f"--- 第 {i+1} 页原文 ---\n{text}")

    combined_content = "\n\n".join(initial_text) if initial_text else "文档为纯图片或无法提取文字。"

    return FastTrackResult(
        success=True,
        document_id=doc_id,
        toc_tree=parse_res.toc_tree,
        initial_content=combined_content,
        total_pages=parse_res.total_pages,
        message=f"已成功建立逻辑索引。首屏包含 {len(initial_text)} 页采样内容。"
    )


@mcp.tool()
async def fetch_secure_physical_slice(
    document_id: str,
    node_id: str,
    ctx: Context[ServerSession, None]
) -> FetchSliceResult:
    """
    精确提取该章节的物理原文。
    """
    doc_info = _document_cache.get(document_id)
    if not doc_info:
        return FetchSliceResult(
            success=False, content="", page_numbers=[],
            chapter_title="", char_count=0, warning="文档未找到"
        )

    target_node = next((n for n in doc_info["toc_tree"] if n.id == node_id), None)
    if not target_node:
        return FetchSliceResult(
            success=False, content="", page_numbers=[],
            chapter_title="", char_count=0, warning="节点未找到"
        )

    import fitz
    start_page = target_node.page_range[0] - 1
    end_page = min(target_node.page_range[1], doc_info["total_pages"])
    extracted_text, page_numbers = [], []

    with fitz.open(doc_info["file_path"]) as pdf:
        for p_idx in range(start_page, end_page):
            if p_idx < len(pdf):
                text = pdf[p_idx].get_text("text")
                if text.strip():
                    extracted_text.append(f"--- Page {p_idx + 1} ---\n{text}")
                    page_numbers.append(p_idx + 1)

    full_content = "\n\n".join(extracted_text)
    return FetchSliceResult(
        success=True, content=full_content, page_numbers=page_numbers,
        chapter_title=target_node.title, char_count=len(full_content)
    )


@mcp.tool()
async def search_by_toc(
    document_id: str,
    query: str,
    ctx: Context[ServerSession, None]
) -> SearchByTocResult:
    """
    逻辑感知的级联检索。
    返回的每个片段都包含其在文档'脊柱'中的完整路径。
    """
    await ctx.info(f"🔎 执行逻辑感知检索：{query}")
    
    try:
        from app.core.db import get_async_sessionmaker
        from sqlalchemy import select
        from app.core.models import Document
        from uuid import UUID

        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            # 转换文档 ID
            real_doc_id = None
            if document_id.startswith("doc_"):
                doc_name = document_id.replace("doc_", "")
                res = await session.execute(
                    select(Document).where(Document.filename.like(f"%{doc_name}%"))
                )
                doc_obj = res.scalars().first()
                if doc_obj:
                    real_doc_id = doc_obj.id
            else:
                try:
                    real_doc_id = UUID(document_id)
                except:
                    pass

            if not real_doc_id:
                return SearchByTocResult(
                    success=False, answer="", relevant_chapters=[],
                    source_chunks=[], warning="Invalid ID"
                )

            # 调用 RAG 引擎
            search_res = await rag_engine.search(query, real_doc_id, limit=6, session=session)
            chunks = search_res.get("chunks", [])
            toc_analysis = search_res.get("toc_analysis", {})

            relevant_chapters = [
                {"id": tid, "title": info['title'], "hits": info['count']}
                for tid, info in sorted(toc_analysis.items(), key=lambda x: x[1]['count'], reverse=True)
            ]

            summary = f"检索完成。已通过脊柱路由锁定 {len(relevant_chapters)} 个章节。"
            return SearchByTocResult(
                success=True, answer=summary, relevant_chapters=relevant_chapters,
                source_chunks=chunks
            )
    except Exception as e:
        return SearchByTocResult(
            success=False, answer="", relevant_chapters=[],
            source_chunks=[], warning=f"检索引擎异常：{str(e)}"
        )


@mcp.tool()
async def spine_chat(
    document_id: str,
    query: str,
    ctx: Context[ServerSession, None]
) -> SpineChatResult:
    """
    端到端文档对话。
    执行：脊柱路由 → 双径召回 → 重排序 → 导航链注入 → 深度生成。
    """
    await ctx.info(f"🧠 启动端到端逻辑对话模式：{query}")
    
    try:
        from app.core.db import get_async_sessionmaker
        from app.schemas.rag import RagQuery
        from sqlalchemy import select
        from app.core.models import Document
        from uuid import UUID

        session_maker = get_async_sessionmaker()
        async with session_maker() as session:
            # 转换文档 ID
            real_doc_id = None
            if document_id.startswith("doc_"):
                doc_name = document_id.replace("doc_", "")
                res = await session.execute(
                    select(Document).where(Document.filename.like(f"%{doc_name}%"))
                )
                doc_obj = res.scalars().first()
                if doc_obj:
                    real_doc_id = doc_obj.id
            else:
                try:
                    real_doc_id = UUID(document_id)
                except:
                    pass

            if not real_doc_id:
                return SpineChatResult(success=False, answer="Invalid ID", status_history=[])

            # 创建查询请求
            request = RagQuery(query=query, document_id=real_doc_id, top_k=5)
            full_answer_parts = []
            status_history = []

            async for event in rag_engine.chat_stream(request, session=session):
                if event["type"] == "status":
                    status_history.append(event["content"])
                    await ctx.info(f"⚡ {event['content']}")
                elif event["type"] == "message":
                    full_answer_parts.append(event["content"])
                elif event["type"] == "error":
                    return SpineChatResult(
                        success=False, answer=event["content"], status_history=status_history
                    )

            return SpineChatResult(
                success=True,
                answer="".join(full_answer_parts),
                status_history=status_history
            )
    except Exception as e:
        return SpineChatResult(
            success=False, answer=f"对话引擎异常：{str(e)}", status_history=[]
        )


# =============================================================================
# 健康检查
# =============================================================================

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "version": "1.0.0-open",
        "edition": "Open Source",
        "tools_available": 5,
        "tools": [
            "parse_document_spine",
            "fast_track_analyze",
            "fetch_secure_physical_slice",
            "search_by_toc",
            "spine_chat"
        ],
        "storage_root": STORAGE_ROOT,
        "features": {
            "toc_extraction": True,
            "basic_rag": True,
            "document_chat": True,
            "ocr_support": False,
            "multi_doc_reasoning": False,
            "auto_labeling": False
        }
    }


# =============================================================================
# 启动入口
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8002, type=int)
    args = parser.parse_args()

    print("🚀 Spine-MCP Server (Open Source) 启动中...", file=sys.stderr)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        print(f"📡 SSE 模式启动在端口：{args.port}", file=sys.stderr)
        mcp.run(transport="streamable-http")
