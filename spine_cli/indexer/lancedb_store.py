import pyarrow as pa
from typing import List, Dict, Optional
from pathlib import Path
from rich import print as rprint

try:
    import lancedb
    from sentence_transformers import SentenceTransformer
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False

class LanceDBStore:
    """独立的 LanceDB 向量存储实现"""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.table_name = "doc_chunks"
        self._db = None
        self._model = None
        self.is_available = LANCEDB_AVAILABLE

    @property
    def model(self):
        if not self.is_available: return None
        if self._model is None:
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        return self._model

    def _get_db(self):
        if not self.is_available: return None
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _ensure_table(self):
        db = self._get_db()
        if not db: return None
        if self.table_name not in db.table_names():
            schema = pa.schema([
                pa.field("vector", pa.list_(pa.float32(), 384)),
                pa.field("text", pa.string()),
                pa.field("doc_id", pa.string()),
                pa.field("page", pa.int32()),
                pa.field("breadcrumb", pa.string())
            ])
            return db.create_table(self.table_name, schema=schema)
        return db.open_table(self.table_name)

    async def add_documents(self, doc_id: str, chunks: List[Dict]):
        if not self.is_available:
            raise RuntimeError("LanceDB environment is not available.")
            
        table = self._ensure_table()
        if not table or not self.model: return
        
        texts = [c["content"] for c in chunks]
        embeddings = self.model.encode(texts)
        
        data = []
        for i, c in enumerate(chunks):
            data.append({
                "vector": embeddings[i],
                "text": c["content"],
                "doc_id": doc_id,
                "page": c["metadata"].get("page_start", 0),
                "breadcrumb": c["metadata"].get("breadcrumb", "未知章节")
            })
        table.add(data)

    def search(self, query: str, doc_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        if not self.is_available:
            return []
            
        db = self._get_db()
        if not db or not self.model or self.table_name not in db.table_names(): return []
        
        table = db.open_table(self.table_name)
        query_vec = self.model.encode([query])[0]
        
        query_builder = table.search(query_vec).limit(limit)
        if doc_id:
            query_builder = query_builder.where(f"doc_id = '{doc_id}'")
            
        return query_builder.to_list()
