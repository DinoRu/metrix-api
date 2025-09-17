from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
	model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
	created_at: datetime
	updated_at: datetime


class PaginationParams(BaseModel):
	skip: int = 0
	limit: int = 100

	class Config:
		json_schema_extra = {
			"example": {
				"skip": 0,
				"limit": 100
			}
		}


class PaginatedResponse(BaseModel):
	total: int
	skip: int
	limit: int
	data: list
