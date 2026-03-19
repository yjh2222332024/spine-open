"""
SpineDoc 快速开始示例

运行前请确保：
1. 后端服务已启动 (http://localhost:8000)
2. 已上传至少一个文档
"""

import httpx
import asyncio

BASE_URL = "http://localhost:8000"

async def quickstart():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🚀 SpineDoc 快速开始示例\n")
        
        # 1. 获取文档列表
        print("📋 步骤 1: 获取文档列表")
        response = await client.get(f"{BASE_URL}/api/v1/documents")
        docs = response.json()
        
        if not docs:
            print("❌ 暂无文档，请先上传文档")
            return
        
        print(f"✅ 找到 {len(docs)} 个文档\n")
        
        # 2. 选择第一个文档
        doc = docs[0]
        print(f"📄 使用文档：{doc['title']} ({doc['total_pages']}页)\n")
        
        # 3. 发起 RAG 检索
        print("🔍 步骤 2: 发起 RAG 检索")
        query = "文档的核心技术是什么？"
        print(f"❓ 问题：{query}\n")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/rag/query",
            json={
                "document_id": doc["id"],
                "query": query,
                "top_k": 5
            }
        )
        result = response.json()
        
        # 4. 显示结果
        print(f"⏱️  响应时延：{result['metrics']['latency_ms']}ms\n")
        print("=" * 60)
        
        for i, chunk in enumerate(result['chunks'], 1):
            print(f"\n[证据 {i}]")
            print(f"📍 位置：第{chunk['page']}页 | {chunk.get('toc_path', '未知章节')}")
            print(f"🎯 置信度：{chunk['score']:.2f}")
            print(f"📝 内容：{chunk['content'][:300]}...\n")
        
        print("✅ 示例完成！")

if __name__ == "__main__":
    asyncio.run(quickstart())
