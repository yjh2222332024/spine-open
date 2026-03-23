from typing import Dict, Any
from spine_cli.core.agents.state import DocumentState

def llm_recovery_node(state: DocumentState) -> Dict[str, Any]:
    toc = state.get("structured_toc", [])
    if not toc: return {"current_node": "llm_recovery"}
    
    # 模拟语义自愈算法 (页码单调性与层级对齐)
    recovered = []
    last_p = -1
    for item in toc:
        if item["page"] < last_p: item["page"] = last_p # 强行单调
        last_p = item["page"]
        recovered.append(item)
        
    return {
        "structured_toc": recovered,
        "confidence_score": 0.65,
        "metadata": {**state.get("metadata", {}), "status": "recovered"},
        "current_node": "llm_recovery"
    }
