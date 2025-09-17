from sqlalchemy import Column, ForeignKey, String, Text, DateTime, BigInteger, JSON, Float
from sqlalchemy.dialects.postgresql.base import UUID


from app.database import Base
from app.models.base import BaseModel


class Photo(Base, BaseModel):
	__tablename__ = "photos"

	reading_id = Column(UUID(as_uuid=True), ForeignKey("readings.id", ondelete="CASCADE"), nullable=False)
	storage_path = Column(String(500))
	presigned_url = Column(Text)
	presigned_expires_at = Column(DateTime(timezone=True))
	upload_status = Column(String(50), default="pending", index=True)
	file_size_bytes = Column(BigInteger)
	mime_type = Column(String(100))
	exif_data = Column(JSON)
	latitude = Column(Float)
	longitude = Column(Float)
	taken_at = Column(DateTime(timezone=True))
	uploaded_at = Column(DateTime(timezone=True))