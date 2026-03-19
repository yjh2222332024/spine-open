import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# 🏛️ 路径对齐
BASE_PATH = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_PATH))

from app.services.parser import hybrid_parser
from app.services.summarizer import summarizer
from app.core.config import settings
import fitz

async def grow_summary_tree(pdf_path: str):
    print(f"🌱 [Spine Tree Growth Initialized] Target: {Path(pdf_path).name}")
    
    # 1. 物理结构提取 (Divide)
    print("🚀 步骤 1: 正在提取物理 TOC 结构...")
    raw_toc = hybrid_parser.extract_toc(pdf_path)
    if not raw_toc:
        print("❌ 未能提取到 TOC，实验终止。")
        return

    # 2. 物理内容切片与叶子节点摘要 (Distill)
    print(f"🚀 步骤 2: 正在并行生成 {len(raw_toc[:5])} 个核心章节的叶子摘要...")
    doc = fitz.open(pdf_path)
    leaf_tasks = []
    
    # 为了演示效率，我们取前 5 个章节作为代表
    for i, item in enumerate(raw_toc[:5]):
        start_page = item['page'] - 1
        # 简单估算结束页码：下一个章节的起始页码 - 1
        end_page = raw_toc[i+1]['page'] - 1 if i+1 < len(raw_toc) else len(doc) - 1
        
        content = ""
        for p in range(start_page, end_page + 1):
            content += doc[p].get_text("text")
        
        leaf_tasks.append({
            "id": item['id'],
            "title": item['title'],
            "content": content[:3000] # 截断以节省 token
        })

    # 并行调用 LLM 蒸馏器
    leaf_summaries = await summarizer.batch_summarize(leaf_tasks)
    
    for i, summary in enumerate(leaf_summaries):
        print(f"✅ Leaf Node '{leaf_tasks[i]['title']}' Summary Generated. ({len(summary)} chars)")

    # 3. 递归聚合 (Recursive Aggregate)
    print("\n🚀 步骤 3: 正在执行‘分治递归’逻辑，生成全局综述...")
    # 模拟将前 3 个摘要聚合成一个总的大纲
    global_overview = await summarizer.aggregate_node_summaries(
        "Introduction & Background Overview", 
        leaf_summaries[:3]
    )
    
    print(f"\n🏛️ [Global Recursive Summary]:\n{global_overview}")

    # 4. 效能审计
    print("\n📊 [H-RAG 效能审计]")
    print(f"原始文本量: ~{sum(len(t['content']) for t in leaf_tasks)} chars")
    print(f"摘要树总量: ~{sum(len(s) for s in leaf_summaries) + len(global_overview)} chars")
    print(f"Context 压缩比: {(1 - (len(global_overview)/20000))*100:.1f}% (理论上限)")
    
    doc.close()

if __name__ == "__main__":
    sample_pdf = str(BASE_PATH / "storage" / "workspaces" / "00000000-0000-0000-0000-000000000002" / "[Academic]_Retrieval-Augmented Generation for Knowl.pdf")
    asyncio.run(grow_summary_tree(sample_pdf))
