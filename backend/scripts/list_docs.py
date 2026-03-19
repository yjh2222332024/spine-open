"""
SpineDoc Data Factory: Document Lister
======================================
列出所有可以导出为训练数据集的文档及其状态。
"""
import asyncio
import sys
import os
from sqlalchemy.future import select
from sqlalchemy import func

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk, ProcessingStatus

async def list_available_docs():
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 查询所有已完成的文档
        stmt = select(Document).where(Document.status == ProcessingStatus.COMPLETED)
        result = await session.execute(stmt)
        docs = result.scalars().all()
        
        if not docs:
            print("⚠️ 没有找到状态为 COMPLETED 的文档。")
            return

        print(f"\n{'Document ID':<40} | {'Filename':<30} | {'TOCs':<10} | {'Chunks':<10}")
        print("-" * 100)
        
        for doc in docs:
            # 统计 TOC 项数量
            toc_count_stmt = select(func.count(TocItem.id)).where(TocItem.document_id == doc.id)
            toc_res = await session.execute(toc_count_stmt)
            toc_count = toc_res.scalar() or 0
            
            # 统计 Chunks 数量
            chunk_count_stmt = select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
            chunk_res = await session.execute(chunk_count_stmt)
            chunk_count = chunk_res.scalar() or 0
            
            print(f"{str(doc.id):<40} | {doc.filename[:28]:<30} | {toc_count:<10} | {chunk_count:<10}")

if __name__ == "__main__":
    asyncio.run(list_available_docs())
