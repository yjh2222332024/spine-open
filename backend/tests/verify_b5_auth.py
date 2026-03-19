import asyncio
from sqlmodel import select, SQLModel
from app.core.models import User, Workspace, Document, Folder
from app.core.db import async_session_maker, engine
from app.core.config import settings
from uuid import uuid4
from sqlalchemy import text
from app.api.deps import get_current_user, get_current_workspace

# Mock Depends behaviour manually since we are not running a full FastAPI app here
async def verify_auth_deps():
    print("--- 验证 Dev Mode Auth Dependencies ---")
    
    # 1. Reset DB
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    async with async_session_maker() as session:
        # 2. Call get_current_user directly
        print("[Action] Calling get_current_user...")
        user = await get_current_user(session)
        print(f"[Result] User ID: {user.id}, Username: {user.username}")
        
        if user.id == settings.DEV_USER_ID:
            print("[PASS] 返回了预期的 Dev User")
        else:
            print(f"[FAIL] User ID 不匹配: {user.id}")

        # 3. Call get_current_workspace directly
        print("[Action] Calling get_current_workspace...")
        ws = await get_current_workspace(user, session)
        print(f"[Result] Workspace ID: {ws.id}, Name: {ws.name}, Owner: {ws.owner_id}")
        
        if ws.id == settings.DEV_WORKSPACE_ID and ws.owner_id == user.id:
            print("[PASS] 返回了预期的 Dev Workspace 且 Owner 正确")
        else:
            print(f"[FAIL] Workspace 校验失败")

        # 4. Verify DB persistence
        db_user = await session.get(User, settings.DEV_USER_ID)
        if db_user:
            print("[PASS] Dev User 已持久化到数据库")
        else:
            print("[FAIL] Dev User 未找到")

if __name__ == "__main__":
    asyncio.run(verify_auth_deps())
