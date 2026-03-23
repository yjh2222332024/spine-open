import os
from typing import List, Dict, Optional
from mcp.server.fastmcp import FastMCP
from spine_cli.core.engine import SpineEngine

# 创建 FastMCP 实例
mcp = FastMCP("SpineDoc-Engine")
engine = SpineEngine()

@mcp.tool()
async def ingest_document(file_path: str) -> str:
    """
    解析 PDF 文档并重建逻辑脊梁 (ISR)。
    
    Args:
        file_path: PDF 文件的绝对路径。
    """
    if not os.path.exists(file_path):
        return f"错误: 找不到文件 {file_path}"
    
    doc_id = await engine.ingest_document(file_path)
    return f"成功摄入文档。ID: {doc_id}"

@mcp.tool()
async def list_available_documents() -> List[Dict]:
    """
    列出当前知识库中所有已解析的文档。
    """
    return engine.list_documents()

@mcp.tool()
async def get_document_spine(doc_id: str) -> Dict:
    """
    获取指定文档的逻辑脊梁结构 (TOC)。
    """
    doc = engine.get_document(doc_id)
    if not doc:
        return {"error": "未找到文档"}
    return {"filename": doc["filename"], "toc": doc["toc"]}

@mcp.tool()
async def search_knowledge(query: str, doc_id: Optional[str] = None) -> List[Dict]:
    """
    在知识库中进行逻辑感知检索。
    返回相关的原文片段、页码和所属章节路径。
    """
    docs = engine.list_documents()
    if not docs:
        return [{"error": "库中尚无文档，请先 ingest。"}]
    
    target_doc = engine.get_document(doc_id) if doc_id else docs[-1]
    
    # 优先语义，逻辑兜底
    results = []
    if target_doc.get("vectorized") and engine.vector_store.is_available:
        results = engine.vector_store.search(query, doc_id=target_doc["id"])
    
    if not results:
        results = engine.search_fallback(target_doc, query)
        
    return results

def run_mcp_server():
    """启动 MCP 服务器 (stdio 模式)"""
    mcp.run(transport="stdio")
