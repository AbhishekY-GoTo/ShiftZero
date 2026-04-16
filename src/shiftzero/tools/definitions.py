"""Tool definitions for Bedrock Claude"""

from typing import List, Dict, Any


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get tool definitions in AWS Bedrock format

    These define what the agent can do and match the Tool classes.
    """
    return [
        {
            "toolSpec": {
                "name": "get_pod_status",
                "description": (
                    "Get Kubernetes pod status, health, restart count, and recent events. "
                    "Use this to investigate pod issues and understand what's happening."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "Kubernetes namespace (e.g., 'production', 'staging')"
                            },
                            "pod_name": {
                                "type": "string",
                                "description": "Specific pod name (optional)"
                            },
                            "deployment_name": {
                                "type": "string",
                                "description": "Deployment name to get all its pods (optional)"
                            }
                        },
                        "required": ["namespace"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_pod_logs",
                "description": (
                    "Retrieve recent logs from a Kubernetes pod. "
                    "Use this to investigate errors and understand what went wrong."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "Kubernetes namespace"
                            },
                            "pod_name": {
                                "type": "string",
                                "description": "Pod name to get logs from"
                            },
                            "container": {
                                "type": "string",
                                "description": "Container name (optional, defaults to first container)"
                            },
                            "lines": {
                                "type": "integer",
                                "description": "Number of log lines to retrieve (default: 100)",
                                "default": 100
                            }
                        },
                        "required": ["namespace", "pod_name"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "restart_deployment",
                "description": (
                    "Perform a rolling restart of a Kubernetes deployment. "
                    "Use this when you're confident a restart will fix the issue. "
                    "IMPORTANT: Only use after investigating and confirming it's safe. "
                    "Maximum 3 restarts per hour per service."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "Kubernetes namespace"
                            },
                            "deployment_name": {
                                "type": "string",
                                "description": "Deployment name to restart"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Clear reason for restart (for audit trail)"
                            }
                        },
                        "required": ["namespace", "deployment_name", "reason"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "check_deployment_history",
                "description": (
                    "Check recent deployment history including replica sets and image changes. "
                    "Use this to see if recent deployments might be related to the incident."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "namespace": {
                                "type": "string",
                                "description": "Kubernetes namespace"
                            },
                            "deployment_name": {
                                "type": "string",
                                "description": "Deployment name"
                            }
                        },
                        "required": ["namespace", "deployment_name"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "update_pagerduty_incident",
                "description": (
                    "Update or resolve a PagerDuty incident. "
                    "Use this to acknowledge or resolve incidents after successful remediation."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "PagerDuty incident ID"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["acknowledged", "resolved"],
                                "description": "New status for the incident"
                            },
                            "resolution_note": {
                                "type": "string",
                                "description": "Resolution note explaining what was done (required when resolving)"
                            }
                        },
                        "required": ["incident_id", "status"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "add_pagerduty_note",
                "description": (
                    "Add a note to a PagerDuty incident. "
                    "Use this to document investigation progress or findings."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "PagerDuty incident ID"
                            },
                            "note": {
                                "type": "string",
                                "description": "Note content"
                            }
                        },
                        "required": ["incident_id", "note"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "escalate_to_oncall",
                "description": (
                    "Escalate incident to human on-call engineer with full diagnostic report. "
                    "Use this when: confidence is low, service is high-criticality, "
                    "or issue is outside approved autonomy scope."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "PagerDuty incident ID"
                            },
                            "diagnostic_summary": {
                                "type": "string",
                                "description": "Summary of what was investigated"
                            },
                            "root_cause_hypothesis": {
                                "type": "string",
                                "description": "Your best guess at root cause"
                            },
                            "actions_attempted": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of actions already tried"
                            },
                            "recommended_next_steps": {
                                "type": "string",
                                "description": "What the human should try next"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Your confidence level (0.0-1.0)"
                            }
                        },
                        "required": [
                            "incident_id",
                            "diagnostic_summary",
                            "root_cause_hypothesis",
                            "recommended_next_steps"
                        ]
                    }
                }
            }
        }
    ]
