from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.models.base import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("impact_analyses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    steps = Column(JSON, default=list)  # List of step strings
    expected_result = Column(Text)
    priority = Column(String(50), default="Medium")  # Critical, High, Medium, Low
    test_type = Column(String(100), default="Functional")  # Functional, Integration, Regression, E2E
    module = Column(String(200))
    tags = Column(JSON, default=list)  # List of tag strings
    source_defect_ids = Column(JSON, default=list)  # Defect IDs that inspired this test case
    is_ai_generated = Column(String(10), default="true")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps or [],
            "expected_result": self.expected_result,
            "priority": self.priority,
            "test_type": self.test_type,
            "module": self.module,
            "tags": self.tags or [],
            "source_defect_ids": self.source_defect_ids or [],
            "is_ai_generated": self.is_ai_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
