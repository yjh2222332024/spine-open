from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON

class ProcessingStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PARTIAL = "partial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 多对多关联表：文档-标签
class DocumentTagLink(SQLModel, table=True):
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    tag_id: UUID = Field(foreign_key="tag.id", primary_key=True)

class User(SQLModel, table=True):
    """用户表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    workspaces: List["Workspace"] = Relationship(back_populates="owner")
    event_logs: List["EventLog"] = Relationship(back_populates="user")

class Workspace(SQLModel, table=True):
    """工作空间表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    documents: List["Document"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    folders: List["Folder"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Folder(SQLModel, table=True):
    """文件夹表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")
    workspace_id: UUID = Field(foreign_key="workspace.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    workspace: Workspace = Relationship(back_populates="folders")
    parent: Optional["Folder"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "Folder.id"})
    children: List["Folder"] = Relationship(back_populates="parent")
    documents: List["Document"] = Relationship(back_populates="folder")

class Tag(SQLModel, table=True):
    """标签表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    color: str = "#808080"
    workspace_id: UUID = Field(foreign_key="workspace.id")
    
    documents: List["Document"] = Relationship(back_populates="tags", link_model=DocumentTagLink)

class Document(SQLModel, table=True):
    """文档表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_hash: Optional[str] = Field(index=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(default=None)
    is_toc_locked: bool = Field(default=False)
    processed_pages: int = Field(default=0) # 已处理页数
    total_pages: int = Field(default=0)     # 总页数
    created_at: datetime = Field(default_factory=datetime.utcnow)

    updated_at: datetime = Field(default_factory=datetime.utcnow)

    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")

    # Relationships
    workspace: Optional[Workspace] = Relationship(back_populates="documents")
    folder: Optional[Folder] = Relationship(back_populates="documents")
    tags: List[Tag] = Relationship(back_populates="documents", link_model=DocumentTagLink)
    toc_items: List["TocItem"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    chunks: List["Chunk"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    metrics: List["ProcessingMetric"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class TocItem(SQLModel, table=True):
    """目录项表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    page: int
    level: int
    confidence: float = Field(default=1.0)
    # 🏛️ P2: 语义摘要存储
    summary: Optional[str] = Field(default=None)
    
    # 邻接表设计：支持树形目录
    parent_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id")
    document_id: UUID = Field(foreign_key="document.id")
    
    document: Optional["Document"] = Relationship(back_populates="toc_items")
    # 自关联关系，用于 SQLAlchemy 的层级预加载
    parent: Optional["TocItem"] = Relationship(
        back_populates="children", 
        sa_relationship_kwargs={"remote_side": "TocItem.id"}
    )
    children: List["TocItem"] = Relationship(back_populates="parent")
class Chunk(SQLModel, table=True):
    """文本分块表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    content: str
    page_number: int
    embedding: List[float] = Field(sa_column=Column(Vector(768)))

    # 架构师加固：建立与目录项的直接物理关联
    toc_item_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id", ondelete="SET NULL")
    document_id: UUID = Field(foreign_key="document.id", ondelete="CASCADE")

    document: Optional[Document] = Relationship(back_populates="chunks")

# --- Analytics Models ---

class EventLog(SQLModel, table=True):
    """用户行为日志表 (Analytics)"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    event_type: str = Field(index=True) # e.g., "document_view", "search"
    # 使用 SQLAlchemy 的 JSON 类型存储动态负载
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="event_logs")

class ProcessingMetric(SQLModel, table=True):
    """后台处理性能指标表 (Audit)"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id", index=True)
    stage: str = Field(index=True) # e.g., "ocr", "parsing", "vectorizing"
    duration_ms: int
    status: str = Field(default="success") # success, failed
    error_info: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    document: Document = Relationship(back_populates="metrics")