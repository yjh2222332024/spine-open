# 🏛️ SpineDoc (阅脊) - The Semantic Logic Engine for Shell
# Copyright (c) 2026 Junhao Yan (严俊皓). All Rights Reserved.
# Licensed under MIT License. 
# "Stop chatting with PDFs. Start reconstructing their logic."

import asyncio
import typer
import os
import sys
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TaskID
from rich import print as rprint

from app.core.config import settings

app = typer.Typer(
    help="SpineDoc CLI - The Semantic Logic Engine for Shell",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich"
)
console = Console()

def get_engine():
    """延迟加载 Engine，并捕获因缺少 API_KEY 导致的初始化崩溃"""
    try:
        from spine_cli.core.engine import SpineEngine
        return SpineEngine()
    except Exception as e:
        if "api_key" in str(e).lower() or "OPENAI_API_KEY" in str(e):
            console.print("[bold red]⚠️ 架构师拦截: 引擎启动失败！[/bold red]")
            console.print("[yellow]原因: 未检测到大模型 API Key。[/yellow]")
            console.print("请在系统环境变量中设置 [bold]OPENAI_API_KEY[/bold]，或者在项目根目录下创建 [bold].env[/bold] 文件并配置 [bold]LLM_API_KEY[/bold]。")
            sys.exit(1)
        else:
            raise e

def get_onboarding_panel():
    return Panel(
        """[bold cyan]🚀 欢迎使用 SpineDoc (阅脊) CLI 极客版！[/bold cyan]\n
[bold]1. 建立知识晶体 (Ingest):[/bold]
   $ [green]spine ingest ./papers/[/green] (支持文件夹批量处理)
   $ [green]spine ingest sample.pdf[/green]

[bold]2. 查看你的知识大典 (Inventory):[/bold]
   $ [green]spine list[/green]
   $ [green]spine tree <doc_id>[/green]

[bold]3. 深度问答与综述 (Intelligence):[/bold]
   $ [green]spine ask "这篇文章核心创新是什么？"[/green]
   $ [green]spine ask "什么是多跳推理" --kg[/green] (图谱增强)
   $ [green]spine compare "Methodology"[/green] (跨文档综述)
""",
        title="[bold magenta]快速上手指南[/bold magenta]",
        border_style="bright_blue",
        padding=(1, 2)
    )

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        rprint(get_onboarding_panel())
        rprint(ctx.get_help())

@app.command()
def ingest(
    path: str = typer.Argument(..., help="PDF 文件路径、文件夹路径或通配符"),
    concurrency: int = typer.Option(4, "--workers", "-w", help="并行处理的文档数量")
):
    """
    📥 [bold]摄入文档[/bold]: 支持单文件、文件夹批量处理。
    系统将自动执行：ISR 重建 -> OpenKG 对齐 -> 语义分块 -> 向量化。
    """
    engine = get_engine()
    target_path = Path(path)
    files_to_process = []

    if target_path.is_dir():
        files_to_process = list(target_path.glob("*.pdf"))
    elif "*" in path:
        import glob
        files_to_process = [Path(f) for f in glob.glob(path) if f.endswith(".pdf")]
    elif target_path.suffix.lower() == ".pdf":
        files_to_process = [target_path]

    if not files_to_process:
        console.print(f"[bold red]错误:[/bold red] 在 {path} 下未找到 PDF 文件。")
        raise typer.Exit(1)

    console.print(f"📂 [bold]发现 {len(files_to_process)} 篇文档，启动并行编纂流 (Workers: {concurrency})...[/bold]")

    async def process_with_limit(files):
        semaphore = asyncio.Semaphore(concurrency)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=False,
        ) as progress:
            overall_task = progress.add_task("[bold cyan]总体进度", total=len(files))
            
            async def worker(file_path: Path):
                async with semaphore:
                    task_id = progress.add_task(f"  > {file_path.name[:20]}...", total=None)
                    try:
                        doc_id = await engine.ingest_document(
                            str(file_path), 
                            progress_callback=lambda m: progress.update(task_id, description=f"  > {m[:30]}...")
                        )
                        progress.update(task_id, description=f"  ✅ [green]{file_path.name[:20]}[/green]", completed=True)
                    except Exception as e:
                        progress.update(task_id, description=f"  ❌ [red]{file_path.name[:20]} (失败)[/red]", completed=True)
                        console.print(f"\n[red]文档 {file_path.name} 处理异常: {e}[/red]")
                    finally:
                        progress.advance(overall_task)

            await asyncio.gather(*(worker(f) for f in files))

    asyncio.run(process_with_limit(files_to_process))
    console.print("\n[bold green]✨ 批量编纂任务执行完毕！输入 `spine list` 查看结果。[/bold green]")

