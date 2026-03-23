import asyncio
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console

console = Console()

async def test_mcp():
    # 指向我们的 spine cli
    # 确保 spine 命令已经安装
    server_params = StdioServerParameters(
        command="spine",
        args=["mcp"],
        env=os.environ.copy()
    )

    console.print("[bold cyan]📡 正在尝试连接本地 SpineDoc MCP 服务器...[/bold cyan]")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. 初始化
                await session.initialize()
                console.print("✅ [green]MCP 初始化成功！[/green]")

                # 2. 列出工具
                tools = await session.list_tools()
                console.print(f"\n[bold]🛠️ 已发现工具 ({len(tools.tools)} 个):[/bold]")
                for tool in tools.tools:
                    console.print(f"  • [blue]{tool.name}[/blue]: {tool.description[:50]}...")

                # 3. 调用 list_available_documents 测试逻辑联通
                console.print("\n[bold cyan]🧪 正在调用 'list_available_documents'...[/bold cyan]")
                result = await session.call_tool("list_available_documents")
                console.print(f"📦 结果: 已发现 {len(result.content[0].text)} 篇文档。")
                
                console.print("\n[bold green]✨ MCP 本地握手测试圆满成功！[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ MCP 测试失败:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
