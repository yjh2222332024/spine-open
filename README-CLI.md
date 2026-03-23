# 🏛️ SpineDoc CLI: The Semantic Logic Engine for Shell (v1.2.0)

> **"不要只是与 PDF 聊天，要重构它们的逻辑。"**
>
> SpineDoc CLI (阅脊) 是一款专为长文档设计的**逻辑感知型 RAG 引擎**。在 v1.2.0 版本中，我们正式确立了 **Trident (三叉戟) 架构**：将终端命令、大模型协议 (MCP) 与 Agent 技能 (Gemini Skill) 完美合龙，打造真正的 AI 时代知识基座。

---

## 🔱 Trident (三叉戟) 架构

*   **1. 核心 CLI (The Core)**: 支持 Ingest, Ask, Compare, Tree 等闭合逻辑，支持秒级晶体化处理。
*   **2. 内置 MCP 服务器 (The Protocol)**: 通过 `spine mcp` 一键开启，让 Claude Desktop、Cursor 或 IDE 远程调度你的本地文档解析能力。
*   **3. Gemini Skill 原生增强 (The Agent)**: 深度集成于 Gemini CLI。当你提到 PDF 或长文档时，Gemini 将自动激活 SpineDoc 专家模式。

---

## 🌟 核心黑科技

*   **🧬 ISR (Implicit Spine Reconstruction)**: 采用 5 智能体联邦 (LangGraph) 驱动，精准重建文档的逻辑脊梁（TOC）。
*   **🕸️ OpenKG Alignment**: 零成本对接全球最大中文知识图谱，为每个章节锚点赋予全球唯一知识坐标。
*   **🛰️ Cascading Retrieval**: 独创“级联式语义路由”。比 GraphRAG 节省 99% Token，精度不相上下。
*   **⚔️ Matrix Fusion**: 支持跨文档协同辩论。一键生成 100+ 篇论文/合同的对比性综述报告。

---

## ⚡ 极速上手

### 1. 安装 (极简、无需配置数据库)
```bash
pip install -e Spine-open
# 确保在 .env 中配置了你的 LLM_API_KEY
```

### 2. 建立知识大典 (Ingest)
将你的 PDF 文件夹瞬间晶体化：
```bash
spine ingest ./papers/ --workers 6
```

### 3. 开启 MCP 生态融合 (New!)
让你的 Claude 具备“脊梁解析”能力：
```bash
spine mcp
```

### 4. 深度问答 (Ask)
```bash
spine ask "HippoRAG 2 的核心改进是什么？" --kg
```

---

## 🛠️ 进阶命令参考

| 命令 | 说明 |
| :--- | :--- |
| `spine ingest <path>` | 摄入文档/文件夹。支持 `--workers` 参数。 |
| `spine mcp` | **[New]** 启动内置 MCP 服务器，对接外部 AI 客户端。 |
| `spine ask "<query>"` | 问答。支持 `--kg` (图谱增强) 和 `--limit` (片段数)。 |
| `spine compare "<topic>"` | 跨文档对比。支持 `--docs` 指定特定文档 ID。 |
| `spine list` | 列出当前知识库中的所有“知识晶体”。 |
| `spine tree <id>` | 打印彩色的文档逻辑树。 |

---

## 🤝 贡献与社区

*   **官网**: [spinedoc.ai](https://spinedoc.ai)
*   **开源**: [Spine-open GitHub](https://github.com/yjh2222332024/Spine-open)
*   **愿景**: 让人类不再被文档淹没，让知识重新变得有序。

---
*Powered by SpineDoc Trident Engine v1.2.0*
