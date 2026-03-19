import asyncio
from sqlmodel import select, SQLModel
from app.core.models import Document, ProcessingStatus, Chunk
from app.core.db import async_session_maker, engine, init_db
from app.services.pipeline import process_document_pipeline
from uuid import uuid4
import os
import shutil

# 模拟一个 PDF 文件路径 (我们需要一个真实的 PDF 文件来测试 hybrid_parser)
# 为了测试，我们创建一个极简的 dummy PDF 或 mock parser
# 这里选择 Mock parser 的行为，因为我们只想验证 Pipeline 逻辑，而不是真的去跑 OCR
from unittest.mock import MagicMock
from app.services.parser import hybrid_parser

# Mock hybrid_parser.extract_toc to avoid actual PDF processing dependency in this test
hybrid_parser.extract_toc = MagicMock(return_value=[
    {"title": "Chapter 1", "page": 1, "level": 1},
    {"title": "Section 1.1", "page": 1, "level": 2}
])

async def verify_pipeline():
    print("--- 验证异步流水线 (Mocked Parser) ---")
    
    # 1. 初始化 DB (Reset schema for dev)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        # Ensure pgvector extension
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    # 2. 创建一个测试 Document
    doc_id = uuid4()
    # 创建一个空的 dummy 文件用于路径检查
    test_file_path = f"test_{doc_id}.pdf"
    with open(test_file_path, "wb") as f:
        f.write(b"%PDF-1.4 header dummy content")
    
    try:
        async with async_session_maker() as session:
            doc = Document(
                id=doc_id,
                filename="test_pipeline.pdf",
                file_path=test_file_path,
                status=ProcessingStatus.PENDING
            )
            session.add(doc)
            await session.commit()
            print(f"[Setup] 文档已创建, Status: {doc.status}")

        # 3. 手动触发 Pipeline (不通过 API，直接调函数)
        print("[Action] 触发 process_document_pipeline...")
        await process_document_pipeline(doc_id)
        
        # 4. 验证结果
        async with async_session_maker() as session:
            # 重新获取文档
            result = await session.execute(select(Document).where(Document.id == doc_id))
            updated_doc = result.scalar_one()
            
            print(f"[Check] 文档状态: {updated_doc.status}")
            
            if updated_doc.status == ProcessingStatus.COMPLETED:
                print("[PASS] 状态流转正确")
            else:
                print(f"[FAIL] 状态错误: {updated_doc.status} (Error: {updated_doc.error_message})")
                
            # 验证 Chunks
            chunks_res = await session.execute(select(Chunk).where(Chunk.document_id == doc_id))
            chunks = chunks_res.scalars().all()
            print(f"[Check] 生成 Chunks 数量: {len(chunks)}")
            
            if len(chunks) == 2:
                print("[PASS] Chunk 数量正确")
            else:
                print(f"[FAIL] Chunk 数量预期 2, 实际 {len(chunks)}")

    finally:
        # 清理
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    # Windows 下 asyncio SelectorEventLoop 可能会有警告，忽略
    asyncio.run(verify_pipeline())
