from fastapi import Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.db import get_session
from app.core.config import settings
from app.core.models import User, Workspace
from uuid import uuid4

async def get_current_user(session: AsyncSession = Depends(get_session)) -> User:
    """
    获取当前用户依赖。
    如果开启 DEV_MODE，返回默认的开发用户。
    """
    if settings.DEV_MODE:
        # 1. 尝试获取 Dev User
        user = await session.get(User, settings.DEV_USER_ID)
        if not user:
            # 2. 如果不存在，自动创建
            user = User(
                id=settings.DEV_USER_ID,
                username="dev_admin",
                hashed_password="dev_password_hash", # Dummy hash
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user
    
    # PROD 模式下的 JWT 逻辑 (暂未实现)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (JWT not implemented yet)",
    )

async def get_current_workspace(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Workspace:
    """
    获取当前工作空间依赖。
    简化逻辑：返回用户拥有的第一个工作空间，如果没有则创建默认的 Dev Workspace。
    """
    if settings.DEV_MODE:
        # 尝试获取固定 ID 的 Workspace
        workspace = await session.get(Workspace, settings.DEV_WORKSPACE_ID)
        if not workspace:
            workspace = Workspace(
                id=settings.DEV_WORKSPACE_ID,
                name="Dev Workspace",
                owner_id=current_user.id
            )
            session.add(workspace)
            await session.commit()
            await session.refresh(workspace)
        return workspace

    # 真实逻辑可能需要从 Header 或 Query 参数中获取 workspace_id，并校验权限
    # 这里暂且返回用户的第一个 Workspace
    # await session.refresh(current_user, ["workspaces"]) # 确保加载关系
    # if not current_user.workspaces:
    #     raise HTTPException(status_code=404, detail="No workspace found")
    # return current_user.workspaces[0]
    pass
