# =====================================
# api/app/models/task.py
# =====================================
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.base import BaseModel
import enum


class TaskStatus(str, enum.Enum):
	PENDING = "pending"
	PROCESSING = "processing"
	COMPLETED = "completed"
	FAILED = "failed"
	CANCELLED = "cancelled"


class TaskResult(Base, BaseModel):
	__tablename__ = "task_results"

	id = Column(String, primary_key=True)  # Celery task ID
	task_name = Column(String, nullable=False, index=True)
	user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
	status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
	params = Column(JSON)
	result = Column(JSON)
	error_message = Column(String)
	started_at = Column(DateTime(timezone=True))
	completed_at = Column(DateTime(timezone=True))
	progress = Column(JSON)  # Store progress updates
