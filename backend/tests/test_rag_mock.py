import sys
import os
import asyncio
from uuid import uuid4

# 路径 Hack，确保能导入 app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag.engine import rag_engine
from app.schemas.rag import ChatQuery

async def test_rag_flow():
    print("\n--- Testing RAG Interface (Mock) ---")
    
    # 1. 构造模拟请求
    fake_doc_id = uuid4()
    fake_toc_ids = [uuid4(), uuid4()] # 模拟用户选了两个章节
    
    query = ChatQuery(
        document_id=fake_doc_id,
        query="什么是 TOC-Driven RAG?",
        toc_item_ids=fake_toc_ids
    )
    
    print(f"Request: {query.model_dump_json(indent=2)}")
    
    # 2. 调用流式接口
    print("\nResponse Stream:")
    try:
        async for chunk in rag_engine.chat_stream(query):
            print(chunk, end="", flush=True)
            # 模拟一点点网络延迟
            await asyncio.sleep(0.01)
            
        print("\n\n✅ Test Passed: Stream completed successfully.")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_rag_flow())
