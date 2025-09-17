# =====================================
# api/app/schemas/task.py
# =====================================
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.task import TaskStatus


class TaskResponse(BaseModel):
	task_id: str = Field(alias='id')
	task_name: str
	status: TaskStatus
	created_at: datetime
	started_at: Optional[datetime]
	completed_at: Optional[datetime]
	progress: Optional[Dict[str, Any]]
	result: Optional[Dict[str, Any]]
	error_message: Optional[str]

	model_config = ConfigDict(from_attributes=True)


class TaskStatusResponse(BaseModel):
	task_id: str
	status: str
	current: Optional[int]
	total: Optional[int]
	percentage: Optional[float]
	message: Optional[str]
	result: Optional[Dict[str, Any]]
	error: Optional[str]


class MeterImportTaskResponse(BaseModel):
	task_id: str
	status: TaskStatus
	message: str

	class Config:
		json_encoders = {
			TaskStatus: lambda v: v.value
		}


class MeterImportStatusResponse(BaseModel):
	task_id: str
	status: TaskStatus
	processed: int = 0
	total: int = 0
	success: int = 0
	failed: int = 0
	percentage: int = 0
	errors: List[str] = []
	result: Optional[dict] = None

	class Config:
		json_encoders = {
			TaskStatus: lambda v: v.value
		}


class MeterImportResultResponse(BaseModel):
	task_id: str
	status: TaskStatus
	success: int
	failed: int
	errors: List[str]
	meters: List[dict] = []  # MeterResponse serialized

	class Config:
		json_encoders = {
			TaskStatus: lambda v: v.value
		}
