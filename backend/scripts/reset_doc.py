"""
SpineDoc Data Factory: Reset Tool
=================================
彻底删除特定文档及其关联的所有 TOC 和 Chunk，以便重新进行全链路分析。
"""
import asyncio
import sys
import os
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy import delete

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk

async def reset_document(filename: str):
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 查找文档
        stmt = select(Document).where(Document.filename == filename)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            print(f"⚠️ Document {filename} not found in DB.")
            return

        print(f"🗑️ Resetting Document: {filename} ({doc.id})")
        
        # 2. 删除关联项
        await session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        await session.execute(delete(TocItem).where(TocItem.document_id == doc.id))
        await session.delete(doc)
        
        await session.commit()
        print(f"✅ Document and all related data purged.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/reset_doc.py <filename>")
    else:
        asyncio.run(reset_document(sys.argv[1]))
