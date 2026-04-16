"""ShiftZero autonomous agent core"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .bedrock_client import BedrockClaudeClient
from .config import get_settings
from .models import Incident, IncidentStatus
from .tools import KubernetesTool, PagerDutyTool, get_tool_definitions
from .services.safety import SafetyGuard
from config.prompts import get_system_prompt

logger = logging.getLogger(__name__)


class ShiftZeroAgent:
    """
    Autonomous on-call incident response agent

    Handles investigation, remediation, and escalation decisions
    using Claude via AWS Bedrock with tool use.
    """

    def __init__(self):
        """Initialize the agent with tools and clients"""
        self.settings = get_settings()
        self.claude = BedrockClaudeClient()
        self.safety_guard = SafetyGuard()

        # Initialize tools
        self.k8s_tool = KubernetesTool(self.settings.kubeconfig)
        self.pd_tool = PagerDutyTool(self.settings.pagerduty_api_key)

        # Tool registry
        self.tools = {
            "get_pod_status": self.k8s_tool.get_pod_status,
            "get_pod_logs": self.k8s_tool.get_pod_logs,
            "restart_deployment": self.k8s_tool.restart_deployment,
            "check_deployment_history": self.k8s_tool.check_deployment_history,
            "update_pagerduty_incident": self.pd_tool.update_incident,
            "add_pagerduty_note": self.pd_tool.add_note,
            "escalate_to_oncall": self.escalate_to_oncall,
        }

        logger.info("ShiftZero agent initialized")

    async def handle_incident(self, incident: Incident):
        """
        Main entry point for handling an incident

        Args:
            incident: Incident to handle
        """
        logger.info(f"Agent handling incident {incident.incident_id}")

        # Build conversation context
        conversation_history = []

        # Initial user message with incident details
        incident_context = self._build_incident_context(incident)
        conversation_history.append({
            "role": "user",
            "content": [{"text": incident_context}]
        })

        # Agent loop with tool use
        max_iterations = 10
        for iteration in range(max_iterations):
            logger.info(f"Agent iteration {iteration + 1}/{max_iterations}")

            try:
                # Invoke Claude
                response = self.claude.invoke(
                    messages=conversation_history,
                    system=get_system_prompt(),
                    tools=get_tool_definitions(),
                    max_tokens=4096,
                    temperature=0.0  # Deterministic for safety
                )

                # Parse response
                stop_reason = response.get('stopReason')
                output = response.get('output', {})
                message = output.get('message', {})
                content_blocks = message.get('content', [])

                logger.info(f"Claude response stop_reason: {stop_reason}")

                # Add assistant response to history
                conversation_history.append({
                    "role": "assistant",
                    "content": content_blocks
                })

                # Extract text and tool calls
                text_content = None
                tool_uses = []

                for block in content_blocks:
                    if 'text' in block:
                        text_content = block['text']
                        logger.info(f"Agent reasoning: {text_content[:200]}...")
                        incident.agent_reasoning = text_content

                    elif 'toolUse' in block:
                        tool_uses.append(block['toolUse'])

                # If agent finished thinking without tool calls, we're done
                if stop_reason == "end_turn" and not tool_uses:
                    logger.info("Agent completed without further tool calls")
                    break

                # Execute tool calls
                if tool_uses:
                    tool_results = await self._execute_tools(
                        tool_uses,
                        incident
                    )

                    # Add tool results to conversation
                    conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                # Check if agent is done (resolved or escalated)
                if incident.status in [
                    IncidentStatus.AUTO_RESOLVED,
                    IncidentStatus.ESCALATED
                ]:
                    logger.info(f"Incident {incident.incident_id} is {incident.status}")
                    break

            except Exception as e:
                logger.error(f"Error in agent loop: {e}", exc_info=True)
                incident.status = IncidentStatus.FAILED
                break

        logger.info(
            f"Agent completed handling incident {incident.incident_id}. "
            f"Status: {incident.status}, "
            f"Time: {incident.resolution_time_seconds}s"
        )

    async def _execute_tools(
        self,
        tool_uses: List[Dict[str, Any]],
        incident: Incident
    ) -> List[Dict[str, Any]]:
        """
        Execute tool calls from Claude

        Args:
            tool_uses: List of tool use requests
            incident: Current incident being handled

        Returns:
            Tool results to send back to Claude
        """
        tool_results = []

        for tool_use in tool_uses:
            tool_id = tool_use['toolUseId']
            tool_name = tool_use['name']
            tool_input = tool_use['input']

            logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

            # Update incident status based on tool
            if tool_name == "restart_deployment":
                incident.status = IncidentStatus.REMEDIATING
            elif tool_name.startswith("get_"):
                if incident.status == IncidentStatus.RECEIVED:
                    incident.status = IncidentStatus.INVESTIGATING

            # Check safety constraints
            safety_check = await self.safety_guard.check_action(
                tool_name,
                tool_input,
                incident
            )

            if not safety_check["allowed"]:
                # Action blocked by safety rules
                result_content = {
                    "status": "blocked",
                    "reason": safety_check["reason"],
                    "message": "This action was blocked by safety rules. Consider escalating to a human."
                }
                logger.warning(
                    f"Tool {tool_name} blocked by safety guard: {safety_check['reason']}"
                )
            else:
                # Execute the tool
                try:
                    tool_func = self.tools.get(tool_name)
                    if tool_func:
                        result_content = await tool_func(**tool_input)
                        incident.actions_taken.append(
                            f"{tool_name}({json.dumps(tool_input)})"
                        )
                    else:
                        result_content = {"error": f"Unknown tool: {tool_name}"}

                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    result_content = {"error": str(e)}

            # Format result for Claude
            # Bedrock requires json to be an object, not a string
            if isinstance(result_content, str):
                result_content = {"result": result_content}

            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_id,
                    "content": [
                        {"json": result_content}
                    ]
                }
            })

            logger.info(f"Tool {tool_name} result: {result_content}")

        return tool_results

    def _build_incident_context(self, incident: Incident) -> str:
        """
        Build initial context message for the agent

        Args:
            incident: Incident details

        Returns:
            Formatted context string
        """
        return f"""
