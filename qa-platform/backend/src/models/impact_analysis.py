from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.models.base import Base


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    change_id = Column(Integer, ForeignKey("changes.id"), nullable=True)
    query_description = Column(Text, nullable=False)
    query_module = Column(String(200))

    # Analysis results
    impact_score = Column(Float, default=0.0)  # 0-100
    risk_level = Column(String(50), default="Low")  # Low, Medium, High, Critical
    affected_areas = Column(JSON, default=list)  # List of affected area strings
    potential_side_effects = Column(JSON, default=list)  # List of side effect descriptions
    similar_defect_ids = Column(JSON, default=list)  # IDs of similar defects
    similarity_scores = Column(JSON, default=list)  # Corresponding similarity scores
    test_case_ids = Column(JSON, default=list)  # IDs of generated test cases

    # Metadata
    analysis_duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="analyses")
    change = relationship("Change", back_populates="analyses")

    def to_dict(self):
        return {
            "id": self.id,
            "query_description": self.query_description,
            "query_module": self.query_module,
            "impact_score": self.impact_score,
            "risk_level": self.risk_level,
            "affected_areas": self.affected_areas or [],
            "potential_side_effects": self.potential_side_effects or [],
            "similar_defect_ids": self.similar_defect_ids or [],
            "similarity_scores": self.similarity_scores or [],
            "test_case_ids": self.test_case_ids or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
