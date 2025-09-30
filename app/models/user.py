import enum

from sqlalchemy import Column, String, Enum, Boolean
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
	ADMIN="admin"
	CONTROLLER="controller"
	SUB_ADMIN = "sub_admin"


class User(Base, BaseModel):
	__tablename__ = "users"

	username = Column(String(255), unique=True, nullable=False, index=True)
	hashed_password = Column(String(255), nullable=False)
	full_name = Column(String(255))
	role = Column(Enum(UserRole), nullable=False, default=UserRole.CONTROLLER)
	is_active = Column(Boolean, default=True)

	# Relationships
	readings = relationship("Reading", back_populates="user")
	