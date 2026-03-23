# 🏛️ SpineDoc (阅脊): The Semantic Logic Engine for Shell

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Trident Architecture](https://img.shields.io/badge/Arch-Trident_v1.2.0-red.svg)](#-trident-architecture)

> **"Stop chatting with PDFs. Start reconstructing their logic."**
>
> SpineDoc is an agentic RAG engine designed specifically for **ultra-long documents (1000-5000 pages)**. It doesn't just "read" text; it reconstructs the **Implicit Spine (ISR)** of a document to enable high-precision, logical-aware retrieval.

---

## 🔱 Trident Architecture

SpineDoc v1.2.0 establishes a three-in-one ecosystem for document intelligence:

1.  **Core CLI (The Engine)**: A powerful shell interface for indexing, tree-viewing, and cross-document synthesis.
2.  **Embedded MCP Server (The Protocol)**: Instant integration with Claude Desktop, Cursor, and IDEs via the Model Context Protocol.
3.  **Gemini Agent Skill (The Intelligence)**: Native integration for AI agents to autonomously manage and query your knowledge crystals.

---

## 🌟 Key Innovations

*   **🧬 ISR (Implicit Spine Reconstruction)**: Recovers the document's logical hierarchy using a multi-agent federation.
*   **🛰️ Cascading Retrieval**: Routes queries through the logical spine first, reducing token costs by **90%** compared to GraphRAG.
*   **⚔️ Matrix Fusion**: Orchestrates multi-document "debates" to generate comprehensive comparative summaries.
*   **🎯 Physical Attribution**: Every answer is anchored to a **Physical Page Number** and **Section Title**.

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/yjh2222332024/Spine-open.git
cd Spine-open
pip install -e .
```

### 2. Configuration
Create a `.env` file in the root directory and add your API Key:
```bash
LLM_API_KEY=your_key_here
```

### 3. Run Your First Synthesis
```bash
# Index official example papers
spine ingest examples/academic_papers/

# Generate a comparative summary
spine compare "Innovation and Performance in RAG"
```

---

## 📊 Benchmarks

| Metric | GraphRAG (Baseline) | **SpineDoc (v1.2.0)** |
| :--- | :--- | :--- |
| **Indexing Speed** | ~1 hour / 3 PDFs | **43.1 seconds / 3 PDFs** |
| **Token Cost** | ~20,000+ Tokens | **~2,150 Tokens** |
| **Precision** | Community Level | **Physical Page Level** |

*For detailed reports, see [BENCHMARK.md](BENCHMARK.md).*

---

## 🏛️ Acknowledgments & Credits

### Core Technology
SpineDoc is powered by the following open-source giants:
- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Agentic orchestration.
- **[LanceDB](https://github.com/lancedb/lancedb)**: High-performance vector storage.
- **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)**: Advanced document parsing.

### Demo Dataset
The example papers in `examples/academic_papers/` are sourced from **arXiv.org**. We deeply thank the authors and the research community for their open contributions to the field of AI and RAG.

---

## 📄 License
This project is licensed under the **MIT License**.

Copyright (c) 2026 SpineDoc Team. All Rights Reserved.
