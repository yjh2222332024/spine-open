"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
try:
    from app.agents.state import DocumentType
except ImportError:
    # 架构师适配: 针对精简版/CLI版的回退逻辑
    from enum import Enum
    class DocumentType(str, Enum):
        NATIVE = "native"
        SCANNED = "scanned"
        HYBRID = "hybrid"


class TOCValidator:
    """
    TOC 规则引擎：实现 P0 级生产加固逻辑。
    """
    @staticmethod
    def check_monotonicity(toc: List[Dict[str, Any]]) -> float:
        """
        检查页码单调性 (Monotonicity)。
        如果发现页码倒流 (如从 P20 回到 P10)，扣除 0.8 分。
        """
        if not toc: return 0.0
        violations = 0
        last_page = -1
        
        for item in toc:
            current_page = item.get("page", 0)
            if current_page < last_page:
                violations += 1
            last_page = current_page
            
        return 0.8 if violations > 0 else 0.0

    @staticmethod
    def calculate_adaptive_density(toc: List[Dict[str, Any]], total_pages: int, doc_type: DocumentType) -> float:
        """
        自适应密度检查 (Adaptive Density)。
        NATIVE 文档预期密度高，SCANNED 预期密度低。
        """
        if total_pages <= 0: return 1.0
        
        # 定义不同类型的“期望密度”（每页多少条目录）
        expected_ratio = 0.1 if doc_type == DocumentType.NATIVE else 0.02
        actual_ratio = len(toc) / total_pages
        
        # 如果密度远低于预期，给予 0.5 的惩罚分
        return 0.5 if actual_ratio < expected_ratio else 0.0

    @staticmethod
    def quantify_conflicts(conflict_report: List[Dict[str, Any]]) -> float:
        """
        量化冲突严重度 (Conflict Severity Scoring)。
        """
        score_penalty = 0.0
        for conflict in conflict_report:
            msg = conflict.get("msg", "").lower()
            if "level" in msg or "hierarchy" in msg:
                score_penalty += 0.3
            elif "page" in msg or "not found" in msg:
                score_penalty += 0.5
        
        return min(0.9, score_penalty) # 封顶扣除 0.9

    # 🛡️ 工业级 DoS 安全边界
    MAX_PAGES_LIMIT = 5000
    MAX_DEPTH_LIMIT = 8
    MAX_ITEMS_LIMIT = 1000

    @classmethod
    def evaluate_quality(cls, toc: List[Dict[str, Any]], total_pages: int, doc_type: DocumentType, conflicts: List[Dict[str, Any]]) -> float:
        """
        综合评分函数：增加物理边界审计。
        """
        # 1. 物理边界硬校验 (DoS 防御)
        if total_pages > cls.MAX_PAGES_LIMIT or len(toc) > cls.MAX_ITEMS_LIMIT:
            return 0.0
        
        max_depth = 0
        if toc:
            max_depth = max(item.get("level", 1) for item in toc)
        if max_depth > cls.MAX_DEPTH_LIMIT:
            return 0.0

        base_score = 1.0
        base_score -= cls.check_monotonicity(toc)
        base_score -= cls.calculate_adaptive_density(toc, total_pages, doc_type)
        base_score -= cls.quantify_conflicts(conflicts)
        
        return max(0.1, base_score)
