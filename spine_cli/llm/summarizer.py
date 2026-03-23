from openai import AsyncOpenAI
from app.core.config import settings

class SpineSummarizer:
    """
    SpineDoc 摘要蒸馏引擎
    负责将长章节原文压缩为语义稠密的摘要，供语义路由使用。
    """
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL_NAME

    async def summarize_section(self, title: str, content: str) -> str:
        """对单个章节进行蒸馏摘要"""
        prompt = (
            f"你是一个学术/文档摘要专家。请针对以下章节内容，生成一段极其简炼的‘语义摘要’(50-100字)。\n"
            f"目标是保留该章节的核心观点、实验方法或关键结论，以便后续进行语义匹配。\n\n"
            f"章节标题: {title}\n"
            f"内容片段: {content[:3000]}"
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"摘要生成失败: {e}"
