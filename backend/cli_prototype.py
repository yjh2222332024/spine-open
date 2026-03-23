import os
import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich import print as rprint

# 将 backend 目录添加到 Python 路径，确保能导入 app
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

# 导入现有的逻辑
try:
    from app.services.parser import hybrid_parser
except ImportError as e:
    rprint(f"[bold red]错误:[/bold red] 无法导入 app.services.parser: {e}")
    rprint("[yellow]请确保在 Spine-open/backend 目录下运行此脚本。[/yellow]")
    sys.exit(1)

app = typer.Typer(help="阅脊 (SpineDoc) 逻辑引擎 CLI 原型")
console = Console()

@app.command()
def tree(
    file_path: str = typer.Argument(..., help="PDF 文件的路径"),
    limit_pages: int = typer.Option(0, "--limit", "-l", help="限制扫描的页数 (0 为全量)")
):
    """
    提取并展示 PDF 的逻辑脊梁 (TOC)。
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]错误:[/bold red] 文件 [underline]{file_path}[/underline] 不存在。")
        raise typer.Exit(code=1)

    file_name = Path(file_path).name
    console.print(Panel(f"正在分析 [bold cyan]{file_name}[/bold cyan] 的逻辑脊梁...", title="SpineDoc ISR Engine", border_style="blue"))

    with console.status("[bold green]正在执行 ISR 重建 (Implicit Spine Reconstruction)...") as status:
        try:
            # 调用你现有的 HybridParser 逻辑
            toc_items = hybrid_parser.extract_toc(file_path, limit_pages=limit_pages)
        except Exception as e:
            console.print(f"[bold red]解析失败:[/bold red] {str(e)}")
            raise typer.Exit(code=1)

    if not toc_items:
        console.print("[yellow]警告:[/yellow] 未能从文档中提取到逻辑脊梁。")
        return

    # 使用 Rich 构建美观的逻辑树
    spine_tree = Tree(f"[bold blue]📄 {file_name}[/bold blue]")
    
    # 简单的分层构建逻辑 (支持 level 1 和 level 2)
    # 复杂的多层级可以在后续迭代中优化为递归
    current_node = spine_tree
    last_level1_node = None

    for item in toc_items:
        level = item.get('level', 1)
        title = item.get('title', '未命名章节')
        page = item.get('page', 0)
        
        display_text = f"[bold green]{title}[/bold green] [dim](P{page})[/dim]"
        
        if level == 1:
            last_level1_node = spine_tree.add(display_text)
        elif level == 2:
            if last_level1_node:
                last_level1_node.add(f"[cyan]{title}[/cyan] [dim](P{page})[/dim]")
            else:
                spine_tree.add(f"[cyan]{title}[/cyan] [dim](P{page})[/dim]")
        else:
            # 对于更深的层级，简单展示
            spine_tree.add(f"[dim]{'  ' * (level-1)}[/dim]{display_text}")

    console.print("\n[bold]提取结果:[/bold]")
    console.print(spine_tree)
    console.print(f"\n[bold green]成功![/bold green] 共提取到 [bold]{len(toc_items)}[/bold] 个逻辑锚点。")

@app.command()
def info():
    """
    显示 SpineDoc 引擎信息。
    """
    rprint(Panel.fit(
        "[bold blue]阅脊 (SpineDoc) 逻辑引擎[/bold blue]\n"
        "[dim]版本: 1.0.0-cli-prototype[/dim]\n"
        "专为长文档设计的逻辑感知 RAG 引擎",
        title="关于"
    ))

if __name__ == "__main__":
    app()
