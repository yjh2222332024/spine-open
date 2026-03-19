import asyncio
import os
import shutil
from uuid import uuid4
from fastapi import UploadFile
from io import BytesIO
from app.services.storage import StorageService
from app.core.config import settings

# 简单的 MockUploadFile 类用于测试
class MockUploadFile(UploadFile):
    def __init__(self, filename, content):
        self.filename = filename
        self.file = BytesIO(content)
        self.size = len(content)
        self.headers = {}

async def verify_storage():
    print("--- 验证存储服务 ---")
    
    # 1. 准备测试数据
    test_content = b"Hello, StructuRAG Storage!"
    test_filename = "test.pdf"
    mock_file = MockUploadFile(test_filename, test_content)
    
    workspace_id = uuid4()
    document_id = uuid4()
    
    print(f"Workspace ID: {workspace_id}")
    print(f"Document ID: {document_id}")
    
    # 2. 初始化服务
    # 使用测试专用的临时目录
    test_root = os.path.join(os.getcwd(), "backend", "test_storage_tmp")
    service = StorageService(test_root)
    
    try:
        # 3. 执行保存
        print("正在保存文件...")
        result = await service.save_upload_file(mock_file, workspace_id, document_id)
        
        print("保存结果:", result)
        
        # 4. 验证
        expected_path = os.path.join(test_root, "workspaces", str(workspace_id), f"{document_id}.pdf")
        
        if os.path.exists(expected_path):
            print("[PASS] 文件已创建")
        else:
            print("[FAIL] 文件未找到:", expected_path)
            
        with open(expected_path, "rb") as f:
            saved_content = f.read()
            if saved_content == test_content:
                print("[PASS] 文件内容一致")
            else:
                print("[FAIL] 文件内容不匹配")
                
        if result['size'] == len(test_content):
            print("[PASS] 文件大小正确")
        else:
            print(f"[FAIL] 文件大小错误: Exp {len(test_content)}, Got {result['size']}")

    finally:
        # 5. 清理测试环境
        if os.path.exists(test_root):
            shutil.rmtree(test_root)
            print("测试目录已清理")

if __name__ == "__main__":
    asyncio.run(verify_storage())
