from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from uuid import UUID

class ThinkingBudget(str, Enum):
    """
    自适应推理预算等级
    借鉴：DeepSeek-R1 / Claude 3.7 Sonnet
    """
    AUTO = "auto"           # 智能路由：根据问题复杂度和检索置信度自动升级
    FAST = "fast"           # Top-3, 无 Rerank, <100ms
    BALANCED = "balanced"   # Top-5, 有 Rerank, ~300ms 
    DEEP = "deep"           # Top-10, Rerank + HMAC, ~2s

class SourceChunk(BaseModel):
    chunk_id: Optional[UUID] = None
    content: str
    score: float
    toc_id: Optional[UUID] = None
    toc_title: Optional[str] = None
    full_path: Optional[str] = Field(default=None, description="逻辑全路径导航 chain")
    page: Optional[int] = None

class RagQuery(BaseModel):
    query: str
    document_id: UUID
    target_toc_ids: Optional[List[UUID]] = Field(default=None, description="限定检索的目录节点 ID 列表")
    top_k: int = 5

    # 🆕 新增：自适应推理预算
    thinking_budget: ThinkingBudget = Field(
        default=ThinkingBudget.AUTO,
        description="推理预算等级：auto/fast/balanced/deep"
    )

    # 🆕 高级参数 (仅 DEEP/AUTO 模式生效)
    enable_debate: bool = Field(
        default=False,
        description="是否启动多智能体辩论"
    )
    conflict_threshold: float = Field(
        default=0.3,
        description="触发扩展检索的置信度阈值"
    )

    @model_validator(mode='after')
    def validate_budget_logic(self) -> 'RagQuery':
        if self.thinking_budget not in [ThinkingBudget.DEEP, ThinkingBudget.AUTO]:
            self.enable_debate = False
        return self

class RagResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    meta: Dict[str, Any] = {}
