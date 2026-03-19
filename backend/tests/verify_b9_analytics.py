import asyncio
from sqlmodel import select, SQLModel
from app.core.models import User, Document, EventLog, ProcessingMetric, ProcessingStatus
from app.core.db import async_session_maker, engine
from uuid import uuid4
from sqlalchemy import text

async def verify_analytics_models():
    print("--- 验证埋点模型 (Task B9) ---")
    
    # 1. Reset DB Schema
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    async with async_session_maker() as session:
        # 2. 准备基础数据
        user_id = uuid4()
        user = User(id=user_id, username="metric_tester", hashed_password="...")
        session.add(user)
        
        doc_id = uuid4()
        doc = Document(id=doc_id, filename="metrics.pdf", file_path="/tmp/m.pdf", status=ProcessingStatus.COMPLETED)
        session.add(doc)
        await session.commit()

        # 3. 测试 EventLog (JSON Payload)
        print("[Action] 记录用户行为事件...")
        event = EventLog(
            user_id=user_id,
            event_type="search",
            payload={"query": "FastAPI", "results_count": 10, "filters": ["pdf"]}
        )
        session.add(event)
        
        # 4. 测试 ProcessingMetric
        print("[Action] 记录性能指标...")
        metric = ProcessingMetric(
            document_id=doc_id,
            stage="ocr",
            duration_ms=1500,
            status="success"
        )
        session.add(metric)
        
        await session.commit()
        
        # 5. 验证查询
        print("[Check] 验证数据读取...")
        stmt_event = select(EventLog).where(EventLog.user_id == user_id)
        saved_event = (await session.execute(stmt_event)).scalar_one()
        print(f"  Event Type: {saved_event.event_type}")
        print(f"  Payload Content: {saved_event.payload['query']}")
        
        if saved_event.payload['query'] == "FastAPI":
            print("[PASS] JSON Payload 存储与读取正常")
        else:
            print("[FAIL] JSON Payload 读取错误")

        stmt_metric = select(ProcessingMetric).where(ProcessingMetric.document_id == doc_id)
        saved_metric = (await session.execute(stmt_metric)).scalar_one()
        print(f"  Stage: {saved_metric.stage}, Duration: {saved_metric.duration_ms}ms")
        
        if saved_metric.duration_ms == 1500:
            print("[PASS] 性能指标记录正常")
        else:
            print("[FAIL] 性能指标数据错误")

if __name__ == "__main__":
    asyncio.run(verify_analytics_models())