NEW INCIDENT RECEIVED

**Incident ID**: {incident.incident_id}
**Service**: {incident.service}
**Alert Type**: {incident.alert_type}
**Severity**: {incident.severity}
**Title**: {incident.title}
**Description**: {incident.description}
**Timestamp**: {incident.timestamp.isoformat()}

Your mission: Investigate this incident and take appropriate action (auto-remediate or escalate with full diagnostic report).

Follow your decision framework:
1. INVESTIGATE - Use tools to gather information
2. DIAGNOSE - Determine root cause and confidence level
3. DECIDE - Auto-remediate (≥0.85 confidence) or escalate (<0.85 confidence)
4. VERIFY - Confirm fix worked before closing

Begin your investigation now.
        """.strip()

    async def escalate_to_oncall(
        self,
        incident_id: str,
        diagnostic_summary: str,
        root_cause_hypothesis: str,
        actions_attempted: Optional[List[str]] = None,
        recommended_next_steps: str = "",
        confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Escalate incident to human on-call engineer

        Args:
            incident_id: PagerDuty incident ID
            diagnostic_summary: Summary of investigation
            root_cause_hypothesis: Best guess at root cause
            actions_attempted: List of actions already tried
            recommended_next_steps: What human should try
            confidence: Agent's confidence level

        Returns:
            Escalation result
        """
        try:
            # Build escalation report
            report = f"""
🚨 **ESCALATION REPORT** - ShiftZero Agent

**Incident ID**: {incident_id}
**Escalated At**: {datetime.utcnow().isoformat()}
**Agent Confidence**: {confidence:.2f}

---

**DIAGNOSTIC SUMMARY**
{diagnostic_summary}

**ROOT CAUSE HYPOTHESIS**
{root_cause_hypothesis}

**ACTIONS ATTEMPTED**
{chr(10).join(f"- {action}" for action in (actions_attempted or ["None"]))}

**RECOMMENDED NEXT STEPS**
{recommended_next_steps}

---
🤖 Report generated by ShiftZero autonomous agent
            """.strip()

            # Add note to PagerDuty
            await self.pd_tool.add_note(incident_id, report)

            # TODO: Send to Slack if configured
            if self.settings.slack_bot_token:
                logger.info("Would send escalation to Slack (not implemented yet)")

            logger.info(f"Escalated incident {incident_id} to human on-call")

            return {
                "status": "escalated",
                "incident_id": incident_id,
                "report": report,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error escalating incident: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
