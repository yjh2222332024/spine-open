import os
import sys
import json
import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich import print as rprint

# --- 🚀 路径注入 ---
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from app.services.parser import hybrid_parser
    from app.services.rag.splitter import context_splitter
    from app.core.config import settings
except ImportError as e:
    rprint(f"[bold red]核心模块导入错误:[/bold red] {e}")
    sys.exit(1)

# --- 向量库适配器 (带精准诊断) ---

LANCEDB_AVAILABLE = False
IMPORT_ERROR_MSG = ""

try:
    import lancedb
    import pyarrow as pa
    from sentence_transformers import SentenceTransformer
    LANCEDB_AVAILABLE = True
except ImportError as e:
    IMPORT_ERROR_MSG = str(e)
    LANCEDB_AVAILABLE = False

class LocalVectorStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.table_name = "doc_chunks"
        self._db = None
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        return self._model

    def _get_db(self):
        if not LANCEDB_AVAILABLE: return None
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
        table = self._ensure_table()
        if not table: return
        texts = [c["content"] for c in chunks]
        embeddings = self.model.encode(texts)
        data = []
        for i, c in enumerate(chunks):
            data.append({
                "vector": embeddings[i],
                "text": c["content"],
                "doc_id": doc_id,
                "page": c["metadata"]["page_start"],
                "breadcrumb": c["metadata"].get("breadcrumb", "未知章节")
            })
        table.add(data)

    def search(self, query: str, doc_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        db = self._get_db()
        if not db or self.table_name not in db.table_names(): return []
        table = db.open_table(self.table_name)
        query_vec = self.model.encode([query])[0]
        query_builder = table.search(query_vec).limit(limit)
        if doc_id:
            query_builder = query_builder.where(f"doc_id = '{doc_id}'")
        return query_builder.to_list()

# --- 核心引擎 (Trident Core) ---

class SpineCore:
    def __init__(self, storage_dir: str = ".spine"):
        self.storage_dir = Path(storage_dir)
        self.metadata_file = self.storage_dir / "metadata.json"
        self.vector_store = LocalVectorStore(self.storage_dir / "lancedb")
        self._ensure_storage()

    def _ensure_storage(self):
        if not self.storage_dir.exists():
            self.storage_dir.mkdir(parents=True)
        if not self.metadata_file.exists():
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump({"documents": {}}, f)

    def _load_metadata(self) -> Dict:
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_metadata(self, data: Dict):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def ingest(self, file_path: str, progress_callback=None) -> str:
        p = Path(file_path)
        doc_id = f"doc_{p.stem}"
        if progress_callback: progress_callback("正在重建逻辑脊梁 (ISR)...")
        toc_items = hybrid_parser.extract_toc(str(p))
        if progress_callback: progress_callback("正在执行上下文感知切片...")
        import fitz
        with fitz.open(file_path) as pdf:
            total_pages = len(pdf)
            chunks = context_splitter.split_by_toc(pdf, toc_items)
        if LANCEDB_AVAILABLE:
            if progress_callback: progress_callback(f"正在向量化 {len(chunks)} 个片段...")
            await self.vector_store.add_documents(doc_id, chunks)
        meta = self._load_metadata()
        meta["documents"][doc_id] = {
            "id": doc_id, "filename": p.name, "path": str(p.absolute()),
            "total_pages": total_pages, "toc": toc_items,
            "chunk_count": len(chunks), "ingested_at": datetime.now().isoformat(),
            "vectorized": LANCEDB_AVAILABLE
        }
        self._save_metadata(meta)
        return doc_id

    def fetch_all_docs(self):
        return list(self._load_metadata()["documents"].values())

    def get_document(self, doc_id: str):
        return self._load_metadata()["documents"].get(doc_id)

# --- CLI ---

app = typer.Typer(help="阅脊 (SpineDoc) 极客版 CLI", add_completion=False)
console = Console()
core = SpineCore()

@app.command()
def ingest(file_path: str):
    """📥 导入文档、重建脊梁。"""
    if not os.path.exists(file_path):
        console.print(f"[red]文件不存在: {file_path}[/red]")
        return
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), MofNCompleteColumn(), transient=True) as progress:
        task = progress.add_task(description="启动引擎...", total=None)
        def update_msg(msg): progress.update(task, description=msg)
        doc_id = asyncio.run(core.ingest(file_path, progress_callback=update_msg))
    console.print(Panel(f"✅ [bold green]导入成功![/bold green]\nID: [bold cyan]{doc_id}[/bold cyan]", title="SpineDoc", border_style="green"))

@app.command(name="list")
def list_cmd():
    """📋 列出已解析文档。"""
    docs = core.fetch_all_docs()
    table = Table(title="SpineDoc 索引库")
    table.add_column("ID", style="cyan"); table.add_column("文件名"); table.add_column("页数", justify="right"); table.add_column("向量化", style="magenta")
    for d in docs:
        table.add_row(d["id"], d["filename"], str(d["total_pages"]), "✅" if d.get("vectorized") else "❌")
    console.print(table)

@app.command()
def tree(doc_id: str):
    """🌳 展示文档逻辑树。"""
    doc = core.get_document(doc_id)
    if not doc: return console.print("[red]未找到文档[/red]")
    spine_tree = Tree(f"[bold blue]📄 {doc['filename']}[/bold blue]")
    for item in doc["toc"]:
        spine_tree.add(f"[bold green]{item['title']}[/bold green] [dim](P{item['page']})[/dim]")
    console.print(spine_tree)

@app.command()
def ask(query: str, doc_id: str = typer.Option(None, "--doc", "-d"), limit: int = typer.Option(5, "--limit", "-l")):
    """🧠 逻辑感知问答。"""
    if not LANCEDB_AVAILABLE:
        console.print(f"[bold red]语义检索不可用:[/bold red] 无法加载依赖库。\n[yellow]错误详情: {IMPORT_ERROR_MSG}[/yellow]")
        console.print(f"[dim]当前 Python: {sys.executable}[/dim]")
        return

    with console.status(f"[bold cyan]正在执行语义检索..."):
        results = core.vector_store.search(query, doc_id=doc_id, limit=limit)
    
    if not results: return console.print("[yellow]未找到内容。请确保已 ingest。[/yellow]")

    rprint("\n[bold]📍 逻辑定位与证据溯源:[/bold]")
    for i, res in enumerate(results):
        rprint(f"  • [cyan][{i+1}] {res['breadcrumb']}[/cyan] [dim](P{res['page']}, Score: {res['_distance']:.4f})[/dim]")

    if settings.LLM_API_KEY:
        console.print(f"\n[bold green]AI 回答:[/bold green] ", end="")
        context = "\n\n".join([f"章节: {r['breadcrumb']}\n{r['text']}" for r in results])
        sys_prompt = f"你是一个阅脊助手。请基于参考片段回答，注明章节名。\n\n{context}"
        async def chat():
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
            stream = await client.chat.completions.create(model=settings.LLM_MODEL_NAME, messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}], stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
        asyncio.run(chat())
        print("\n")

if __name__ == "__main__":
    app()
