# SpineDoc 性能基准测试

## 📊 测试环境

- **CPU**: 2 Core
- **Memory**: 4GB
- **Database**: PostgreSQL 16 + pgvector
- **Cache**: Redis 7

## 🎯 测试场景

### 场景 1: 单文档检索（1200 页）

```
查询："什么是 ISR 技术？"
结果:
- Token 消耗：1,342 tokens
- 响应时延：14.8ms
- 检索精度：8.5/10
```

### 场景 2: 15 文档协同检索（18,000 页）

```
查询："总结这些文档的核心技术贡献"
结果:
- Token 消耗：20,443 tokens
- 响应时延：45.2ms
- 检索精度：8.2/10
```

## 📈 对比数据

| 指标 | GraphRAG | LightRAG | SpineDoc |
|------|----------|----------|----------|
| 检索时延 | >500ms | >100ms | **14.8ms** |
| Token 消耗 | 未披露 | 30K/查询 | **2 万/15 文档** |
| 长文档支持 | ❌ | ❌ | ✅ **5000 页** |

## 🔍 测试方法

```bash
cd backend
python scripts/benchmark.py --documents 15 --query "RAG 优化技术"
```
