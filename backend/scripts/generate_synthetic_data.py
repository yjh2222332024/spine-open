"""
SpineDoc Data Engine: Synthetic Data Factory CLI
================================================
一键启动“智力铸造”流程，支持 S1基础生成、S2逻辑演化、S4对抗挖掘。

Usage:
    python backend/scripts/generate_synthetic_data.py --doc_id <UUID> --evolve --mine_negatives

Author: Yan Junhao (严俊皓)
"""

import asyncio
import argparse
import sys
import os
import json
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# 注入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk
from app.services.train.qa_synthesizer import qa_synthesizer
from app.services.train.evolution_engine import spine_evolver
from app.services.train.negative_miner import negative_miner

async def generate_document_dataset(doc_id: str, limit_per_node: int, output_path: str, evolve: bool = False, mine_negatives: bool = False):
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        # 1. 预加载文档数据
        stmt = (
            select(Document)
            .options(selectinload(Document.toc_items))
            .where(Document.id == UUID(doc_id))
        )
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            print(f"❌ Error: Document {doc_id} not found.")
            return

        print(f"🏭 Starting IQ Distillation Factory for: {doc.filename}")
        print(f"🧬 Mode: [Base: Yes] [Evolve: {evolve}] [Negative Mining: {mine_negatives}]")

        all_examples = []
        
        for item in doc.toc_items:
            chunk_stmt = select(Chunk).where(Chunk.toc_item_id == item.id)
            chunk_res = await session.execute(chunk_stmt)
            chunks = chunk_res.scalars().all()
            
            content = "\n".join([c.content for c in chunks])
            if len(content.strip()) < 100: continue

            print(f"  🧠 Processing: [{item.title}]")
            
            # S1: Base QA
            examples = await qa_synthesizer.generate_base_qa(item.title, content, limit=limit_per_node)
            
            # S2: Evolution
            if evolve and examples:
                print(f"    🔥 Evolving...")
                evolved_tasks = [spine_evolver.evolve_example(ex, content) for ex in examples]
                evolved_results = await asyncio.gather(*evolved_tasks)
                examples.extend(evolved_results)

            # S4: Negative Mining
            if mine_negatives:
                print(f"    🛡️ Mining Negatives...")
                neg_example = await negative_miner.mine_negative_example(item.title, content)
                if neg_example:
                    examples.append(neg_example)

            # Inject Metadata
            for ex in examples:
                ex.metadata["doc_id"] = doc_id
                ex.metadata["node_id"] = str(item.id)
                all_examples.append(ex)

        # 3. Export
        if all_examples:
            with open(output_path, 'w', encoding='utf-8') as f:
                for ex in all_examples:
                    f.write(json.dumps(ex.model_dump(), ensure_ascii=False) + '\n')
            print(f"🚀 Success! Dataset saved to: {output_path} ({len(all_examples)} samples)")
        else:
            print("⚠️ No data generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpineDoc IQ Distillation Factory")
    parser.add_argument("--doc_id", required=True, help="UUID of the document")
    parser.add_argument("--limit", type=int, default=1, help="Base QA per node")
    parser.add_argument("--evolve", action="store_true", help="Enable Stage 2 Evolution")
    parser.add_argument("--mine_negatives", action="store_true", help="Enable Stage 4 Negative Mining")
    parser.add_argument("--output", default="synthetic_full_power_dataset.jsonl", help="Output path")
    
    args = parser.parse_args()
    asyncio.run(generate_document_dataset(args.doc_id, args.limit, args.output, args.evolve, args.mine_negatives))
