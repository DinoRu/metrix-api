

from sqlalchemy import Column, ForeignKey, Float, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel


class Reading(Base, BaseModel):
	__tablename__ = "readings"

	meter_id = Column(UUID(as_uuid=True), ForeignKey("meters.id", ondelete="CASCADE"), nullable=False)
	user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
	reading_value = Column(Float, nullable=False)
	reading_date = Column(DateTime(timezone=True), nullable=False)
	reading_type = Column(String(50), default="manual")
	device_id = Column(String(255))
	latitude = Column(Float)
	longitude = Column(Float)
	accuracy_meters = Column(Float)
	notes = Column(Text)
	sync_status = Column(String(50), default="synced", index=True)
	client_id = Column(String(255), unique=True, index=True)  # For offline conflict resolution
	photos = Column(ARRAY(String), nullable=False)

	# Relationships
	meter = relationship("Meter", back_populates="readings")
	user = relationship("User", back_populates="readings")


	__table_args__ = (
		UniqueConstraint('client_id', name='unique_client_reading'),
	)
