"""
SpineDoc Data Factory: Quality Diagnoser
========================================
诊断数据库中特定文档的数据质量：TOC 是否有对应的 Chunk 内容。
"""
import asyncio
import sys
import os
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy import func

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk

async def diagnose(doc_id: str):
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 检查文档状态
        doc = await session.get(Document, UUID(doc_id))
        if not doc:
            print(f"❌ Document {doc_id} not found.")
            return
        print(f"📄 Document: {doc.filename} | Status: {doc.status}")

        # 2. 统计 TOC 数量
        tocs = await session.execute(select(TocItem).where(TocItem.document_id == doc.id))
        toc_list = tocs.scalars().all()
        print(f"🌲 Total TOC Nodes: {len(toc_list)}")

        # 3. 统计 Chunk 数量
        chunks = await session.execute(select(Chunk).where(Chunk.document_id == doc.id))
        chunk_list = chunks.scalars().all()
        print(f"📦 Total Physical Chunks: {len(chunk_list)}")

        # 4. 检查关联度
        linked_chunks = [c for c in chunk_list if c.toc_item_id is not None]
        print(f"🔗 Linked Chunks (with TOC): {len(linked_chunks)}")

        # 5. 详细查看第一个有内容的 TOC
        for item in toc_list:
            item_chunks = [c for c in chunk_list if c.toc_item_id == item.id]
            if item_chunks:
                print(f"\n✅ Found Quality Node: '{item.title}'")
                print(f"   - Level: {item.level}")
                print(f"   - Content Length: {sum(len(c.content) for c in item_chunks)} chars")
                return

        print("\n⚠️ Warning: No TOC items are currently linked to any physical content.")
        print("💡 Suggestion: The ISR pipeline may have extracted the spine but failed the 'Spine-Align' step.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/diagnose_data_quality.py <doc_id>")
    else:
        asyncio.run(diagnose(sys.argv[1]))
