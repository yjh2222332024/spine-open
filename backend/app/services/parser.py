import fitz
from typing import List, Dict, Any
import os
import uuid
from collections import Counter
import re

class HybridParser:
    # 🛡️ P0 安全边界定义
    MAX_PAGES = 2000
    MAX_TOC_DEPTH = 5
    MAX_TOC_ITEMS = 3000

    def __init__(self):
        pass

    def extract_toc(self, file_path: str, limit_pages: int = 0) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 文件未找到: {file_path}")
        doc = None
        try:
            doc = fitz.open(file_path)
            if len(doc) > self.MAX_PAGES:
                return []

            # 🛡️ 1. 扫描件探测
            is_scanned = True
            text_sample = ""
            for i in range(min(5, len(doc))):
                text_sample += doc[i].get_text("text").strip()
                if len(text_sample) > 100:
                    is_scanned = False
                    break
            
            if is_scanned:
                return [{"id": "SCANNED_PDF_DETECTED", "title": "SCANNED_PDF_DETECTED", "level": 0, "page": 0}]

            # 2. 优先 Metadata
            raw_toc = doc.get_toc(simple=True)
            if raw_toc and len(raw_toc) >= 6:
                return self._parse_metadata_toc(raw_toc)
            
            # 3. 文本层嗅探 (目录页)
            target_pages = self._sniff_toc_pages(doc, max_scan=limit_pages or 45)
            
            if target_pages:
                native_toc = self._extract_from_text_layer(doc, target_pages)
                if native_toc:
                    max_p = max([it['page'] for it in native_toc])
                    if max_p > max(target_pages) + 2:
                        return native_toc

            # 🚀 4. [ISR 核心] 全量物理锚点扫描
            print(f"🌊 [Deep-Scan] 正在尝试逻辑脊梁重建...")
            recovered_toc = self._deep_body_scan(doc)
            
            # 🚀 [架构师补丁]：针对学术论文/短文档，如果 Body-Scan 失败，启用逻辑胶水
            if not recovered_toc or len(recovered_toc) < 3:
                print(f"🧬 [Logic-Glue-Trigger] 切换至学术语义分水岭模式...")
                recovered_toc = self._recover_hidden_spine(doc)
            
            if recovered_toc:
                return recovered_toc

            # 5. 兜底
            return self._extract_by_visual(doc, page_limit=limit_pages, target_pages=target_pages)
            
        except Exception as e:
            print(f"解析错误: {str(e)}")
            return []
        finally:
            if doc: doc.close()

    def _deep_body_scan(self, doc) -> List[Dict[str, Any]]:
        results = []
        BOOK_PATTERN = re.compile(r"^\s*BOOK\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN).*", re.I | re.M)
        CHAPTER_PATTERN = re.compile(r"^\s*CHAPTER\s+([IVXLCDM]+|\d{1,3})\s*$", re.I | re.M)

        current_book_title = "START"
        seen_global_anchors = set()
        
        for p_idx in range(len(doc)):
            try:
                page = doc[p_idx]
                text = page.get_text("text")
                matches = CHAPTER_PATTERN.findall(text)
                if len(matches) > 2: continue
                if len(text.strip()) < 300: continue

                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    bm = BOOK_PATTERN.match(line)
                    if bm:
                        title = line.upper()
                        current_book_title = title
                        if title not in seen_global_anchors:
                            seen_global_anchors.add(title)
                            results.append({"id": f"bk_{p_idx}", "level": 1, "title": title, "page": p_idx + 1})
                        break 
                    cm = CHAPTER_PATTERN.match(line)
                    if cm:
                        title = line.upper()
                        anchor_key = f"{current_book_title}_{title}"
                        if anchor_key not in seen_global_anchors:
                            seen_global_anchors.add(anchor_key)
                            results.append({"id": f"ch_{p_idx}", "level": 2, "title": title, "page": p_idx + 1})
                        break
            except: continue
        return results

    def _recover_hidden_spine(self, doc) -> List[Dict[str, Any]]:
        """
        🚀 [Logic Glue V3.1] 针对学术论文优化的语义引擎
        """
        raw_candidates = []
        scan_limit = min(len(doc), 30)
        # 增强正则表达式：支持 "1. Introduction", "I. Methodology", "Abstract" 等
        ACADEMIC_PATTERN = re.compile(r"^(\d+\.?\s+|[IVXLCDM]+\.\s+)?(ABSTRACT|INTRODUCTION|RELATED\s+WORK|METHODOLOGY|EXPERIMENT|RESULTS|DISCUSSION|CONCLUSION|REFERENCES|SYSTEM\s+DESIGN|IMPLEMENTATION|EVALUATION|CONCLUSION).*$", re.IGNORECASE)
        
        for p_idx in range(scan_limit):
            try:
                page = doc[p_idx]
                blocks = page.get_text("dict")["blocks"]
                all_sizes = []
                for b in blocks:
                    if "lines" in b:
                        for l in b["lines"]:
                            for s in l["spans"]:
                                all_sizes.append(s["size"])
                
                if not all_sizes: continue
                avg_size = sum(all_sizes) / len(all_sizes)
                
                for b in blocks:
                    if "lines" not in b or len(b["lines"]) > 5: continue
                    for l in b["lines"]:
                        for s in l["spans"]:
                            text = s["text"].strip()
                            if len(text) < 3 or len(text) > 120: continue
                            
                            is_big = s["size"] > avg_size * 1.15
                            is_match = ACADEMIC_PATTERN.match(text)
                            
                            if is_match or (is_big and text.isupper()):
                                raw_candidates.append({
                                    "text": text,
                                    "size": s["size"],
                                    "y": s["origin"][1],
                                    "page": p_idx + 1,
                                    "is_academic": bool(is_match)
                                })
            except: continue

        glued_toc = []
        if not raw_candidates: return []

        current = raw_candidates[0]
        for next_node in raw_candidates[1:]:
            if next_node["page"] == current["page"] and 0 < (next_node["y"] - current["y"]) < (current["size"] * 2.0):
                current["text"] = f"{current['text']} {next_node['text']}"
            else:
                glued_toc.append(current)
                current = next_node
        glued_toc.append(current)

        final_toc = []
        seen_titles = set()
        for node in glued_toc:
            title = node["text"].strip()
            if title.upper() in seen_titles or len(title) < 4: continue
            seen_titles.add(title.upper())
            final_toc.append({
                "id": f"ac_{node['page']}_{str(uuid.uuid4())[:4]}",
                "title": title,
                "level": 1 if node["is_academic"] else 2,
                "page": node["page"]
            })
        return final_toc

    def _sniff_toc_pages(self, doc, max_scan=35) -> List[int]:
        toc_pages = []
        scan_limit = min(len(doc), max_scan)
        LEADER_LINE_PATTERN = re.compile(r"[\.\-_\u00b7\u2022]{3,}")
        PAGE_NUMBER_END_PATTERN = re.compile(r"\s+\d+$")
        
        for i in range(scan_limit):
            try:
                text = doc[i].get_text("text")
                if not text: continue
                if (len(LEADER_LINE_PATTERN.findall(text)) >= 3 or 
                    len(PAGE_NUMBER_END_PATTERN.findall(text)) >= 5):
                    toc_pages.append(i)
            except: continue
        return toc_pages

    def _extract_from_text_layer(self, doc, target_pages: List[int]) -> List[Dict[str, Any]]:
        toc_items = []
        BOOK_PATTERN = re.compile(r"BOOK\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)", re.IGNORECASE)
        CHAPTER_PATTERN = re.compile(r"CHAPTER\s+([IVXLCDM]+|\d{1,3})", re.IGNORECASE)
        
        for p_num in target_pages:
            try:
                text = doc[p_num].get_text("text")
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if BOOK_PATTERN.match(line):
                        toc_items.append({'id': f"bk_{p_num}", 'level': 1, 'title': line, 'page': p_num + 1})
                    elif CHAPTER_PATTERN.match(line):
                        toc_items.append({'id': f"ch_{p_num}", 'level': 2, 'title': line, 'page': p_num + 1})
            except: continue
        return toc_items

    def _parse_metadata_toc(self, raw_toc: List) -> List[Dict[str, Any]]:
        return [{"id": str(uuid.uuid4()), "level": item[0], "title": item[1].strip(), "page": item[2]} for item in raw_toc]

    def _extract_by_visual(self, doc, page_limit: int = 0, target_pages: List[int] = None) -> List[Dict[str, Any]]:
        # 开源版暂不实现 OCR 逻辑
        return []

hybrid_parser = HybridParser()
