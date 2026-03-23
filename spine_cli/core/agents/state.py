from typing import List, Dict, Any, Optional, TypedDict
from enum import Enum

class DocumentType(str, Enum):
    NATIVE = "native"
    SCANNED = "scanned"
    HYBRID = "hybrid"

class PageInfo(TypedDict):
    page_num: int
    text_content: Optional[str]
    has_text_layer: bool
    ocr_result: Optional[Dict[str, Any]]

class TocItem(TypedDict):
    id: str
    level: int
    title: str
    page: int
    parent_id: Optional[str]
    confidence: float

class DocumentState(TypedDict):
    file_path: str
    document_type: Optional[DocumentType]
    total_pages: int
    pages: List[PageInfo]
    raw_toc: Optional[List[Dict[str, Any]]]
    structured_toc: List[TocItem]
    processing_errors: List[str]
    confidence_score: float
    current_node: Optional[str]
    instructions: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    metadata: Dict[str, Any]
