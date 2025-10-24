from sqlalchemy import Column, Integer, String
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
class Role(Base):
    __tablename__ = "roles"

    id =  Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)