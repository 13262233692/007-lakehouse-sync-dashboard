import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


logger = logging.getLogger(__name__)


class DataAsset(Base):
    __tablename__ = "data_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    fully_qualified_name: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_layer: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    database_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schema_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    table_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    partition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    columns: Mapped[list["AssetColumn"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    partitions: Mapped[list["AssetPartition"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assets_source_storage", "source_type", "storage_layer"),
    )


class AssetColumn(Base):
    __tablename__ = "asset_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(128), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_nullable: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    is_partition: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    asset: Mapped["DataAsset"] = relationship(back_populates="columns")


class AssetPartition(Base):
    __tablename__ = "asset_partitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    asset: Mapped["DataAsset"] = relationship(back_populates="partitions")


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_assets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_assets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StorageTrend(Base):
    __tablename__ = "storage_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stat_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    storage_layer: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tables: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_trend_date_layer", "stat_date", "storage_layer", unique=True),
    )
