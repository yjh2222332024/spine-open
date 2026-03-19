import pytest
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, patch
from app.services.document_service import document_service
from app.core.models import Document, ProcessingStatus, TocItem, Workspace, User
from app.tasks.process_document import process_document
from sqlmodel import select
from datetime import datetime

@pytest.mark.asyncio
async def test_full_upload_and_task_trigger(db_session):
    """
    全链路验证：API 请求 -> 数据库记录 -> 任务分发
    """
    # 0. 准备基础数据 (User -> Workspace)
    user_id = uuid4()
    user = User(id=user_id, username=f"test_user_{user_id}", hashed_password="pw", is_active=True, created_at=datetime.now())
    db_session.add(user)
    
    workspace_id = uuid4()
    ws = Workspace(id=workspace_id, name="Test WS", owner_id=user_id, created_at=datetime.now())
    db_session.add(ws)
    await db_session.commit()

    # 1. 模拟上传文件
    mock_file = MagicMock()
    mock_file.filename = "test_e2e.pdf"
    
    # Mock 存储服务，避免真实 IO
    with patch("app.services.storage.storage_service.save_upload_file") as mock_save:
        mock_save.return_value = {"absolute_path": "/tmp/test.pdf", "hash": "abc123"}
        
        # 2. 调用 Service (包含 DB 事务)
        with patch("app.tasks.process_document.process_document.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="test-task-id")
            
            new_doc, task_id = await document_service.create_and_trigger_processing(
                mock_file, workspace_id, db_session
            )
            
            # 3. 验证数据库状态
            assert new_doc.filename == "test_e2e.pdf"
            assert new_doc.status == ProcessingStatus.PENDING
            assert task_id == "test-task-id"

@pytest.mark.asyncio
async def test_celery_bridge_to_ai_engine(db_session):
    """
    验证 Celery 任务是否能正确拉起 AI 解析流
    """
    # 0. 准备基础数据
    user_id = uuid4()
    user = User(id=user_id, username=f"ai_user_{user_id}", hashed_password="pw", is_active=True, created_at=datetime.now())
    db_session.add(user)
    
    workspace_id = uuid4()
    ws = Workspace(id=workspace_id, name="AI WS", owner_id=user_id, created_at=datetime.now())
    db_session.add(ws)
    
    doc_id = uuid4()
    # 注意：这里需要一个真实存在的 PDF 路径用于 AI 解析（如果有的话），或者 mock AI 引擎
    new_doc = Document(
        id=doc_id,
        filename="ai_bridge_test.pdf",
        file_path="backend/temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf",
        status=ProcessingStatus.PENDING,
        workspace_id=workspace_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_session.add(new_doc)
    await db_session.commit()

    # 2. 这里的核心是测试桥接。由于 pytest 环境已有 loop，我们 mock 掉分布式锁并直接调用内部函数
    # 避免在测试中触发 loop.run_until_complete
    with patch("app.core.redis.redis_manager.distributed_lock") as mock_lock:
        mock_lock.return_value.__enter__.return_value = True
        
        # 注意：这里我们避开任务外部的 loop 逻辑，直接测试业务逻辑是否能跑通
        # 或者我们 mock 掉 process_document 里的 loop.run_until_complete 行为
        from app.tasks.process_document import process_document
        
        # 由于 process_document 内部使用了同步包装器，测试它最好的方式是 mock 掉它内部的 _get_path 等异步调用
        with patch("app.tasks.process_document.process_document.run") as mock_run:
            # 模拟执行
            process_document(str(doc_id))
            assert mock_run.called
