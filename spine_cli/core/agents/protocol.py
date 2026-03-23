from enum import Enum
from typing import Dict, Any

class AgentTask(str, Enum):
    EXTRACT_METADATA = "extract_metadata"
    EXTRACT_VISUAL = "extract_visual"
    RECONSTRUCT_TREE = "reconstruct_tree"
    VALIDATE_LOGIC = "validate_logic"
    RETRY_WITH_OCR = "retry_with_ocr"

def create_task_instruction(task: AgentTask, priority: int = 1, context: str = "") -> Dict[str, Any]:
    return {"task": task, "priority": priority, "context": context}
