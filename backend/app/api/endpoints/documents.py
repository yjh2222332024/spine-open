"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.db import get_session
from app.core.models import Document, Workspace, TocItem, ProcessingStatus
from app.api.responses import StandardResponse, DocumentTaskInfo
from app.services.document_service import document_service
from app.api.deps import get_current_workspace
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- DTOs (解耦层) ---

class TocNodeResponse(BaseModel):
    id: str
    title: str
    page: int
    level: int
    confidence: float = 1.0
    children: List['TocNodeResponse'] = []

class TocItemUpdate(BaseModel):
    id: str
    title: str
    level: int
    page: int
    children: List['TocItemUpdate'] = []

class DocumentStatusResponse(BaseModel):
    id: str
    filename: str = ""
    status: str
    processed_pages: int = 0
    total_pages: int = 0
    error_message: Optional[str] = None

# --- 核心业务接口 ---

@router.post("/upload", response_model=StandardResponse[DocumentTaskInfo], status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks, # 注入 FastAPI 背景任务
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-01】上传并启动 AI (工业级全双工实现)"""
    if not file.filename.endswith(".pdf"):
        return StandardResponse.error("仅支持 PDF 文件", code=400)
    
    try:
        # 调用 Service 层：物理存盘 + DB 事务 + (BackgroundTasks 或 Celery) 触发
        new_doc, task_id = await document_service.create_and_trigger_processing(
            file, current_workspace.id, session, background_tasks
        )
        return StandardResponse.success(data=DocumentTaskInfo(
            document_id=str(new_doc.id),
            task_id=task_id or "OFFLINE",
            status=new_doc.status,
            message="文件已入库，AI 解析引擎已在后台启动"
        ))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return StandardResponse.error(f"处理失败: {str(e)}", code=500)

@router.get("/", response_model=StandardResponse[List[DocumentStatusResponse]])
async def list_documents(
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-00】获取当前工作区的文档列表 (动态化支持)"""
    statement = select(Document).where(Document.workspace_id == current_workspace.id).order_by(Document.created_at.desc())
    result = await session.execute(statement)
    docs = result.scalars().all()
    
    return StandardResponse.success(data=[
        DocumentStatusResponse(
            id=str(doc.id),
            filename=doc.filename,
            status=doc.status.value,
            processed_pages=doc.processed_pages,
            total_pages=doc.total_pages
        )
        for doc in docs
    ])

@router.get("/{document_id}/content/{page_num}", response_model=StandardResponse[Dict[str, Any]])
async def get_page_content(
    document_id: UUID,
    page_num: int,
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-08】获取指定页面的 Markdown 结构化内容 (两栏阅读真实对接)"""
    doc = await session.get(Document, document_id)
    if not doc or doc.workspace_id != current_workspace.id:
        return StandardResponse.error("文档未找到", code=404)
    
    # 架构逻辑：从 Chunk 表中聚合该页的所有文本
    # 考虑到 1200 页的高并发压力，我们通过 page_number 进行索引过滤
    from app.core.models import Chunk
    statement = select(Chunk).where(
        Chunk.document_id == document_id, 
        Chunk.page_number == page_num
    ).order_by(Chunk.id) # 默认按物理插入顺序拼接
    
    result = await session.execute(statement)
    chunks = result.scalars().all()

    if not chunks:
        # 架构师动态兜底：物理级路径加固 (Windows 兼容)
        try:
            from pathlib import Path
            # 计算 backend 根目录
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            # 如果存的是相对路径 storage/...
            rel_path = doc.file_path.replace("\\", "/")
            if rel_path.startswith("./"): rel_path = rel_path[2:]
            
            abs_file_path = base_dir / rel_path
            
            logger.info(f"🔍 [Path Fix] Attempting to read: {abs_file_path}")
            
            if abs_file_path.exists():
                with fitz.open(str(abs_file_path)) as pdf:
                    idx = max(0, min(page_num - 1, len(pdf) - 1))
                    real_text = pdf[idx].get_text("text").strip()
                    if real_text:
                        return StandardResponse.success(data={
                            "document_id": str(document_id),
                            "page_num": page_num,
                            "markdown": f"[SpineDoc Engine | 实时流式读取]\n\n{real_text}",
                            "confidence": 0.85
                        })
            else:
                logger.error(f"❌ File not found at: {abs_file_path}")
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")

        # 如果连物理提取都失败了，再返回提示
        if doc.status == ProcessingStatus.PROCESSING:
            msg = "AI 引擎正在奋力解析本页，请稍候刷新..."
        else:
            msg = "本页暂无解析内容（可能是空白页或扫描质量过低）。"
        return StandardResponse.success(data={
            "document_id": str(document_id),
            "page_num": page_num,
            "markdown": f"> **提示**: {msg}",
            "confidence": 1.0
        })
    
    # 聚合 Markdown
    full_markdown = "\n\n".join([c.content for c in chunks])
    
    # 获取该页关联的目录项置信度 (如果有)
    statement_toc = select(TocItem).where(
        TocItem.document_id == document_id,
        TocItem.page == page_num
    )
    res_toc = await session.execute(statement_toc)
    toc_item = res_toc.scalars().first()
    confidence = toc_item.confidence if toc_item else 0.95 # 默认高置信度

    return StandardResponse.success(data={
        "document_id": str(document_id),
        "page_num": page_num,
        "markdown": full_markdown,
        "confidence": confidence
    })

@router.get("/{document_id}", response_model=StandardResponse[DocumentStatusResponse])
async def get_document_status(
    document_id: UUID, 
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-02】轮询文档状态"""
    doc = await session.get(Document, document_id)
    if not doc or doc.workspace_id != current_workspace.id:
        return StandardResponse.error("文档未找到", code=404)
    
    return StandardResponse.success(data=DocumentStatusResponse(
        id=str(doc.id),
        filename=doc.filename,
        status=doc.status.value,
        processed_pages=doc.processed_pages,
        total_pages=doc.total_pages,
        error_message=doc.error_message
    ))

@router.get("/{document_id}/toc", response_model=StandardResponse[List[TocNodeResponse]])
async def get_document_toc(
    document_id: UUID, 
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-03】拉取嵌套目录树 (后端递归组树)"""
    doc = await session.get(Document, document_id)
    if not doc or doc.workspace_id != current_workspace.id:
        return StandardResponse.error("文档未找到", code=404)

    statement = select(TocItem).where(TocItem.document_id == document_id).order_by(TocItem.page, TocItem.id)
    result = await session.exec(statement)
    items = result.scalars().all()

    # 递归组树逻辑 (使用从 ORM 模型中提取的数据)
    item_map: Dict[str, TocNodeResponse] = {
        str(item.id): TocNodeResponse(
            id=str(item.id),
            title=item.title,
            page=item.page,
            level=item.level,
            confidence=item.confidence,
            children=[]
        )
        for item in items
    }
    
    tree: List[TocNodeResponse] = []
    for item in items:
        node = item_map[str(item.id)]
        if item.parent_id and str(item.parent_id) in item_map:
            item_map[str(item.parent_id)].children.append(node)
        elif item.level == 1:
            tree.append(node)
            
    return StandardResponse.success(data=tree)

@router.put("/{document_id}/toc")
async def update_document_toc(
    document_id: UUID,
    payload: List[TocItemUpdate],
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-04】真实落库：接收前端修改并更新数据库"""
    await session.execute(delete(TocItem).where(TocItem.document_id == document_id))
    
    def flatten(nodes, parent_id=None):
        out = []
        for n in nodes:
            uid = UUID(n.id) if len(n.id) == 36 else uuid4()
            db_item = TocItem(id=uid, title=n.title, page=n.page, level=n.level, confidence=1.0, document_id=document_id, parent_id=parent_id)
            out.append(db_item)
            if n.children: out.extend(flatten(n.children, uid))
        return out

    session.add_all(flatten(payload))
    await session.commit()
    return StandardResponse.success(data={"status": "updated"})

@router.post("/{document_id}/toc/lock")
async def lock_document_toc(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """【API-05】锁定目录结构：固化当前 TOC 并标志文档处理完成"""
    doc = await session.get(Document, document_id)
    if not doc or doc.workspace_id != current_workspace.id:
        return StandardResponse.error("文档未找到", code=404)
    
    # 架构逻辑：锁定后，文档进入可问答状态 (COMPLETED)
    doc.status = ProcessingStatus.COMPLETED
    doc.is_toc_locked = True # 核心：激活目录锁
    doc.updated_at = datetime.utcnow()
    session.add(doc)
    await session.commit()
    
    return StandardResponse.success(data={
        "status": "locked", 
        "document_id": str(document_id),
        "final_status": doc.status
    })

from fastapi import Response
import fitz

@router.get("/{document_id}/preview/{page_num}")
async def get_document_page_preview(
    document_id: UUID,
    page_num: int,
    session: AsyncSession = Depends(get_session)
):
    """【API-07】获取文档单页预览图 (加固版)"""
    doc_record = await session.get(Document, document_id)
    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 路径规范化处理 (Windows Path Safety)
    abs_path = os.path.abspath(doc_record.file_path)
    if not os.path.exists(abs_path):
        logger.error(f"File not found on disk: {abs_path}")
        raise HTTPException(status_code=404, detail="File missing on disk")

    try:
        # 使用 context manager 确保句柄释放
        with fitz.open(abs_path) as pdf:
            idx = max(0, min(page_num - 1, len(pdf) - 1))
            page = pdf[idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_bytes = pix.tobytes("png")
            return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Render engine error: {e}")
        raise HTTPException(status_code=500, detail=f"渲染失败: {str(e)}")
