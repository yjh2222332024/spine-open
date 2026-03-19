import asyncio
from sqlmodel import select, SQLModel
from app.core.models import User, Workspace, Document, Folder, ProcessingStatus
from app.core.db import async_session_maker, engine
from uuid import uuid4
import os
from sqlalchemy import text

async def verify_folders():
    print("--- 验证文件夹管理功能 ---")
    
    # 1. 重置数据库 Schema (为了确保 Folder 表存在)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    workspace_id = uuid4()
    user_id = uuid4()

    async with async_session_maker() as session:
        # 2. 准备数据: User & Workspace
        user = User(id=user_id, username="test_user", hashed_password="pw")
        session.add(user)
        ws = Workspace(id=workspace_id, name="Test Workspace", owner_id=user_id)
        session.add(ws)
        await session.commit()

        # 3. 创建文件夹层级: Root -> Sub
        folder_root = Folder(name="Root Folder", workspace_id=workspace_id)
        session.add(folder_root)
        await session.commit()
        await session.refresh(folder_root)
        print(f"[Created] Root Folder ID: {folder_root.id}")

        folder_sub = Folder(name="Sub Folder", parent_id=folder_root.id, workspace_id=workspace_id)
        session.add(folder_sub)
        await session.commit()
        await session.refresh(folder_sub)
        print(f"[Created] Sub Folder ID: {folder_sub.id}, Parent: {folder_sub.parent_id}")

        # 4. 创建文档并移动到 Sub Folder
        doc = Document(
            filename="doc_in_folder.pdf",
            file_path="/tmp/fake.pdf",
            status=ProcessingStatus.COMPLETED,
            workspace_id=workspace_id,
            folder_id=None # 初始在根目录
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        print(f"[Created] Document ID: {doc.id}, Folder: {doc.folder_id}")

        # Move to sub folder
        doc.folder_id = folder_sub.id
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        print(f"[Moved] Document Folder: {doc.folder_id}")

        if doc.folder_id == folder_sub.id:
            print("[PASS] 文档移动成功")
        else:
            print("[FAIL] 文档移动失败")

        # 5. 验证反向查询 (Folder.documents)
        # 需要重新加载 relationship，或者开启 expire_on_commit=False (已开启)
        # 但通常最好重新查一次
        reloaded_folder = await session.get(Folder, folder_sub.id)
        # 注意: async session 访问 lazy relationship 会报错，需显式加载 options(selectinload)
        # 或者直接查
        stmt = select(Document).where(Document.folder_id == folder_sub.id)
        docs_in_folder = (await session.execute(stmt)).scalars().all()
        
        print(f"[Check] Sub Folder contains {len(docs_in_folder)} documents")
        if len(docs_in_folder) == 1:
             print("[PASS] 文件夹包含文档验证成功")
        else:
             print("[FAIL] 文件夹为空")

if __name__ == "__main__":
    asyncio.run(verify_folders())
