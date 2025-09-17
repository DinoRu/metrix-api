from sqlalchemy import Column, String, JSON, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql.base import UUID

from app.database import Base
from app.models.base import BaseModel


class Outbox(Base, BaseModel):
	__tablename__ = "outbox"

	entity_type = Column(String(50), nullable=False)
	entity_id = Column(UUID(as_uuid=True), nullable=False)
	operation = Column(String(20), nullable=False)
	payload = Column(JSON, nullable=False)
	retry_count = Column(Integer, default=0)
	max_retries = Column(Integer, default=5)
	status = Column(String(50), default="pending", index=True)
	error_message = Column(Text)
	scheduled_at = Column(DateTime(timezone=True), default=func.now(), index=True)
	processed_at = Column(DateTime(timezone=True))
