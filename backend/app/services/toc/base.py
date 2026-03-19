"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class TOCStrategy(ABC):
    """
    TOC 策略抽象基类，用于依赖注入。
    """
    @abstractmethod
    def process(self, raw_items: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理原始目录项并返回增强后的结果。
        
        Args:
            raw_items: 来自 Parser/OCR 的原始数据。
            context: 冲突日志容器。
        """
        pass
