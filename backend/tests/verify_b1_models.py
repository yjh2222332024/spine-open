import asyncio
from sqlmodel import create_mock_engine
from app.core.models import User, Workspace, Document, TocItem, Chunk, ProcessingStatus
import sys
import os
from sqlalchemy.schema import CreateTable

# 确保 backend 目录在路径中
sys.path.append(os.path.join(os.getcwd(), "backend"))

def dump(sql, *multiparams, **params):
    pass

engine = create_mock_engine("postgresql://", dump)

async def verify_models():
    print("--- 验证模型导入 ---")
    print(f"User model: {User}")
    print(f"Workspace model: {Workspace}")
    print(f"Document model: {Document}")
    print(f"Chunk model: {Chunk}")
    print(f"Status Enum: {list(ProcessingStatus)}")
    
    print("\n--- 模拟生成 DDL (检查语法) ---")
    # 由于是 mock engine，这里不会真的连接数据库，主要检查 pgvector 是否正确转换
    for table in [User.__table__, Workspace.__table__, Document.__table__, Chunk.__table__]:
        ddl = CreateTable(table).compile(dialect=engine.dialect)
        print(f"Table {table.name} DDL generated successfully.")

if __name__ == "__main__":
    asyncio.run(verify_models())