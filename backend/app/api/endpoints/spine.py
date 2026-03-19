"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import delete
from uuid import UUID, uuid4
from typing import List
from app.api.responses import StandardResponse
from app.core.db import get_session
from app.core.models import TocItem

router = APIRouter()

@router.post("/parse-toc")
async def parse_toc_manual(payload: dict):
    """
    【MVP 演示用存根】：模拟手动触发框选区域的 TOC 解析
    """
    return StandardResponse.success(data={
        "items": [
            {"title": "解析后的层级 A", "level": 1, "original_page": 1, "physical_page": 1, "confidence": 0.95}
        ]
    })

@router.post("/align")
async def align_toc_pages(payload: dict):
    """模拟页码对齐算法：直接返回 items"""
    items = payload.get("items", [])
    return StandardResponse.success(data={"items": items})

@router.post("/apply")
async def apply_toc_changes(
    payload: dict,
    session: AsyncSession = Depends(get_session)
):
    """【API-06】递归持久化树形目录结构 (全量重置)"""
    doc_id_str = payload.get("document_id")
    items_data = payload.get("items", [])
    if not doc_id_str:
        return StandardResponse.error("Missing document_id", code=400)
    
    doc_id = UUID(doc_id_str)
    
    # 1. 物理清空旧目录 (级联删除会自动处理 children，但此处我们全量重刷)
    await session.execute(delete(TocItem).where(TocItem.document_id == doc_id))
    
    # 2. 递归插入逻辑
    async def save_recursive(nodes: List[dict], parent_id: UUID = None):
        for node in nodes:
            new_id = uuid4()
            # 兼容前端字段名
            page = node.get("page") or node.get("physical_page") or 1
            
            db_item = TocItem(
                id=new_id,
                title=node.get("title", "Untitled"),
                page=page,
                level=node.get("level", 1),
                confidence=node.get("confidence", 1.0),
                document_id=doc_id,
                parent_id=parent_id
            )
            session.add(db_item)
            
            # 处理子节点
            children = node.get("children", [])
            if children:
                await save_recursive(children, new_id)

    try:
        await save_recursive(items_data)
        await session.commit()
        return StandardResponse.success(data={"status": "sync_complete", "document_id": str(doc_id)})
    except Exception as e:
        await session.rollback()
        return StandardResponse.error(f"Save failed: {str(e)}", code=500)
