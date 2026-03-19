import asyncio
import os
from uuid import uuid4
from datetime import datetime
from app.core.models import Document, ProcessingStatus, TocItem, Workspace, User
from app.core.db import AsyncSessionLocal
from app.tasks.process_document import process_document
from sqlmodel import select

async def verify_real_ai_flow():
    """
    【真实 AI 验证】：Member A (LangGraph) -> Member B (Database)
    """
    # 0. 环境注入 (5433 专属库)
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:password@127.0.0.1:5433/structurag"
    
    print("\n[Step 1] Initializing Backend Data...")
    async with AsyncSessionLocal() as session:
        # 创建一个测试用户和空间 (如果不存在)
        user_id = uuid4()
        user = User(id=user_id, username=f"ai_verify_{user_id.hex[:4]}", hashed_password="pw", is_active=True, created_at=datetime.now())
        session.add(user)
        
        workspace_id = uuid4()
        ws = Workspace(id=workspace_id, name="AI Lab", owner_id=user_id, created_at=datetime.now())
        session.add(ws)
        
        # 挑选现有的 PDF 文件
        sample_pdf = "backend/temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf"
        
        doc_id = uuid4()
        new_doc = Document(
            id=doc_id,
            filename="real_analysis_test.pdf",
            file_path=sample_pdf,
            status=ProcessingStatus.PENDING,
            workspace_id=workspace_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(new_doc)
        await session.commit()
        print(f"Document {doc_id} created for analysis.")

    print("\n[Step 2] Awakening Member A's AI Engine...")
    print("--- Note: This involves LLM and Vision processing. Please wait... ---")
    
    # 我们直接通过 Member B 的 Celery 任务入口启动 (不走队列，本地同步执行)
    # process_document 本身是一个同步函数，它内部会启动异步循环
    process_document(str(doc_id))

    print("\n[Step 3] Checking AI Persistence Results...")
    async with AsyncSessionLocal() as session:
        # 验证状态
        db_doc = await session.get(Document, doc_id)
        print(f"Final Status: {db_doc.status}")
        
        if db_doc.status == ProcessingStatus.FAILED:
            print(f"ERROR: AI Pipeline failed with message: {db_doc.error_message}")
            return

        # 验证解析出的 TOC
        statement = select(TocItem).where(TocItem.document_id == doc_id).order_by(TocItem.page)
        result = await session.exec(statement)
        items = result.all()
        
        print(f"\n--- Member A's Real AI Output (Stored by Member B) ---")
        if not items:
            print("No TOC items found. (AI may have returned empty list)")
        else:
            for item in items:
                indent = "  " * (item.level - 1)
                print(f"{indent}• {item.title} (Page {item.page}, Confidence: {item.confidence:.2f})")
        
        print(f"\n[SUMMARY] Successfully processed and stored {len(items)} AI-generated structure items.")

if __name__ == "__main__":
    asyncio.run(verify_real_ai_flow())
