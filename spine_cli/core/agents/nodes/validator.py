from typing import Dict, Any
from spine_cli.core.agents.state import DocumentState
from spine_cli.core.agents.protocol import AgentTask, create_task_instruction
from app.services.toc.validator_rules import TOCValidator

def validator_node(state: DocumentState) -> Dict[str, Any]:
    structured_toc = state.get("structured_toc", [])
    total_pages = state.get("total_pages", 0)
    doc_type = state.get("document_type")
    conflicts = state.get("metadata", {}).get("conflict_report", [])
    
    quality_score = TOCValidator.evaluate_quality(structured_toc, total_pages, doc_type, conflicts)
    
    if quality_score < 0.6 and state.get("retry_count", 0) < state.get("max_retries", 3):
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "confidence_score": quality_score,
            "current_node": "validator"
        }
    
    return {
        "confidence_score": quality_score,
        "current_node": "validator",
        "metadata": {**state.get("metadata", {}), "status": "passed" if quality_score >= 0.6 else "failed"}
    }
