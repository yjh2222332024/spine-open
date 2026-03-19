"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
import fitz
from typing import List, Dict, Any
from uuid import UUID
import re

class ContextAwareSplitter:
    """
    上下文感知切片器 (The Context-Aware Splitter)
    
    职责：
    1. 结合 PDF 目录 (TOC) 将文档划分为物理章节。
    2. 在章节内部进行细粒度切片。
    3. 为每个 Chunk 注入章节路径和元数据，增强检索时的语义理解。
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size (int): 每个文本块的最大字符数。
            chunk_overlap (int): 相邻文本块之间的重叠字符数，用于保持语义连续性。
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_by_toc(self, doc: fitz.Document, toc: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据目录结构对 PDF 进行切片。
        
        Args:
            doc (fitz.Document): PyMuPDF 文档对象。
            toc (List[Dict]): 包含 id, title, page, level 的目录列表。
            
        Returns:
            List[Dict]: 增强后的切片列表。每个切片包含 content 和 metadata。
        """
        if not toc:
            # 如果没有目录，退化为普通的全文档切片
            return self._fallback_split(doc)

        all_chunks = []
        num_items = len(toc)
        total_pages = len(doc)
        
        # 维护一个栈来追踪当前的层级路径 (Breadcrumb)
        # 栈元素: TOC Item Dict
        hierarchy_stack = []

        for i, item in enumerate(toc):
            # 0. 维护层级栈 (Breadcrumb Logic)
            current_level = item.get("level", 1)
            
            # 当遇到同级或更高级别(数字更小或相等)的节点时，弹出栈顶
            # 假设 TOC 是按顺序遍历的 (DFS Order)
            while hierarchy_stack and hierarchy_stack[-1].get("level", 1) >= current_level:
                hierarchy_stack.pop()
            
            hierarchy_stack.append(item)
            
            # 构建面包屑路径字符串，例如 "第一章 > 第一节"
            breadcrumb = " > ".join([node["title"] for node in hierarchy_stack])

            # 1. 计算当前章节的页码范围
            start_page = max(0, item["page"] - 1) # fitz 是 0-based
            
            # 结束页码是下一章的起始页码 - 1；如果是最后一章，则直到文档末尾
            if i < num_items - 1:
                # 确保 end_page 至少比 start_page 大，避免 range 为空
                # 注意：如果下一章和当前章在同一页，这里会取 start_page + 1，即读取当前这一页
                next_start_page = toc[i+1]["page"] - 1
                end_page = max(start_page + 1, next_start_page)
            else:
                end_page = total_pages

            # 2. 提取该页码范围内的所有文本
            chapter_text = ""
            for p_idx in range(start_page, end_page):
                # 提示：未来这里可以优化，通过坐标排除页眉页脚
                if p_idx < total_pages:
                    page_text = doc[p_idx].get_text("text")
                    chapter_text += page_text + "\n"

            # 3. 清洗文本 (去除多余空白等)
            chapter_text = self._clean_text(chapter_text)

            # 4. 在章节内部进行物理切分
            # 注入完整的面包屑路径作为 Context
            sub_chunks = self._sliding_window_split(
                text=chapter_text, 
                prefix=f"[Context: {breadcrumb}] "
            )

            # 5. 组装结果
            for content in sub_chunks:
                all_chunks.append({
                    "content": content,
                    "metadata": {
                        "toc_item_id": item["id"],
                        "title": item["title"],
                        "level": item["level"],
                        "breadcrumb": breadcrumb,
                        "page_start": start_page + 1,
                        "page_end": end_page
                    }
                })

        return all_chunks

    def _sliding_window_split(self, text: str, prefix: str = "") -> List[str]:
        """
        滑动窗口切分算法。
        """
        chunks = []
        effective_chunk_size = self.chunk_size - len(prefix)
        
        if len(text) <= effective_chunk_size:
            return [prefix + text]

        start = 0
        while start < len(text):
            end = start + effective_chunk_size
            chunk = text[start:end]
            chunks.append(prefix + chunk)
            start += (effective_chunk_size - self.chunk_overlap)
            
        return chunks

    def _clean_text(self, text: str) -> str:
        """
        基础文本清洗。
        """
        # 替换多个换行为两个（保持段落感）
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 移除不可见字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    def _fallback_split(self, doc: fitz.Document) -> List[Dict[str, Any]]:
        """
        当没有目录时的兜底方案：全文档滑动窗口切分。
        """
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        
        cleaned_text = self._clean_text(full_text)
        sub_chunks = self._sliding_window_split(cleaned_text, prefix="[未分类章节] ")
        
        return [
            {"content": c, "metadata": {"toc_item_id": None, "title": "无目录", "level": 0}}
            for c in sub_chunks
        ]

# 导出单例
context_splitter = ContextAwareSplitter()
