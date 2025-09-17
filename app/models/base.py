import uuid

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql.base import UUID
from sqlalchemy.ext.declarative import declared_attr


class BaseModel:
	"""Base model with common fields"""

	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

	@declared_attr
	def __tablename__(cls):
		return cls.__name__.lower() + 's'