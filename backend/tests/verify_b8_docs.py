import json
import os

def verify_docs():
    print("--- 验证 API 文档生成 ---")
    
    # 1. 检查 openapi.json
    json_path = "backend/openapi.json"
    if os.path.exists(json_path):
        print(f"[PASS] {json_path} 存在")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            paths = data.get("paths", {})
            
            # Check critical endpoints
            if "/api/v1/upload/init" in paths:
                print("[PASS] 包含分块上传接口")
            else:
                print("[FAIL] 缺失 /upload/init 接口")
                
            if "/api/v1/folders/" in paths:
                print("[PASS] 包含文件夹接口")
            else:
                print("[FAIL] 缺失 /folders/ 接口")
    else:
        print(f"[FAIL] {json_path} 未生成")

    # 2. 检查指南文档
    guide_path = "docs/API_Guide_Mobile.md"
    if os.path.exists(guide_path):
        print(f"[PASS] {guide_path} 存在")
    else:
        print(f"[FAIL] {guide_path} 不存在")

if __name__ == "__main__":
    verify_docs()