@app.command(name="list")
def list_docs():
    """📋 [bold]仓库概览[/bold]: 列出所有已纳入大典的知识晶体。"""
    engine = get_engine()
    docs = engine.list_documents()
    if not docs:
        console.print("[yellow]当前仓库为空。使用 `spine ingest` 开启你的知识大典。[/yellow]")
        return
    table = Table(title="SpineDoc 知识晶体库 (永乐大典版)", header_style="bold cyan")
    table.add_column("文档 ID", style="dim"); table.add_column("文件名", style="bold"); table.add_column("逻辑锚点", justify="right"); table.add_column("状态", justify="center")
    for d in docs:
        status = "[green]Ready[/green]" if d.get("vectorized") else "[yellow]Logic[/yellow]"
        table.add_row(d["id"], d["filename"], str(len(d["toc"])), status)
    console.print(table)

@app.command()
def tree(doc_id: str):
    """🌳 [bold]可视化脊梁[/bold]: 展示长文档的逻辑骨架。"""
    engine = get_engine()
    doc = engine.get_document(doc_id)
    if not doc: return console.print(f"[red]未找到文档 {doc_id}[/red]")
    spine_tree = Tree(f"[bold blue]📄 {doc['filename']}[/bold blue]")
    for item in doc["toc"]:
        spine_tree.add(f"[bold green]{item['title']}[/bold green] [dim](P{item['page']})[/dim]")
    console.print(Panel(spine_tree, title="Spine ISR Reconstruction", border_style="blue"))

@app.command()
def ask(
    query: str = typer.Argument(..., help="提问内容"),
    doc_id: str = typer.Option(None, "--doc", "-d", help="指定文档 ID"),
    kg: bool = typer.Option(False, "--kg", help="开启 OpenKG 语义扩写 (战胜 GraphRAG 的武器)"),
    limit: int = typer.Option(5, "--limit", "-l", help="检索片段数量")
):
    """🧠 [bold]语义问答[/bold]: 逻辑感知检索 + LLM 深度解读。"""
    engine = get_engine()
    docs = engine.list_documents()
    if not docs: return
    target_doc = engine.get_document(doc_id) if doc_id else docs[-1]
    
    with console.status(f"[cyan]正在穿透文档: {target_doc['filename']}...[/cyan]"):
        if kg:
            results = asyncio.run(engine.hybrid_ask(query, target_doc["id"], limit=limit))
        else:
            if target_doc.get("vectorized") and engine.vector_store.is_available:
                results = engine.vector_store.search(query, doc_id=target_doc["id"], limit=limit)
            else:
                results = engine.search_fallback(target_doc, query, limit=limit)

    if not results: return console.print("[yellow]未能定位到证据。[/yellow]")
    rprint(f"\n[bold]📍 逻辑溯源 [{ 'KG-Enhanced' if kg else 'Standard' }]:[/bold]")
    for i, res in enumerate(results):
        rprint(f"  • [cyan][{i+1}] {res.get('breadcrumb', 'N/A')}[/cyan] [dim](P{res.get('page', 0)})[/dim]")

    if not settings.LLM_API_KEY: return
    console.print(f"\n[bold blue]🧠 Spine AI:[/bold blue] ", end="")
    context = "\n\n".join([f"章节: {r.get('breadcrumb','')} \n内容: {r['text']}" for r in results])
    sys_prompt = f"你是一个专业的长文档研读引擎(SpineDoc)。请基于提供的切片精准回答，注明章节。参考资料:\n{context}"
    
    async def chat():
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        stream = await client.chat.completions.create(model=settings.LL_MODEL_NAME if hasattr(settings, 'LL_MODEL_NAME') else settings.LLM_MODEL_NAME, messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}], stream=True)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content: print(chunk.choices[0].delta.content, end="", flush=True)
    asyncio.run(chat())
    print("\n")

@app.command()
def compare(
    topic: str = typer.Argument(..., help="对比分析的主题"),
    docs: str = typer.Option(None, "--docs", help="文档 ID 列表 (逗号分隔)")
):
    """⚔️ [bold]跨文档协同[/bold]: 生成多文档对比综述 (永乐大典模式)。"""
    engine = get_engine()
    all_docs = engine.list_documents()
    if not all_docs: return
    target_ids = docs.split(",") if docs else [d["id"] for d in all_docs]
    
    console.print(Panel(f"针对主题 [bold cyan]{topic}[/bold cyan] 开启 {len(target_ids)} 篇文档的矩阵融合分析...", title="🏛️ Spine-Matrix Fusion", border_style="magenta"))
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task(description="透析中...", total=None)
        report = asyncio.run(engine.compare_documents(topic, target_ids, progress_callback=lambda m: progress.update(task, description=m)))
    
    console.print("\n[bold magenta]🏛️ 当代永乐大典·对比性综述报告:[/bold magenta]")
    console.print(Panel(report, border_style="magenta", padding=(1, 2)))

@app.command()
def mcp():
    """📡 启动内置 MCP 服务器，对接 Claude/IDE 等外部 AI 客户端。"""
    from spine_cli.mcp.server import run_mcp_server
    # console.print("[bold green]📡 SpineDoc MCP 服务器正在启动...[/bold green]")
    # console.print("[dim]传输协议: stdio (标准输入输出)[/dim]")
    run_mcp_server()

if __name__ == "__main__":
    app()
