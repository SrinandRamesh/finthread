"""SQLAlchemy ORM models — Section 5 of the contract."""
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint,
)

from app.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)           # ds_ + 8 hex
    name = Column(Text, nullable=False)
    source = Column(String, nullable=False)          # 'upload' | 'sample'
    uploaded_at = Column(DateTime, nullable=False)
    row_count = Column(Integer, nullable=False)
    has_labels = Column(Boolean, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String, nullable=False)      # FK to datasets.id
    transaction_id = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    currency = Column(String, nullable=False)
    channel = Column(String, nullable=True)
    label = Column(String, nullable=True)
    gt_typology = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("dataset_id", "transaction_id", name="uq_dataset_txid"),
        Index("ix_transactions_sender", "sender"),
        Index("ix_transactions_receiver", "receiver"),
        Index("ix_transactions_timestamp", "timestamp"),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True)            # run_ + 8 hex
    dataset_id = Column(String, nullable=False)      # FK to datasets.id
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)           # 'completed' | 'failed'
    config_json = Column(Text, nullable=True)
    summary_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
