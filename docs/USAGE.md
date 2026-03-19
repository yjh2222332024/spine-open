# SpineDoc 使用指南

## 🚀 5 分钟快速开始

### 方式一：Docker 一键启动（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/yjh2222332024/Spine-open.git
cd Spine-open

# 2. 启动数据库
cd docker
docker-compose up -d db redis

# 3. 配置环境变量
cp ../.env.template ../backend/.env
# 编辑 .env 文件，填入你的 API Key

# 4. 启动后端
docker-compose up -d backend

# 5. 访问 API 文档
# http://localhost:8000/docs
```

### 方式二：本地开发环境

```bash
# 1. 安装 Python 3.12+
python --version

# 2. 安装依赖
cd backend
pip install -r requirements.txt

# 3. 启动数据库（Docker）
docker run -d --name spinedoc-db \
  -e POSTGRES_USER=spinedoc \
  -e POSTGRES_PASSWORD=spinedoc123 \
  -e POSTGRES_DB=spinedoc \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 4. 配置环境变量
cp .env.template .env

# 5. 启动服务
cd backend
python -m app.main
```

---

## 📖 API 使用示例

### 1. 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf" \
  -F "title=测试文档"
```

### 2. RAG 检索

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid-here",
    "query": "什么是 ISR 隐式脊梁重建？",
    "top_k": 5
  }'
```

### 3. 获取文档目录

```bash
curl http://localhost:8000/api/v1/spine/{document_id}/toc
```

---

## 🐍 Python SDK 示例

```python
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

async def main():
    async with httpx.AsyncClient() as client:
        # 上传文档
        with open("test.pdf", "rb") as f:
            response = await client.post(
                f"{BASE_URL}/api/v1/documents",
                files={"file": f},
                data={"title": "测试文档"}
            )
        doc = response.json()
        
        # RAG 检索
        response = await client.post(
            f"{BASE_URL}/api/v1/rag/query",
            json={
                "document_id": doc["id"],
                "query": "什么是 ISR 技术？",
                "top_k": 5
            }
        )
        result = response.json()
        
        print(f"时延：{result['metrics']['latency_ms']}ms")
        for chunk in result['chunks']:
            print(f"第{chunk['page']}页：{chunk['content'][:100]}...")

asyncio.run(main())
```

---

## 🔧 常见问题

### Q1: LLM API Key 未配置

A: 在 `.env` 文件中配置：
```env
LLM_API_KEY=sk-your-api-key
```

### Q2: 数据库连接失败

A: 检查 PostgreSQL 是否启动：
```bash
docker ps | grep spinedoc-db
```

### Q3: 检索结果为空

A: 可能原因：
1. 文档尚未完成向量化处理
2. 查询问题与文档内容不相关

---

## 💡 最佳实践

- 单文档页数：建议 <5000 页
- 文件格式：PDF（原生或扫描件）
- 文件大小：<50MB

---

## 🎯 下一步

- 📚 查看 [架构设计](ARCHITECTURE.md)
- 📊 查看 [性能基准](BENCHMARK.md)
- 💼 了解 [企业版](https://github.com/yjh2222332024/Spine-enterprise)
