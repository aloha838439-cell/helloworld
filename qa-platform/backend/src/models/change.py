from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.models.base import Base


class Change(Base):
    __tablename__ = "changes"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    module = Column(String(200), nullable=False)
    change_type = Column(String(100), default="Feature")  # Feature, Bug Fix, Refactor, Config
    author = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    affected_files = Column(JSON, default=list)  # List of affected file paths
    jira_ticket = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User")
    analyses = relationship("ImpactAnalysis", back_populates="change", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "module": self.module,
            "change_type": self.change_type,
            "author": self.author,
            "affected_files": self.affected_files or [],
            "jira_ticket": self.jira_ticket,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
