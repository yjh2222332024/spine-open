import os
import yaml

def verify_docker_config():
    print("--- 验证 Docker 部署配置 ---")
    
    # 1. 检查 Dockerfile
    if os.path.exists("backend/Dockerfile"):
        print("[PASS] Dockerfile 存在")
        with open("backend/Dockerfile", "r", encoding="utf-8") as f:
            content = f.read()
            if "libgl1-mesa-glx" in content:
                print("[PASS] 包含 OpenCV 依赖 (libgl1-mesa-glx)")
            else:
                print("[FAIL] 缺少 OpenCV 依赖")
                
            if "mkdir -p /app/storage" in content:
                 print("[PASS] 包含存储目录创建")
            else:
                 print("[FAIL] 未自动创建存储目录")
    else:
        print("[FAIL] Dockerfile 不存在")

    # 2. 检查 docker-compose.yml
    if os.path.exists("docker-compose.yml"):
        print("[PASS] docker-compose.yml 存在")
        try:
            with open("docker-compose.yml", "r", encoding="utf-8") as f:
                compose = yaml.safe_load(f)
                
            services = compose.get("services", {})
            if "db" in services and "pgvector/pgvector" in services["db"]["image"]:
                print("[PASS] DB 使用了 pgvector 镜像")
            else:
                print("[FAIL] DB 镜像配置错误")
                
            if "backend" in services:
                volumes = services["backend"].get("volumes", [])
                has_storage = any("storage" in v for v in volumes)
                if has_storage:
                    print("[PASS] Backend 挂载了持久化存储")
                else:
                    print("[FAIL] Backend 未挂载存储卷")
                    
        except Exception as e:
            print(f"[FAIL] docker-compose 解析失败: {e}")
    else:
        print("[FAIL] docker-compose.yml 不存在")

if __name__ == "__main__":
    verify_docker_config()
