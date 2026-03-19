# SpineDoc Backend

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

> **长文档检索专家** - 专为 1000-5000 页长文档设计的 RAG 后端引擎

**性能对比** | **使用文档** | **企业版**

---

## 🚀 核心特性

- **ISR 隐式脊梁重建**：还原文档逻辑结构，检索精度提升 108.9%
- **SCR 级联检索**：TOC 路由 + 向量召回，时延仅 14.8ms
- **长文档优化**：支持单文档 5000 页，100+ 文档协同
- **极致成本**：15 文档协同检索仅 2 万 Token（降低 95.6%）

---

## 📊 性能对比

| 指标 | GraphRAG | LightRAG | SpineDoc |
|------|----------|----------|----------|
| 长文档支持 | ❌ | ❌ | ✅ **5000 页** |
| 检索时延 | >500ms | >100ms | **14.8ms** |
| Token 消耗 | 未披露 | 30K/查询 | **2 万/15 文档** |
| 部署成本 | ¥5000+/月 | ¥2000+/月 | **¥500/月** |
| 检索精度 | 8.5/10 | 领先 52.3% | **8.5/10 (+108.9%)** |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yjh2222332024/Spine-open.git
cd Spine-open
```

### 2. 启动数据库（Docker）

```bash
cd docker
docker-compose up -d db redis
```

### 3. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp ../.env.template ../backend/.env
# 编辑 .env 文件，填入你的 LLM API Key
```

### 5. 启动后端

```bash
cd backend
python -m app.main
```

访问 http://localhost:8000/docs 查看 API 文档

---

## 📁 项目结构

```
Spine-open/
├── backend/
│   ├── app/
│   │   ├── core/              # 核心配置
│   │   ├── schemas/           # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── parser.py      # 混合解析器
│   │   │   ├── rag/           # RAG 引擎
│   │   │   └── toc/           # TOC 提取
│   │   └── api/               # RESTful API
│   ├── scripts/               # 工具脚本
│   └── tests/                 # 测试
├── docker/                    # Docker 配置
├── examples/                  # 示例代码
├── docs/                      # 文档
├── .env.template
├── LICENSE
└── README.md
```

---

## 📖 文档

- [使用指南](docs/USAGE.md)
- [架构设计](docs/ARCHITECTURE.md)
- [性能基准](docs/BENCHMARK.md)

---

## 🧪 运行测试

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## 🐳 Docker 部署

```bash
cd docker
docker-compose up -d
docker-compose logs -f backend
```

---

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE)

---

## 💼 企业版功能

需要企业级功能？查看 [SpineDoc Enterprise](https://github.com/yjh2222332024/Spine-enterprise)(待发布)

- ✅ 多智能体编排（LangGraph 5 节点）
- ✅ OCR+ 语义对齐（扫描件处理）
- ✅ 跨文档知识图谱
- ✅ 自动标注流水线
- ✅ API Key 鉴权 + 限流
- ✅ SLA 保障 + 技术支持

---

## 📬 联系方式

- **项目问题**: [GitHub Issues](https://github.com/yjh2222332024/Spine-open/issues)
- **商务合作**: 2857922968@qq.com

