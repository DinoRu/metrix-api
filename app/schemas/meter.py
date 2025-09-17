# schemas/meter.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.reading import ReadingResponse


class MeterBase(BaseModel):
    meter_id_code: str = Field(..., max_length=50)
    meter_number: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50, )
    location_address: Optional[str] = None
    client_name: Optional[str] = None

    prev_reading_value: Optional[float] = None
    last_reading_date: Optional[datetime] = None

    status: str = "active"
    meter_metadata: Optional[Dict[str, Any]] = {}

class MeterCreate(MeterBase):
    pass

class MeterUpdate(BaseModel):
    type: Optional[str] = None
    location_address: Optional[str] = None
    client_name: Optional[str] = None
    prev_reading_value: Optional[float] = None
    last_reading_date: Optional[datetime] = None
    status: Optional[str] = None
    meter_metadata: Optional[Dict[str, Any]] = None

class MeterResponse(MeterBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MeterImportResponse(BaseModel):
    success: int
    failed: int
    errors: list[str]
    meters: list[MeterResponse]


class MeterResponseWithReading(MeterBase):
    readings: ReadingResponse


class MeterListResponse(BaseModel):
    total: int
    data: List[MeterResponse]