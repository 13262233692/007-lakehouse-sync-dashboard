from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="响应码，0 表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")


class PageMeta(BaseModel):
    skip: int = Field(..., description="跳过的记录数")
    limit: int = Field(..., description="每页记录数")
    total: int = Field(..., description="总记录数")


class PaginatedResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="响应码，0 表示成功")
    message: str = Field(default="success", description="响应消息")
    data: list[T] = Field(default_factory=list, description="数据列表")
    meta: PageMeta


class AssetColumnSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    data_type: str
    comment: Optional[str] = None
    is_nullable: bool
    is_partition: bool
    ordinal_position: int


class AssetPartitionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    value: Optional[str] = None
    size_bytes: int
    file_count: int
    row_count: Optional[int] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    last_modified_at: Optional[datetime] = None


class AssetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fully_qualified_name: str
    source_type: str
    storage_layer: str
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    table_type: Optional[str] = None
    location: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    total_size_bytes: int
    file_count: int
    row_count: Optional[int] = None
    partition_count: int
    column_count: int
    owner: Optional[str] = None
    tags: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    created_at: datetime


class AssetDetail(AssetBase):
    columns: list[AssetColumnSchema] = Field(default_factory=list)
    partitions: list[AssetPartitionSchema] = Field(default_factory=list)


class AssetSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fully_qualified_name: str
    source_type: str
    storage_layer: str
    description: Optional[str] = None
    total_size_bytes: int
    file_count: int
    matched_type: str
    matched_text: Optional[str] = None


class StorageLayerStats(BaseModel):
    name: str
    total_size_bytes: int
    total_tables: int
    total_files: int
    percentage: float


class OverviewStats(BaseModel):
    total_size_bytes: int
    total_tables: int
    total_files: int
    storage_layers: list[StorageLayerStats]


class TreeNode(BaseModel):
    name: str
    type: str
    size_bytes: int = 0
    file_count: int = 0
    children: list["TreeNode"] = Field(default_factory=list)


TreeNode.model_rebuild()


class TrendPoint(BaseModel):
    stat_date: str
    total_size_bytes: int
    total_files: int
    total_tables: int


class SourceBreakdownItem(BaseModel):
    source_type: str
    total_size_bytes: int
    total_tables: int
    total_files: int


class SyncTaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_assets: int
    processed_assets: int
    total_size_bytes: int
    error_message: Optional[str] = None
    triggered_by: Optional[str] = None
    created_at: datetime


class SyncStatusSchema(BaseModel):
    is_running: bool
    current_task: Optional[SyncTaskSchema] = None
    last_completed: Optional[SyncTaskSchema] = None
