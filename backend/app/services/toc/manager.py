"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
from .base import TOCStrategy
import uuid

class TOCManager:
    """
    TOC 合成管理器：负责多源数据合并、层级重建与冲突检测。
    支持策略注入以提高可测试性。
    """
    def __init__(self, strategies: List[TOCStrategy] = None):
        self.strategies = strategies or []
        self.conflict_report = []

    def build_tree(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行策略链条并组装树形结构。
        """
        # 防御性编程：确保只处理字典对象，过滤掉可能误入的嵌套列表或其他类型
        processed_items = [item for item in raw_items if isinstance(item, dict)]
        
        # 1. 运行所有策略 (正则匹配、字体聚类等)
        for strategy in self.strategies:
            context = {"conflicts": self.conflict_report}
            processed_items = strategy.process(processed_items, context)

        # 2. 物理排序 (按页码)
        processed_items.sort(key=lambda x: x.get("page", 0))

        # 3. 建立父子关系 (Stack-based algorithm)
        return self._link_nodes(processed_items)

    def _link_nodes(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        核心算法：根据 level 分配 parent_id。
        """
        stack = []
        structured_toc = []

        for item in items:
            level = item.get("level", 1)
            
            # 弹出栈中比当前级别深的节点
            while stack and stack[-1]["level"] >= level:
                stack.pop()

            # 如果栈不为空，前一个节点就是父节点
            if stack:
                item["parent_id"] = stack[-1]["id"]
            else:
                item["parent_id"] = None

            # 入栈作为后续节点的潜在父节点
            stack.append(item)
            structured_toc.append(item)

        return structured_toc

    def get_conflict_report(self) -> List[Dict[str, Any]]:
        """返回合并过程中的预警信息"""
        return self.conflict_report
