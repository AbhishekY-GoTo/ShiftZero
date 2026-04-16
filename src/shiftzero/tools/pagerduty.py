"""PagerDuty tool integration"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pdpyras

logger = logging.getLogger(__name__)


class PagerDutyTool:
    """Tool for interacting with PagerDuty API"""

    def __init__(self, api_key: str):
        """
        Initialize PagerDuty client

        Args:
            api_key: PagerDuty API key
        """
        self.session = pdpyras.APISession(api_key)
        logger.info("PagerDuty client initialized successfully")

    async def update_incident(
        self,
        incident_id: str,
        status: str,
        resolution_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update or resolve PagerDuty incident

        Args:
            incident_id: PagerDuty incident ID
            status: New status (acknowledged, resolved)
            resolution_note: Optional resolution note

        Returns:
            Update operation result
        """
        try:
            # Build update payload
            incident_update = {
                "type": "incident",
                "status": status
            }

            # Add resolution note if provided and resolving
            if status == "resolved" and resolution_note:
                incident_update["resolution"] = resolution_note

            # Update incident
            response = self.session.put(
                f"/incidents/{incident_id}",
                json={"incident": incident_update}
            )

            logger.info(
                f"Updated PagerDuty incident {incident_id} to status: {status}"
            )

            return {
                "status": "success",
                "incident_id": incident_id,
                "new_status": status,
                "timestamp": datetime.utcnow().isoformat()
            }

        except pdpyras.PDClientError as e:
            logger.error(f"PagerDuty API error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error updating PagerDuty incident: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def add_note(
        self,
        incident_id: str,
        note: str
    ) -> Dict[str, Any]:
        """
        Add a note to PagerDuty incident

        Args:
            incident_id: PagerDuty incident ID
            note: Note content

        Returns:
            Operation result
        """
        try:
            response = self.session.post(
                f"/incidents/{incident_id}/notes",
                json={
                    "note": {
                        "content": note
                    }
                }
            )

            logger.info(f"Added note to PagerDuty incident {incident_id}")

            return {
                "status": "success",
                "incident_id": incident_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        except pdpyras.PDClientError as e:
            logger.error(f"PagerDuty API error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error adding note to PagerDuty: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_incident_history(
        self,
        service_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get recent incident history

        Args:
            service_id: Optional service ID to filter by
            limit: Number of incidents to retrieve

        Returns:
            List of recent incidents
        """
        try:
            params = {
                "limit": limit,
                "sort_by": "created_at:desc",
                "statuses[]": ["resolved", "triggered", "acknowledged"]
            }

            if service_id:
                params["service_ids[]"] = [service_id]

            incidents = list(self.session.iter_all("/incidents", params=params))

            history = []
            for inc in incidents:
                history.append({
                    "id": inc.get("id"),
                    "incident_number": inc.get("incident_number"),
                    "title": inc.get("title"),
                    "status": inc.get("status"),
                    "created_at": inc.get("created_at"),
                    "resolved_at": inc.get("resolved_at"),
                    "service": inc.get("service", {}).get("summary")
                })

            return {
                "status": "success",
                "incidents": history,
                "total": len(history)
            }

        except pdpyras.PDClientError as e:
            logger.error(f"PagerDuty API error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error getting incident history: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
