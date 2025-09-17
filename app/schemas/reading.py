from datetime import datetime
from typing import Optional, Literal, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

ReadingType = Literal["manual", "imported", "estimated"]


class ReadingBase(BaseModel):
    meter_id: UUID
    reading_value: float = Field(..., gt=0)
    reading_date: datetime
    reading_type: ReadingType = "manual"
    device_id: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    accuracy_meters: Optional[float] = None
    notes: Optional[str] = None
    client_id: Optional[str] = None
    photos: List[str]  # ✅ Liste d'URLs obligatoires

    @field_validator("photos")
    def check_min_photos(cls, v):
        if len(v) < 2:
            raise ValueError("Au moins 2 URLs de photo sont obligatoires")
        return v


class ReadingCreate(ReadingBase):
    pass


class ReadingUpdate(BaseModel):
    reading_value: Optional[float] = None
    notes: Optional[str] = None
    photos: Optional[List[str]] = None

    @field_validator("photos")
    def check_min_photos(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError("Au moins 2 URLs de photo sont obligatoires")
        return v


class ReadingResponse(ReadingBase):
    id: UUID
    user_id: UUID
    sync_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingSyncRequest(BaseModel):
    readings: List[ReadingCreate]
    device_id: str


class ReadingSyncResponse(BaseModel):
    synced: int
    failed: int
    conflicts: list[dict]
