"""
SpineDoc Data Engine: Export CLI
================================
一键从数据库提取结构化解析成果，并转化为 4060 可训练的 SFT 数据集。

Usage:
    python backend/scripts/export_training_data.py --doc_id <UUID> --output data.jsonl

Author: Yan Junhao (严俊皓)
"""

import asyncio
import argparse
import sys
import os
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk
from app.services.train.dataset_generator import DatasetGenerator

async def export_document_to_sft(doc_id: str, output_path: str):
    """
    核心导出逻辑：
    1. 获取文档及其所有目录项
    2. 获取所有文本块
    3. 调用 Generator 生成训练对
    """
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 预加载 TocItems 和对应的 Chunks (SQLAlchemy 2.0 风格)
        stmt = (
            select(Document)
            .options(selectinload(Document.toc_items).selectinload(TocItem.children))
            .where(Document.id == UUID(doc_id))
        )
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            print(f"❌ Error: Document {doc_id} not found.")
            return

        print(f"📂 Found Document: {doc.filename}")
        print(f"🌲 Processing {len(doc.toc_items)} TOC items...")

        # 2. 构建符合 Generator 要求的临时 Atlas 结构
        # 这里我们将数据库模型转化为 Generator 需要的 Dict 列表
        nodes = []
        for item in doc.toc_items:
            # 聚合该 TocItem 下的所有物理 Chunk 文本
            chunk_stmt = select(Chunk).where(Chunk.toc_item_id == item.id)
            chunk_res = await session.execute(chunk_stmt)
            chunks = chunk_res.scalars().all()
            content = "\n".join([c.content for c in chunks])

            nodes.append({
                "toc_id": str(item.id),
                "title": item.title,
                "level": item.level,
                "summary": item.summary or "",
                "content": content,
                "atlas_level": 0, # 基础层
                "full_path": item.title # 后续可以递归重建完整路径
            })

        # 3. 运行生成引擎
        from unittest.mock import MagicMock
        mock_atlas = MagicMock()
        mock_atlas.get_flattened_atlas.return_value = nodes
        
        generator = DatasetGenerator(mock_atlas)
        generator.generate_from_atlas()
        
        # 4. 导出
        generator.export_to_jsonl(output_path)
        print(f"🚀 Success! Dataset saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export SpineDoc structured data for LLM training.")
    parser.add_argument("--doc_id", required=True, help="UUID of the document")
    parser.add_argument("--output", default="training_dataset.jsonl", help="Output JSONL file path")
    
    args = parser.parse_args()
    asyncio.run(export_document_to_sft(args.doc_id, args.output))
