from pydantic_settings import BaseSettings
import os
from uuid import UUID
from typing import Optional
from pathlib import Path

# --- 路径锚定：顶级架构师的绝对基准 ---
# APP_ROOT = .../backend/app
APP_ROOT = Path(__file__).resolve().parent.parent
# BACKEND_ROOT = .../backend
BACKEND_ROOT = APP_ROOT.parent

class Settings(BaseSettings):
    """
    【架构师级配置】：支持动态合成连接串，适配多环境运行。
    """
    PROJECT_NAME: str = "SpineDoc"
    
    # 1. 数据库零件 (从 .env 读取)
    DB_USER: str = "spinedoc_admin"
    DB_PASSWORD: str = "YuDD3OlELPBYuVUpTHuA2atV3ARYobz6"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "SpineDoc_DB"

    @property
    def DATABASE_URL(self) -> str:
        # 优先读取系统直接注入的 DATABASE_URL (Docker 模式)，否则动态合成
        env_url = os.getenv("DATABASE_URL")
        if env_url: return env_url
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # 2. Redis 零件
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = "dPYgQR+yWRLs/f8Y/WS8+XSrceUrXRwl"

    @property
    def REDIS_URL(self) -> str:
        env_url = os.getenv("REDIS_URL")
        if env_url: return env_url
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # 2. AI 引擎 (BYOK)
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"
    AI_TIMEOUT: int = 300  # 🚀 [架构师提示] 默认 5 分钟超时，适配长文档解析

    # 向量模型配置 (推荐使用硅基流动 SiliconFlow)
    # 免费额度大, 兼容 OpenAI 协议, 支持 768 维模型
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_NAME: str = "netease-youdao/bce-embedding-base_v1" # 原生 768 维    
    # 3. 存储路径：绝对锚定，不再随 cwd 漂移
    STORAGE_ROOT: str = str(BACKEND_ROOT / "storage")
    TEMP_UPLOADS: str = str(BACKEND_ROOT / "temp_uploads")
    
    # 4. 环境与调试
    DEV_MODE: bool = True
    DEV_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001") 
    DEV_WORKSPACE_ID: UUID = UUID("00000000-0000-0000-0000-000000000002")

    model_config = {
        # 🏛️ 架构师对齐：强制指向项目根目录的 .env，确保 Docker 与本地环境共用一套 Key
        "env_file": str(BACKEND_ROOT.parent / ".env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()

# 自动创建必要物理目录
os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
os.makedirs(settings.TEMP_UPLOADS, exist_ok=True)
