"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
import json
import logging
from app.core.db import get_session
from app.core.models import Document
from app.schemas.rag import RagQuery
from app.services.rag.engine import rag_engine

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query")
async def rag_query(payload: dict, session: AsyncSession = Depends(get_session)):
    """
    🚀 [SAP-8.0] 全面集成的 SCR 级联检索接口：
    1. 协议映射：将原生 JSON 映射为 RagQuery Schema。
    2. 逻辑委派：调用 RAGEngine 的增强型生成流。
    3. SSE 转发：实时下发状态与回答内容。
    """
    doc_id = payload.get("document_id")
    query_text = payload.get("query", "")
    top_k = payload.get("top_k", 5)
    
    if not doc_id or not query_text:
        raise HTTPException(status_code=400, detail="Missing document_id or query")

    try:
        # 验证文档是否存在
        doc_uuid = UUID(doc_id)
        doc = await session.get(Document, doc_uuid)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # 构建规范化的 Query 对象
        request = RagQuery(
            query=query_text,
            document_id=doc_uuid,
            top_k=top_k,
            thinking_budget=payload.get("thinking_budget", "balanced")
        )

        async def sse_adapter():
            # 调用底层 RAG 逻辑引擎
            async for event in rag_engine.chat_stream(request, session=session):
                # 转发引擎产生的每一条结构化消息
                yield f"data: {json.dumps(event)}\n\n"
            
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse_adapter(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"API Error: {e}")
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': f'系统异常: {str(e)}'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

@router.post("/synthesis")
async def rag_synthesis(payload: dict):
    """
    跨文档综合分析接口 (待 RAGEngine 进一步扩展实现)
    """
    async def event_generator():
        yield f"data: {json.dumps({'type': 'message', 'content': '跨文档多维矩阵分析功能正在集成中，敬请期待...'})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
