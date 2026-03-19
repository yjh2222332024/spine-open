
import asyncio
import uuid
import json
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag.engine import RAGEngine
from app.core.models import TocItem, Chunk
from app.schemas.rag import RagQuery

async def test_spine_routing_logic():
    print("\n" + "="*50)
    print("   SpineDoc Logic-Routed Retrieval Verification   ")
    print("="*50)

    # 1. 初始化引擎
    engine = RAGEngine()
    doc_id = uuid.uuid4()
    
    # 2. 模拟目录结构 (Spine)
    toc_1 = TocItem(id=uuid.uuid4(), title="第一章: 脊柱解剖", page=10, level=1, document_id=doc_id)
    toc_1_1 = TocItem(id=uuid.uuid4(), title="1.1 椎骨结构详情", page=12, level=2, parent_id=toc_1.id, document_id=doc_id)
    
    toc_map = {
        toc_1.id: toc_1,
        toc_1_1.id: toc_1_1
    }

    # 3. 模拟 Chunk 数据
    chunk_anatomy = MagicMock(spec=Chunk)
    chunk_anatomy.id = uuid.uuid4()
    chunk_anatomy.content = "椎骨由椎体和椎弓组成，保护着脊髓。"
    chunk_anatomy.page_number = 12
    chunk_anatomy.toc_item_id = toc_1_1.id
    chunk_anatomy.distance = 0.1

    # 4. 智能 Mock 数据库 Session
    mock_session = AsyncMock()
    
    # 定义一个灵活的 execute 处理器
    async def smart_execute(stmt, params=None):
        stmt_str = str(stmt).lower()
        mock_res = MagicMock()
        
        if "from tocitem" in stmt_str:
            # 模拟目录查询
            mock_res.scalars.return_value.all.return_value = list(toc_map.values())
            # 模拟 scalar_one_or_none (用于递归路径获取)
            # 我们需要从 params 或 stmt 中提取 ID，这里简化处理
            mock_res.scalar_one_or_none.side_effect = lambda: list(toc_map.values())[0] 
            return mock_res
        elif "from chunk" in stmt_str:
            # 模拟分块查询
            mock_res.all.return_value = [chunk_anatomy]
            return mock_res
        
        return mock_res

    mock_session.execute = smart_execute

    # 5. 屏蔽重排序模型下载，直接 Mock 返回
    with patch.object(RAGEngine, '_get_reranker', return_value=None):
        # 6. 执行测试 Query
        query_text = "椎骨的解剖结构是什么？"
        request = RagQuery(query=query_text, document_id=doc_id, top_k=1)
        
        print(f"\n[Test] Querying: '{query_text}'")
        
        found_path = False
        async for event in engine.chat_stream(request, session=mock_session):
            if event["type"] == "status":
                print(f"  [Status] {event['content']}")
            elif event["type"] == "message":
                pass # 忽略正文输出
            
            # 检查上下文注入是否包含了全路径
            if "第一章" in str(event):
                found_path = True

        if found_path:
            print("\n✅ SUCCESS: Hierarchy context ('Chapter > Section') injected correctly.")
        else:
            print("\n❌ FAILED: Hierarchy context missing.")

    print("\n" + "-"*30)
    print("Verification Completed.")

if __name__ == "__main__":
    asyncio.run(test_spine_routing_logic())
