"""
文档上传示例

运行前请确保：
1. 后端服务已启动 (http://localhost:8000)
2. 准备好要上传的 PDF 文件
"""

import httpx
import asyncio
import sys

BASE_URL = "http://localhost:8000"

async def upload_pdf(file_path: str, title: str = None):
    async with httpx.AsyncClient(timeout=300.0) as client:
        if title is None:
            title = file_path.split("\\")[-1]
        
        print(f"📤 正在上传：{file_path}")
        
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{BASE_URL}/api/v1/documents",
                files={"file": f},
                data={"title": title}
            )
        
        if response.status_code == 200:
            doc = response.json()
            print(f"✅ 上传成功！")
            print(f"   文档 ID: {doc['id']}")
            print(f"   标题：{doc['title']}")
            print(f"   页数：{doc['total_pages']}")
            print(f"   状态：{doc['status']}")
            print(f"\n💡 提示：文档正在处理中，请稍后查询")
        else:
            print(f"❌ 上传失败：{response.text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python upload_document.py <pdf 文件路径> [标题]")
        print("示例：python upload_document.py ./test.pdf 测试文档")
        sys.exit(1)
    
    file_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(upload_pdf(file_path, title))
