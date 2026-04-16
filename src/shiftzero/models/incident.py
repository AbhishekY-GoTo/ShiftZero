"""Incident data models"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    """Incident resolution status"""
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    AUTO_RESOLVED = "auto_resolved"
    ESCALATED = "escalated"
    FAILED = "failed"


class Incident(BaseModel):
    """Internal incident record"""

    # Core fields
    incident_id: str = Field(..., description="PagerDuty incident ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = Field(..., description="Affected service name")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="high, medium, low")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    # Layer 1 Analysis (Noise Detection)
    is_noise: bool = Field(default=False)
    noise_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    similar_incidents_count: int = Field(default=0)

    # Layer 2 Analysis (Investigation & Remediation)
    investigation_summary: Optional[str] = None
    root_cause: Optional[str] = None
    root_cause_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    remediation_action: Optional[str] = None
    action_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Outcome
    status: IncidentStatus = Field(default=IncidentStatus.RECEIVED)
    resolution_time_seconds: Optional[float] = None
    verification_passed: bool = Field(default=False)
    escalated_to_human: bool = Field(default=False)
    escalation_reason: Optional[str] = None
    actions_taken: List[str] = Field(default_factory=list)
    agent_reasoning: Optional[str] = None

    # Metadata
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

    def mark_resolved(self):
        """Mark incident as resolved"""
        self.status = IncidentStatus.AUTO_RESOLVED
        self.resolved_at = datetime.utcnow()
        if self.timestamp:
            self.resolution_time_seconds = (
                self.resolved_at - self.timestamp
            ).total_seconds()

    def mark_escalated(self, reason: str):
        """Mark incident as escalated to human"""
        self.status = IncidentStatus.ESCALATED
        self.escalated_to_human = True
        self.escalation_reason = reason
        self.escalated_at = datetime.utcnow()
        if self.timestamp:
            self.resolution_time_seconds = (
                self.escalated_at - self.timestamp
            ).total_seconds()

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "Q1RCZQX6YFXOE2",
                "timestamp": "2026-04-16T08:00:00Z",
                "service": "api-service",
                "alert_type": "PodCrashLooping",
                "severity": "high",
                "title": "Pod api-service-xyz is CrashLooping",
                "description": "Kubernetes pod has restarted 15 times",
            }
        }
