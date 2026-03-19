from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import init_db
from app.core.config import settings
from app.api.endpoints import documents, folders, upload, rag, spine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用的生命周期管理器。
    """
    print("正在初始化数据库连接...")
    await init_db()
    print("数据库初始化完成！")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# 注册路由
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(spine.router, prefix="/api/v1/spine", tags=["spine"])

# 配置 CORS (跨域资源共享)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 联调阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """
    健康检查接口。
    用于确认后端服务是否正常运行。
    """
    return {"message": "StructuRAG API is running!", "status": "ok"}
