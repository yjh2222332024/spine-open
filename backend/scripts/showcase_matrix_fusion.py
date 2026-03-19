import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

import importlib.util

# 🏛️ 路径对齐：绝对锚定项目根目录
SCRIPT_PATH = Path(__file__).resolve()
# backend 目录: E:\study\code\SpineDoc\backend
BACKEND_PATH = SCRIPT_PATH.parent.parent
# 根目录: E:\study\code\SpineDoc
ROOT_PATH = BACKEND_PATH.parent
# 传感器目录: E:\study\code\SpineDoc\Spine-Sensor
SENSOR_PATH = ROOT_PATH / "Spine-Sensor"

# 注入搜索路径
sys.path.append(str(BACKEND_PATH))
sys.path.append(str(SENSOR_PATH))

# 首席架构师：利用 importlib 强行加载传感器内核
def load_semantic_router():
    router_path = SENSOR_PATH / "src" / "adapters" / "semantic_router.py"
    spec = importlib.util.spec_from_file_location("semantic_router_core", str(router_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SemanticRouter

from app.services.parser import hybrid_parser
from app.services.summarizer import summarizer
import fitz

async def multi_doc_fusion_audit():
    print("🏛️ [Spine-Matrix Multi-Doc Fusion Initialized]")
    
    # 动态加载内核
    SemanticRouter = load_semantic_router()
    
    # 物理文件路径也使用绝对锚定
    workspace_path = BACKEND_PATH / "storage" / "workspaces" / "00000000-0000-0000-0000-000000000002"
    files = [
        "[Academic]_Retrieval-Augmented Generation for Knowl.pdf",
        "[Academic]_BloombergGPT A Large Language Model for .pdf",
        "[Academic]_Provided proper attribution is provided .pdf"
    ]
    
    # 1. 独立解析与叶子摘要提取 (Vertical Distillation)
    print("\n🚀 阶段 1: 正在对 3 篇论文执行独立‘脊梁提取’与‘核心摘要生成’...")
    all_doc_data = []
    
    for filename in files:
        pdf_path = workspace_path / filename
        if not pdf_path.exists(): continue
        
        print(f"📄 正在处理: {filename}")
        toc = hybrid_parser.extract_toc(str(pdf_path))
        # 仅取前 3 个章节进行快速实验
        top_sections = toc[:3]
        
        doc = fitz.open(str(pdf_path))
        leaf_summaries = []
        for item in top_sections:
            content = doc[item['page']-1].get_text("text")[:2000]
            summary = await summarizer.summarize_leaf_node(item['title'], content)
            leaf_summaries.append({"title": item['title'], "summary": summary, "doc": filename})
        doc.close()
        all_doc_data.append(leaf_summaries)

    # 2. 语义聚类与对齐 (Horizontal Alignment)
    print("\n🚀 阶段 2: 正在利用 [SemanticRouter] 执行跨文档‘主题对齐’...")
    router = SemanticRouter()
    
    # 我们以“Methods & Architecture”作为聚合目标主题
    target_topic = "Methods and Architecture"
    print(f"🔍 寻找与主题 '{target_topic}' 语义最接近的跨文档章节...")
    
    matches = []
    for doc_summaries in all_doc_data:
        for item in doc_summaries:
            # 计算相似度 (简单模拟路由逻辑)
            query_vec = router.get_embedding(target_topic)
            item_vec = router.get_embedding(f"{item['title']} {item['summary']}")
            score = router.cosine_similarity(query_vec, item_vec)
            if score > 0.45: # 语义高相关
                matches.append(item)
                print(f"🎯 [Match {score:.2f}] Doc: {item['doc']} | Section: {item['title']}")

    # 3. 对比性综述与冲突检测 (Comparative Synthesis & Conflict Radar)
    print("\n🚀 阶段 3: 正在生成跨文档‘对比性综述’，并激活‘语义冲突雷达’...")
    
    combined_context = "\n\n".join([f"Source: {m['doc']}\nTitle: {m['title']}\nSummary: {m['summary']}" for m in matches])
    
    # 专门设计的 Prompt，要求进行“跨文档辩论式总结”
    synthesis_prompt = (
        f"你是一位顶级架构师。请针对以下来自不同文档的摘要内容，生成一份跨文档的‘对比性综述’。\n"
        f"核心要求:\n"
        f"1. 寻找共同点：这些文档在 '{target_topic}' 上有哪些共识？\n"
        f"2. 标记冲突点：不同文档之间是否存在观点矛盾、指标差异或方法论冲突？请以 [CONFLICT] 明确标记。\n"
        f"3. 互补发现：文档 A 提到的哪些细节补充了文档 B 的空白？\n"
        f"\n待分析内容库:\n{combined_context}"
    )

    # 调用 LLM 进行最终合成
    try:
        response = await summarizer.client.chat.completions.create(
            model=summarizer.model,
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_tokens=1000,
            temperature=0.4
        )
        grand_slam_report = response.choices[0].message.content.strip()
        print(f"\n🏛️ [Grand Slam Synthesis Report]:\n{grand_slam_report}")
    except Exception as e:
        print(f"❌ 合成失败: {e}")

    print("\n📊 [Spine-Matrix 融合效能总结]")
    print(f"输入文档数: {len(files)}")
    print(f"语义对齐节点数: {len(matches)}")
    print(f"冲突检测机制: 已激活 (Active)")

if __name__ == "__main__":
    asyncio.run(multi_doc_fusion_audit())
