"""Safety guard for enforcing autonomy boundaries"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from ..config import get_settings
from ..models import Incident

logger = logging.getLogger(__name__)


class SafetyGuard:
    """
    Enforces safety rules and autonomy boundaries

    Prevents the agent from taking actions that:
    - Exceed rate limits
    - Are outside approved scope
    - Are too risky for autonomous execution
    """

    def __init__(self):
        """Initialize safety guard with rules"""
        self.settings = get_settings()

        # Load safety rules
        with open("config/safety_rules.json", "r") as f:
            self.rules = json.load(f)

        # Rate limiting state (in-memory for Phase 1, use Redis for production)
        self.action_history: Dict[str, list] = defaultdict(list)

        logger.info("Safety guard initialized")

    async def check_action(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        incident: Incident
    ) -> Dict[str, Any]:
        """
        Check if an action is allowed based on safety rules

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            incident: Current incident context

        Returns:
            Dict with 'allowed' (bool) and 'reason' (str)
        """
        # Check if action is in approved list
        if tool_name in ["get_pod_status", "get_pod_logs", "check_deployment_history",
                         "add_pagerduty_note", "escalate_to_oncall"]:
            # Always allow read-only and escalation actions
            return {"allowed": True, "reason": "read_only_or_escalation"}

        # Check if action requires approval
        if tool_name in self.rules.get("require_human_approval", []):
            return {
                "allowed": False,
                "reason": f"{tool_name} requires human approval per safety rules"
            }

        # Special checks for restart_deployment
        if tool_name == "restart_deployment":
            return await self._check_restart_deployment(tool_input, incident)

        # Check if action is in approved autonomous list
        if tool_name not in self.rules.get("approved_autonomous_actions", []):
            return {
                "allowed": False,
                "reason": f"{tool_name} is not in approved autonomous actions list"
            }

        return {"allowed": True, "reason": "approved_action"}

    async def _check_restart_deployment(
        self,
        tool_input: Dict[str, Any],
        incident: Incident
    ) -> Dict[str, Any]:
        """
        Check if deployment restart is allowed

        Enforces rate limits and service criticality rules
        """
        namespace = tool_input.get("namespace")
        deployment = tool_input.get("deployment_name")
        service = incident.service

        # Check service criticality
        high_criticality = self.rules.get("service_criticality", {}).get("high", [])
        if service in high_criticality:
            # High criticality services need higher confidence
            if incident.root_cause_confidence < 0.90:
                return {
                    "allowed": False,
                    "reason": (
                        f"{service} is high-criticality. "
                        f"Requires ≥0.90 confidence (current: {incident.root_cause_confidence:.2f}). "
                        "Consider escalating."
                    )
                }

        # Check rate limits
        rate_check = self._check_rate_limit("restart_deployment", deployment)
        if not rate_check["allowed"]:
            return rate_check

        # Check always-escalate patterns
        always_escalate = self.rules.get("always_escalate_patterns", [])
        for pattern in always_escalate:
            if pattern in incident.alert_type.lower() or pattern in service.lower():
                return {
                    "allowed": False,
                    "reason": f"Alert matches always-escalate pattern: {pattern}"
                }

        # Passed all checks
        self._record_action("restart_deployment", deployment)
        return {"allowed": True, "reason": "passed_safety_checks"}

    def _check_rate_limit(
        self,
        action: str,
        resource: str
    ) -> Dict[str, Any]:
        """
        Check if action exceeds rate limits

        Args:
            action: Action name (e.g., 'restart_deployment')
            resource: Resource identifier (e.g., deployment name)

        Returns:
            Dict with 'allowed' and 'reason'
        """
        rate_limits = self.rules.get("rate_limits", {}).get(action, {})
        if not rate_limits:
            return {"allowed": True, "reason": "no_rate_limit"}

        max_per_hour = rate_limits.get("max_per_hour", 999)
        max_per_service = rate_limits.get("max_per_service_per_hour", 999)

        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # Clean old history
        self.action_history[action] = [
            entry for entry in self.action_history[action]
            if entry["timestamp"] > one_hour_ago
        ]

        # Count actions in last hour
        total_count = len(self.action_history[action])
        resource_count = len([
            entry for entry in self.action_history[action]
            if entry["resource"] == resource
        ])

        # Check limits
        if total_count >= max_per_hour:
            return {
                "allowed": False,
                "reason": (
                    f"Rate limit exceeded: {total_count}/{max_per_hour} "
                    f"{action} actions in last hour"
                )
            }

        if resource_count >= max_per_service:
            return {
                "allowed": False,
                "reason": (
                    f"Per-service rate limit exceeded: {resource_count}/{max_per_service} "
                    f"{action} actions for {resource} in last hour"
                )
            }

        return {"allowed": True, "reason": "within_rate_limits"}

    def _record_action(self, action: str, resource: str):
        """
        Record an action for rate limiting

        Args:
            action: Action name
            resource: Resource identifier
        """
        self.action_history[action].append({
            "timestamp": datetime.utcnow(),
            "resource": resource
        })

        logger.info(f"Recorded action: {action} on {resource}")

    def get_action_stats(self) -> Dict[str, Any]:
        """
        Get statistics about recent actions

        Returns:
            Dict with action statistics
        """
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        stats = {}
        for action, entries in self.action_history.items():
            recent = [e for e in entries if e["timestamp"] > one_hour_ago]
            stats[action] = {
                "count_last_hour": len(recent),
                "resources": list(set(e["resource"] for e in recent))
            }

        return stats
