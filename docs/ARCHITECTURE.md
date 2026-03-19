# SpineDoc 架构设计

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      SpineDoc Backend                        │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server                                              │
│  ├── API Endpoints (Documents / RAG / TOC)                  │
│  ├── Services (Parser / RAG Engine / TOC Extractor)         │
│  └── Core (Config / DB / Models)                            │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (pgvector)    Redis (Cache)                     │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 核心模块

### 1. ISR 隐式脊梁重建

```python
# backend/app/services/parser.py
class HybridParser:
    """
    混合 PDF 解析器
    
    支持三种模式：
    1. Metadata 提取（原生 PDF 目录）
    2. 文本层嗅探（目录页正则匹配）
    3. Body-Scan 锚点扫描（无目录文档）
    """
```

### 2. SCR 级联检索

```python
# backend/app/services/rag/engine.py
class RAGEngine:
    """
    RAG 检索引擎
    
    三级级联：
    1. TOC 路由：基于目录标题相似度锁定章节
    2. 向量召回：在精准范围内匹配向量
    3. Reranker：重排序提升精度
    """
```

## 📊 数据模型

- **Document**: 文档元数据
- **TocItem**: 目录项（层级结构）
- **Chunk**: 文本切片（带向量嵌入）

## 🔄 工作流程

1. 上传 PDF → 解析 TOC → 存储 Document
2. 后台任务 → 文本切片 → 向量化 → 存储 Chunk
3. 用户查询 → TOC 路由 → 向量召回 → Rerank → 返回结果
