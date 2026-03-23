from typing import Dict, Any
from spine_cli.core.agents.state import DocumentState
from app.services.toc.manager import TOCManager

def structure_agent_node(state: DocumentState) -> Dict[str, Any]:
    """
    Structure Agent: 接收上游提取结果并进行语义拓扑重建。
    """
    # 接收来自 Classifier 或 ParserWorker 的结果
    incoming_toc = state.get("structured_toc", [])
    
    if not incoming_toc:
        return {"current_node": "structure_agent"}

    manager = TOCManager()
    # 重新构建树结构并清理冗余
    structured_tree = manager.build_tree(incoming_toc)
    conflicts = manager.get_conflict_report()
    
    return {
        "structured_toc": structured_tree,
        "confidence_score": 0.95 if not conflicts else 0.7,
        "metadata": {**state.get("metadata", {}), "conflict_report": conflicts},
        "current_node": "structure_agent"
    }
