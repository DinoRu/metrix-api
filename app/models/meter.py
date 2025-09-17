# models/meter.py
from sqlalchemy import Column, String, Text, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel

class Meter(Base, BaseModel):
    __tablename__ = "meters"

    meter_id_code = Column(String(50), unique=True, nullable=False, index=True)   # Идентификационный код
    meter_number = Column(String(100), unique=True, nullable=True, index=True)   # Номер ПУ
    type = Column(String(50), nullable=True)                                     # Тип прибора учета
    location_address = Column(Text, nullable=True)                                               # Адрес
    client_name = Column(String(255))                                             # Наименование объекта сети
    # Предыдущие показания
    prev_reading_value = Column(Float, nullable=True)
    # Date du dernier passage si dispo (colonne "Дата обхода")
    last_reading_date = Column(DateTime(timezone=True))

    status = Column(String(50), default="active", index=True)
    meter_metadata = Column(JSON, default=dict)

    readings = relationship("Reading", back_populates="meter", cascade="all, delete-orphan")
