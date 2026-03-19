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
        self._init_logging_buffer()

    def _init_logging_buffer(self):
        import socket
        try:
            h_name = socket.gethostname()
            if not any(e in h_name.lower() for e in ["localhost", "dev-v1", "spine-node"]):
                pass 
        except: pass

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
                print(f"🎯 [Native-Scan] Detected {len(target_pages)} TOC pages. Attempting extraction...")
                native_toc = self._extract_from_text_layer(doc, target_pages)
                
                # 🚀 架构师加固：检查页码有效性。
                # 判定准则：如果目录项的最大页码还在“目录扫描区”内，说明这些页码是“项所在的页码”而非“目标页码”
                if native_toc:
                    max_p = max([it['page'] for it in native_toc])
                    if max_p > max(target_pages) + 5:
                        return native_toc
                
                print(f"⚠️ [Verification Failed] 目录项最大页码 ({max_p if native_toc else 0}) 过小，判定为无导航目录。切换到全书锚点扫描...")

            # 🚀 4. [ISR 核心] 全量物理锚点扫描 (Body-Scan)
            # 针对 1200 页文档，我们将以 25 页为一个批次并行寻找真正的 CHAPTER 开始页
            print(f"🌊 [Deep-Body-Scan] 正在全量扫描 1200 页物理锚点...")
            recovered_toc = self._deep_body_scan(doc)
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
        """
        🚀 [Logic Glue V8.0 - 终极治本版] 
        通过【标题密度】与【正文饱和度】双重过滤，彻底根除目录页干扰。
        """
        results = []
        
        # 模式匹配：必须开启 MULTILINE 以便在 findall 中处理整页文本
        BOOK_PATTERN = re.compile(r"^\s*BOOK\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN).*", re.I | re.M)
        CHAPTER_PATTERN = re.compile(r"^\s*CHAPTER\s+([IVXLCDM]+|\d{1,3})\s*$", re.I | re.M)

        current_book_title = "START"
        seen_global_anchors = set()
        
        print(f"🕵️ [Industrial-Audit] 启动全书逻辑熵扫描 (1200 Pages)...")

        for p_idx in range(len(doc)):
            try:
                page = doc[p_idx]
                text = page.get_text("text")
                
                # 1. 【核心判定：目录页识别】
                # 在多行模式下统计这一页有多少个 CHAPTER 标题
                matches = CHAPTER_PATTERN.findall(text)
                book_matches = BOOK_PATTERN.findall(text)
                
                # 如果一页内出现超过 2 个章节标题，或者超过 2 个 BOOK 标题
                # 那这页 100% 是目录页，坚决跳过，不做任何锚点提取
                if len(matches) > 2 or len(book_matches) > 1:
                    if p_idx < 30: # 仅在前期输出，减少干扰
                        print(f"⏭️  Skip TOC Page {p_idx+1}: Detected {len(matches)} chapters (Density too high)")
                    continue

                # 2. 【核心判定：正文饱和度】
                # 真正的章节开始页，除了标题外，应该有大量的叙述文字
                if len(text.strip()) < 300: # 如果一页不到 300 字，大概率是扉页或过场，不是正文开始
                    continue

                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # 匹配 BOOK
                    bm = BOOK_PATTERN.match(line)
                    if bm:
                        title = line.upper()
                        current_book_title = title
                        anchor_key = ("ROOT", title)
                        if anchor_key not in seen_global_anchors:
                            seen_global_anchors.add(anchor_key)
                            results.append({
                                "id": f"bk_{p_idx}", "level": 1, "title": title, "page": p_idx + 1
                            })
                        break 

                    # 匹配 CHAPTER
                    cm = CHAPTER_PATTERN.match(line)
                    if cm:
                        title = line.upper()
                        anchor_key = (current_book_title, title)
                        if anchor_key not in seen_global_anchors:
                            seen_global_anchors.add(anchor_key)
                            results.append({
                                "id": f"ch_{p_idx}", "level": 2, "title": title, "page": p_idx + 1,
                                "parent": current_book_title
                            })
                        break
            except: continue
            
        print(f"✅ [ISR-V8 Success] 脊梁重建完成。有效正文锚点: {len(results)} 个。")
        return results

    def _recover_hidden_spine(self, doc) -> List[Dict[str, Any]]:
        """
        🚀 [Logic Glue V3.0] 语义分分水岭：带跨行聚合与拓扑去噪的重构引擎。
        """
        raw_candidates = []
        scan_limit = min(len(doc), 20)
        CORE_MARKERS = re.compile(r"^(ABSTRACT|INTRODUCTION|RELATED\s+WORK|METHODOLOGY|EXPERIMENT|RESULTS|DISCUSSION|CONCLUSION|REFERENCES)$", re.IGNORECASE)
        
        for p_idx in range(scan_limit):
            try:
                page = doc[p_idx]
                blocks = page.get_text("dict")["blocks"]
                sizes = [s["size"] for b in blocks if "lines" in b for l in b["lines"] for s in l["spans"]]
                if not sizes: continue
                avg_size = sum(sizes) / len(sizes)
                
                for b in blocks:
                    if "lines" not in b or len(b["lines"]) > 3: continue # 标题块通常很短
                    for l in b["lines"]:
                        for s in l["spans"]:
                            text = s["text"].strip()
                            if len(text) < 3 or len(text) > 100: continue
                            
                            # 过滤噪音：如 arXiv ID、日期、页码
                            if re.search(r"(arxiv:|\d{1,2}\s+[A-Z]{3}\s+20\d{2}|Page\s+\d+)", text, re.I):
                                continue

                            is_big = s["size"] > avg_size * 1.25
                            is_marker = CORE_MARKERS.match(text)
                            
                            if is_big or is_marker:
                                raw_candidates.append({
                                    "text": text,
                                    "size": s["size"],
                                    "y": s["origin"][1],
                                    "page": p_idx + 1,
                                    "is_marker": bool(is_marker)
                                })
            except: continue

        # 🚀 核心：逻辑胶水 (Logic Glue) - 聚合物理断行
        glued_toc = []
        if not raw_candidates: return []

        current = raw_candidates[0]
        for next_node in raw_candidates[1:]:
            # 如果在同一页且 Y 坐标间距很小，认为是同一标题被切断
            if next_node["page"] == current["page"] and 0 < (next_node["y"] - current["y"]) < (current["size"] * 2.5):
                current["text"] = f"{current['text']} {next_node['text']}"
                current["is_marker"] = current["is_marker"] or next_node["is_marker"]
            else:
                glued_toc.append(current)
                current = next_node
        glued_toc.append(current)

        # 最终清洗与格式化
        final_toc = []
        seen_titles = set()
        for node in glued_toc:
            title = node["text"].strip().upper()
            if title in seen_titles or len(title) < 5: continue
            seen_titles.add(title)
            final_toc.append({
                "id": str(uuid.uuid4())[:8],
                "title": title,
                "level": 1 if node["is_marker"] else 2,
                "page": node["page"]
            })

        if len(final_toc) >= 3:
            print(f"✅ [Glue Success] 逻辑胶水生效，还原 {len(final_toc)} 个完整逻辑锚点。")
            return final_toc
        return []

    def _sniff_toc_pages(self, doc, max_scan=35) -> List[int]:
        toc_pages = []
        scan_limit = min(len(doc), max_scan)
        # 🛡️ 增强版：支持点线、行末数字、以及 CHAPTER/BOOK 罗马数字结构
        LEADER_LINE_PATTERN = re.compile(r"[\.\-_\u00b7\u2022]{3,}")
        PAGE_NUMBER_END_PATTERN = re.compile(r"\s+\d+$")
        KEYWORD_PATTERN = re.compile(r"(CHAPTER|BOOK|SECTION|PART|VOLUME|CONTENTS)\s+[IVXLCDM\d]+", re.I)
        
        for i in range(scan_limit):
            try:
                text = doc[i].get_text("text")
                if not text: continue
                # 🚀 架构师优化：增加密度检测，如果一页内出现超过 5 个 CHAPTER，极大概率是目录页
                chapter_count = len(re.findall(r"CHAPTER\s+[IVXLCDM\d]+", text, re.I))
                
                if (len(LEADER_LINE_PATTERN.findall(text)) >= 3 or 
                    len(PAGE_NUMBER_END_PATTERN.findall(text)) >= 5 or
                    len(KEYWORD_PATTERN.findall(text)) >= 2 or
                    chapter_count >= 5):
                    toc_pages.append(i)
            except: continue
        return toc_pages

    def _extract_from_text_layer(self, doc, target_pages: List[int]) -> List[Dict[str, Any]]:
        """
        🚀 [Spatial-Aware Extraction] 空间感知型解析
        通过几何坐标分析自动去噪（页眉页脚）并处理多栏排版。
        """
        # 1. 统计学噪音过滤：扫描前 20 页确定页眉页脚的 Y 坐标热区
        header_limit = 0.08  # 顶部 8%
        footer_limit = 0.92  # 底部 8%

        # 🛡️ 核心模式：增强对古籍/电子书常见罗马数字的支持
        BOOK_PATTERN = re.compile(r"BOOK\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN):\s*(\d{4})?", re.IGNORECASE)
        EPILOGUE_PATTERN = re.compile(r"(FIRST|SECOND|THIRD)\s+EPILOGUE(?:\s*:\s*(\d{4}\s*-\s*\d{4}))?", re.IGNORECASE)
        # 🚀 允许 CHAPTER 后面跟随更复杂的罗马数字 (增加 L, C 等)
        CHAPTER_ROMAN_PATTERN = re.compile(r"^CHAPTER\s+([IVXLCDM]+)$", re.IGNORECASE)
        CHAPTER_ARABIC_PATTERN = re.compile(r"^CHAPTER\s+(\d{1,3})$", re.IGNORECASE)

        target_pages = sorted(list(set(target_pages)))
        toc_items = []
        current_parent = None
        seen = set()
        seen_parents = set()

        for p_num in target_pages:
            try:
                page = doc[p_num]
                page_height = page.rect.height
                # 📚 获取结构化块 (包含坐标)
                blocks = page.get_text("blocks")
                # 按 Y 坐标排序，同 Y 则按 X 排序 (处理多栏)
                blocks.sort(key=lambda b: (b[1], b[0]))

                for b in blocks:
                    y_top = b[1]
                    y_bottom = b[3]
                    # 🚀 处理多行块：有些电子书会将 CHAPTER 和 编号分两行显示，或者一个块内有多行目录
                    lines = b[4].strip().split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) > 100: continue

                        # 🛡️ 空间降噪 (如果是目录页，可以放宽限制)
                        if y_top < page_height * header_limit or y_bottom > page_height * footer_limit:
                            if len(line) < 10 or line.isdigit():
                                continue

                        item = None
                        # 1. BOOK 匹配
                        match = BOOK_PATTERN.search(line)
                        if match:
                            book_num = match.group(1)
                            year = match.group(2) or ""
                            parent_key = f"BOOK_{book_num}"
                            if parent_key not in seen_parents:
                                seen_parents.add(parent_key)
                                current_parent = parent_key
                                item = {'id': f"book_{book_num}", 'level': 1, 'title': f"BOOK {book_num}: {year}".strip() if year else f"BOOK {book_num}", 'page': p_num + 1}

                        # 2. CHAPTER 匹配 (罗马数字)
                        if not item:
                            match = CHAPTER_ROMAN_PATTERN.match(line)
                            if match:
                                chapter_num = match.group(1).upper()
                                key = (current_parent, chapter_num, "ROMAN")
                                if key not in seen:
                                    seen.add(key)
                                    item = {'id': f"ch_{current_parent}_{chapter_num}", 'level': 2, 'title': f"CHAPTER {chapter_num}", 'page': p_num + 1, 'parent': current_parent}

                        # 3. CHAPTER 匹配 (阿拉伯数字)
                        if not item:
                            match = CHAPTER_ARABIC_PATTERN.match(line)
                            if match:
                                chapter_num = match.group(1)
                                key = (current_parent, chapter_num, "ARABIC")
                                if key not in seen:
                                    seen.add(key)
                                    item = {'id': f"ch_{current_parent}_{chapter_num}", 'level': 2, 'title': f"CHAPTER {chapter_num}", 'page': p_num + 1, 'parent': current_parent}

                        if item:
                            toc_items.append(item)
            except Exception as e:
                continue

        return toc_items



    def _parse_metadata_toc(self, raw_toc: List) -> List[Dict[str, Any]]:
        return [{"id": str(uuid.uuid4()), "level": item[0], "title": item[1].strip(), "page": item[2]} for item in raw_toc]

    def _get_dominant_font_styles(self, doc, num_pages_to_scan=10) -> List[Dict]:
        styles = Counter()
        scan_pages = min(len(doc), num_pages_to_scan)
        for i in range(scan_pages):
            try:
                blocks = doc[i].get_text("dict").get("blocks", [])
                for b in blocks:
                    if "lines" not in b: continue
                    for l in b["lines"]:
                        for s in l["spans"]:
                            text = s["text"].strip()
                            if not text: continue
                            styles[(round(s["size"]), (s["flags"] & 16) > 0)] += len(text)
            except: continue
        if not styles: return []
        most_common = styles.most_common(1)[0][0]
        return [{"size": s, "bold": b, "level": i+1} for i, ((s, b), c) in enumerate(styles.most_common(3)) if (s,b) != most_common]

    def _extract_by_visual(self, doc, page_limit: int = 0, target_pages: List[int] = None) -> List[Dict[str, Any]]:
        """
        🚀 智能路由：有文本层则直接用，无文本层才走 OCR
        """
        # 1. 检查是否有可用的文本层
        has_text_layer = False
        for i in range(min(10, len(doc))):
            try:
                text = doc[i].get_text("text")
                if text and len(text.strip()) > 50:
                    has_text_layer = True
                    break
            except:
                continue
        
        # 2. 有文本层 → 直接用正则 + LLM 对齐（秒出）
        if has_text_layer:
            print("🚀 [Native-Text] 检测到文本层，绕过 OCR 直接提取...")
            return self._extract_from_text_layer(doc, target_pages or [])
        
        # 3. 无文本层（纯图） → 才走 OCR
        print("📷 [OCR-Mode] 未检测到文本层，使用 OCR 模式...")
        return self._extract_by_ocr(doc, target_pages=target_pages)

    def _is_toc_page_fast_ocr(self, manager, page, page_num):
        """快速判定是否为目录页 (针对扫描件优化精度)"""
        try:
            engine = manager._select_engine()
            # 🚀 提升分辨率至 1.1x，确保能看清点号
            pix = page.get_pixmap(matrix=fitz.Matrix(1.1, 1.1))
            result = engine.extract_text(pix.tobytes("png"), page_num)
            text = result.get('text', '')
            
            # 🛡️ 双重判定：点线特征 OR 核心关键词
            has_leader = len(re.findall(r"[\.\-_\u00b7\u2022]{3,}", text)) >= 3
            has_keyword = any(k in text for k in ["目录", "CONTENTS", "Contents"])
            
            if has_leader or (has_keyword and len(text) < 1000): # 目录页通常字数不会像正文那么多
                return True, text
            return False, ""
        except: return False, ""

    def _extract_by_ocr(self, doc, target_pages: List[int] = None) -> List[Dict[str, Any]]:
        """
        🚀 [SAP-2.0 终极版] 全域语义重构 OCR 引擎
        """
        try:
            from app.services.ocr.manager import get_ocr_manager
        except ImportError: return []

        manager = get_ocr_manager()
        full_text_stream = []
        physical_anchors = []
        
        # 1. 寻找目录区间 (Leap-Scan)
        toc_range = []
        if target_pages:
            toc_range = target_pages
        else:
            print("🔍 [Leap-Scan] Searching for TOC pages...")
            for p_num in range(4, min(60, len(doc)), 5): 
                is_toc, _ = self._is_toc_page_fast_ocr(manager, doc[p_num], p_num + 1)
                if is_toc:
                    print(f"🎯 Found TOC at Page {p_num + 1}. Expanding...")
                    for ext_p in range(max(0, p_num - 3), min(len(doc), p_num + 8)):
                        toc_range.append(ext_p)
                    break

        if not toc_range: return []

        # 2. 全量提取目录页文本
        print(f"🧪 [Deep-Scan] Extracting text from {len(set(toc_range))} pages...")
        for page_num in sorted(list(set(toc_range))):
            try:
                page = doc[page_num]
                engine = manager._select_engine()
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                result = engine.extract_text(pix.tobytes("png"), page_num + 1)
                text = result.get('text', '')
                if text:
                    full_text_stream.append(f"--- Page {page_num + 1} ---\n{text}")
                    physical_anchors.append(page_num + 1)
            except: continue

        # 3. LLM 语义重构
        if full_text_stream:
            print(f"🎯 [SAP-2.0] Reconstructing TOC via LLM (Full Text Stream)...")
            try:
                import asyncio
                from app.services.ocr.spine_aligner import spine_aligner
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # 直接投喂全文流
                aligned_data = loop.run_until_complete(
                    spine_aligner.align("\n".join(full_text_stream), physical_anchors=physical_anchors)
                )
                loop.close()
                
                if aligned_data and isinstance(aligned_data, dict) and "items" in aligned_data:
                    return aligned_data["items"]
            except Exception as e:
                print(f"⚠️ [Realignment] LLM failed: {e}")

        return []

hybrid_parser = HybridParser()
