"""
SpineDoc Data Engine: Document Ingestor
=======================================
把 ceshi 文件夹里的原始 PDF 喂进系统，生成结构化底座。
"""
import asyncio
import sys
import os
import shutil
from uuid import UUID, uuid4
from sqlalchemy.future import select

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, ProcessingStatus, Workspace, User
from app.services.ai_pipeline import run_document_analysis_workflow
from app.core.config import settings

async def ingest_and_process(file_path: str):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 获取默认 Workspace (如果没有，创建一个)
        ws_id = settings.DEV_WORKSPACE_ID
        ws = await session.get(Workspace, ws_id)
        if not ws:
            # Create dummy user and workspace
            user = User(id=settings.DEV_USER_ID, username="admin", hashed_password="xxx")
            session.add(user)
            ws = Workspace(id=ws_id, name="Default Workspace", owner_id=user.id)
            session.add(ws)
            await session.commit()

        # 2. 检查文档是否已存在
        filename = os.path.basename(file_path)
        stmt = select(Document).where(Document.filename == filename)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc:
            print(f"📄 Document already exists in DB: {doc.id}")
            if doc.status == ProcessingStatus.COMPLETED:
                print("✅ Already processed. Skipping ingestion.")
                return doc.id
        else:
            # 3. 复制文件到存储目录并入库
            doc_id = uuid4()
            target_path = os.path.join(settings.STORAGE_ROOT, "workspaces", str(ws_id), f"{doc_id}.pdf")
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy(file_path, target_path)
            
            doc = Document(
                id=doc_id,
                filename=filename,
                file_path=f"workspaces/{ws_id}/{doc_id}.pdf",
                workspace_id=ws_id,
                status=ProcessingStatus.PENDING
            )
            session.add(doc)
            await session.commit()
            print(f"📥 Document ingested: {doc.id}")

        # 4. 触发分析流水线 (ISR 过程)
        print(f"🚀 Starting ISR Analysis for: {filename}...")
        await run_document_analysis_workflow(str(doc.id))
        return doc.id

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/ingest_test_doc.py <pdf_path>")
        sys.exit(1)
    
    asyncio.run(ingest_and_process(sys.argv[1]))
