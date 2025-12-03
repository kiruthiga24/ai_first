from sqlalchemy import Column, Integer, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(Integer, primary_key=True, index=True)
    original_sql = Column(Text, nullable=False)
    optimized_sql = Column(Text, nullable=False)
    diff = Column(Text, nullable=True)
    stats_before = Column(JSON, nullable=True)
    stats_after = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
