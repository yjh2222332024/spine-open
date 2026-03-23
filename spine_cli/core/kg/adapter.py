import json
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from openai import AsyncOpenAI
from app.core.config import settings

class KGAdapter:
    """
    OpenKG 知识图谱适配器 (低成本版)
    职责：
    1. 实体对齐 (Entity Linking): 将章节标题映射到标准实体。
    2. 知识扩写 (KG Expansion): 根据实体寻找关联概念。
    """
    def __init__(self, cache_dir: str = ".spine/kg_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL_NAME

    async def link_entities(self, titles: List[str]) -> Dict[str, List[str]]:
        """
        [低成本方案]: 利用一次 LLM 调用批量提取所有章节标题中的核心实体。
        不使用昂贵的 GraphRAG 全量扫描，仅对 Spine 节点进行‘点对点’锚定。
        """
        if not titles: return {}
        
        prompt = (
            f"你是一个中文知识工程专家。请从以下文档章节标题中提取出对应的‘核心实体名’（标准学术或百科名词）。\n"
            f"返回格式为 JSON: {{\"标题\": [\"实体1\", \"实体2\"]}}\n\n"
            f"待处理标题: {json.dumps(titles, ensure_ascii=False)}"
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception as e:
            print(f"⚠️ KG 实体对齐失败: {e}")
            return {t: [] for t in titles}

    async def get_concept_path(self, entity: str) -> List[str]:
        """
        [开源版模拟]: 从 OpenKG 逻辑中获取概念层级 (例如: 肺癌 -> 癌症 -> 疾病)。
        目前使用 LLM 模拟 OpenConcepts API 的返回结果，以保证零配置可用。
        """
        prompt = f"针对实体 '{entity}'，请给出其在知识图谱中的三层归属路径（从细到粗），用逗号分隔。仅返回路径内容。"
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            path = response.choices[0].message.content.strip().split(",")
            return [p.strip() for p in path]
        except:
            return []
