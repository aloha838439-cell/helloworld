from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.models.base import Base


class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False, default="Medium")  # Critical, High, Medium, Low
    module = Column(String(200), nullable=False, index=True)
    status = Column(String(100), default="Open")  # Open, In Progress, Resolved, Closed
    reporter = Column(String(200))
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    related_features = Column(JSON, default=list)  # List of related feature strings
    embedding = Column(JSON, nullable=True)  # Stored as JSON array of floats
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    reporter_user = relationship("User", back_populates="defects")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "module": self.module,
            "status": self.status,
            "reporter": self.reporter,
            "related_features": self.related_features or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
