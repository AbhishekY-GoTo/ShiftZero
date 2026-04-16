"""PagerDuty webhook data models"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PagerDutyService(BaseModel):
    """PagerDuty service reference"""
    id: str
    name: str
    summary: str
    html_url: Optional[str] = None


class PagerDutyPriority(BaseModel):
    """PagerDuty priority"""
    id: str
    summary: str


class PagerDutyIncident(BaseModel):
    """PagerDuty incident details"""
    id: str
    incident_number: int
    title: str
    description: str
    created_at: datetime
    status: str  # triggered, acknowledged, resolved
    incident_key: str
    service: PagerDutyService
    urgency: str  # high, low
    priority: Optional[PagerDutyPriority] = None
    html_url: str


class PagerDutyWebhookMessage(BaseModel):
    """Individual webhook message"""
    event: str  # incident.triggered, incident.acknowledged, etc.
    incident: PagerDutyIncident


class PagerDutyWebhook(BaseModel):
    """PagerDuty webhook payload"""
    messages: List[PagerDutyWebhookMessage]

    def get_first_incident(self) -> Optional[PagerDutyIncident]:
        """Get the first incident from the webhook"""
        if self.messages:
            return self.messages[0].incident
        return None

    def is_triggered_event(self) -> bool:
        """Check if this is a new incident trigger"""
        return any(msg.event == "incident.triggered" for msg in self.messages)
