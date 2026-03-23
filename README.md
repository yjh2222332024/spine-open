# 🏛️ SpineDoc (阅脊): 终端语义逻辑引擎

[![License: MIT](https://img.shields.io/badge/许可证-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Trident Architecture](https://img.shields.io/badge/架构-Trident_v1.2.0-red.svg)](#-三叉戟架构-trident)

> **"不要只是与 PDF 聊天，去重构它们的逻辑。"**
>
> **SpineDoc (阅脊)** 是一款专为 **超长文档 (1000-5000 页)** 设计的智能 Agent 引擎。它拒绝盲目的文本切块，通过独创的 **隐式脊梁重建 (ISR)** 技术，将非结构化的 PDF 还原为有序的“知识晶体”，实现逻辑感知级的高精度检索。

---

## 🔱 三叉戟架构 (Trident Architecture)

SpineDoc v1.2.0 构建了“三位一体”的文档智能生态：

1.  **核心 CLI (引擎层)**: 强大的终端交互界面，支持秒级入库、逻辑树可视化及跨文档矩阵融合综述。
2.  **内置 MCP 服务器 (协议层)**: 完美对接 Claude Desktop、Cursor 及各大 IDE，让顶级 AI 直接调度本地文档逻辑。
3.  **Gemini Agent Skill (智能层)**: 原生集成 AI Agent 技能，实现知识晶体的自主编纂与智能化查询。

---

## 🌟 核心黑科技

*   **🧬 ISR (Implicit Spine Reconstruction)**: 采用多智能体联邦驱动，精准重建文档的逻辑骨架。
*   **🛰️ 级联检索 (Cascading Retrieval)**: 优先通过逻辑脊梁路由，相比 GraphRAG 降低 **90%** 的 Token 消耗。
*   **⚔️ 矩阵融合 (Matrix Fusion)**: 跨文档“协同辩论”技术，一键生成多篇论文/报告的对比性综述。
*   **🎯 物理级溯源**: 每一个回答都精准锚定 **PDF 物理页码** 与 **逻辑章节名称**。

---

## 🚀 极速上手

### 1. 安装
```bash
git clone https://github.com/yjh2222332024/Spine-open.git
cd Spine-open
pip install -e .
```

### 2. 配置环境变量
在项目根目录下创建 `.env` 文件并添加你的 API Key：
```bash
LLM_API_KEY=你的API_KEY
```

### 3. 开启你的第一场逻辑透析
```bash
# 入库官方演示学术论文
spine ingest examples/academic_papers/

# 运行跨文档对比综述
spine compare "RAG 技术的创新与性能对比"
```

---

## 📊 性能量化 (真实测评数据)

| 维度 | GraphRAG (行业基准) | **SpineDoc (v1.2.0)** | **提升/优势** |
| :--- | :--- | :--- | :--- |
| **构建速度** | ~1 小时 / 3 篇 PDF | **43.1 秒 / 3 篇 PDF** | **🚀 快 ~100 倍** |
| **Token 成本** | ~20,000+ Tokens | **~2,150 Tokens** | **💰 节省 90.7%** |
| **引用精度** | 社区/报告级 | **物理页码级** | **🎯 100% 真实溯源** |

*详细测评报告请参阅 [BENCHMARK.md](BENCHMARK.md)。*

---

## 🏛️ 致谢与声明

### 核心技术支持
SpineDoc 的强大离不开以下开源项目的支持：
- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Agentic 任务编排。
- **[LanceDB](https://github.com/lancedb/lancedb)**: 高性能向量存储。
- **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)**: 深度文档解析。

### 演示数据集
`examples/academic_papers/` 中的示例论文均源自 **arXiv.org**。我们深表感谢论文作者及科研社区在 AI 与 RAG 领域做出的杰出贡献。

---

## 联系方式
- **邮箱**: 2857922968@qq.com
- **GitHub**: [yjh2222332024](https://github.com/yjh2222332024)
- **小红书**:肯德基和麦当劳真是一对苦命鸳鸯 

## 📄 开源协议
本项目采用 **MIT License** 协议。

Copyright (c) 2026 **Junhao Yan (严俊皓)**. All Rights Reserved.
