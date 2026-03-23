import fitz
import os
from typing import Dict, Any
from spine_cli.core.agents.state import DocumentState, DocumentType
from app.services.parser import hybrid_parser

def classifier_node(state: DocumentState) -> Dict[str, Any]:
    """
    Classifier Agent (Spine-CLI 增强版): 
    不再仅仅是分类，它现在集成了 ISR 初步扫描能力。
    """
    file_path = state.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return {"processing_errors": ["File not found."]}

    # 🚀 核心动作：直接调用我们调优过的 HybridParser 执行脊梁提取
    # 这样可以确保‘学术逻辑胶水’被触发
    toc_items = hybrid_parser.extract_toc(file_path)
    
    doc = fitz.open(file_path)
    total_pages = len(doc)
    doc.close()

    # 根据提取结果判定状态
    doc_type = DocumentType.NATIVE if toc_items else DocumentType.SCANNED
    confidence = 0.9 if len(toc_items) > 5 else 0.5
    
    return {
        "document_type": doc_type,
        "total_pages": total_pages,
        "structured_toc": toc_items, # 直接填充初步结果
        "confidence_score": confidence,
        "current_node": "classifier"
    }
