import asyncio
from sqlmodel import select, SQLModel
from app.core.models import User, Workspace, Document
from app.core.db import async_session_maker, engine
from app.services.storage import storage_service
from app.api.deps import get_current_user, get_current_workspace
from app.core.config import settings
from sqlalchemy import text
from uuid import uuid4
import os
import shutil

# Mocking FastAPI UploadFile
class MockUploadFile:
    def __init__(self, content: bytes):
        self.content = content
        self.filename = "chunk.part"
    
    async def read(self, size=-1):
        return self.content
    
    async def seek(self, offset):
        pass

async def verify_chunked_upload():
    print("--- 验证分块上传机制 ---")
    
    # 1. Reset DB
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
    async with async_session_maker() as session:
        # Prepare Dev User
        user = await get_current_user(session)
        workspace = await get_current_workspace(user, session)
        
        # 2. Simulate File Split
        original_content = b"0123456789" * 100 # 1000 bytes
        chunk_size = 200
        chunks = [original_content[i:i+chunk_size] for i in range(0, len(original_content), chunk_size)]
        total_chunks = len(chunks)
        print(f"[Setup] Total Chunks: {total_chunks}")
        
        # 3. Init Session
        filename = "chunked_test.pdf"
        upload_id = await storage_service.create_upload_session(filename, total_chunks, workspace.id)
        print(f"[Step 1] Init Session ID: {upload_id}")
        
        # 4. Upload Chunks (Out of order test: 0, 1, 3, 4 then 2)
        indices = [0, 1, 3, 4]
        for idx in indices:
            await storage_service.save_chunk(upload_id, idx, chunks[idx])
            print(f"  Uploaded chunk {idx}")
            
        # 5. Check Status
        status = storage_service.get_session_status(upload_id)
        print(f"[Step 2] Status: {status['received_chunks']}")
        if status['received_chunks'] == [0, 1, 3, 4]:
            print("[PASS] 状态查询正确")
        else:
            print("[FAIL] 状态查询错误")
            
        # Upload missing chunk
        await storage_service.save_chunk(upload_id, 2, chunks[2])
        print("  Uploaded chunk 2")
        
        # 6. Merge (Complete)
        doc_id = uuid4()
        result = await storage_service.merge_session(upload_id, doc_id)
        print(f"[Step 3] Merge Result: {result}")
        
        # 7. Verify File Content
        with open(result['absolute_path'], 'rb') as f:
            merged_content = f.read()
            if merged_content == original_content:
                print("[PASS] 文件合并内容完全一致")
            else:
                print("[FAIL] 内容不一致")
                
        # 8. Verify DB Insert Context (Simulated)
        if result['workspace_id'] == str(workspace.id):
             print("[PASS] Workspace ID 正确传递")
        else:
             print(f"[FAIL] Workspace ID 丢失: {result.get('workspace_id')}")

if __name__ == "__main__":
    asyncio.run(verify_chunked_upload())
