"""FastAPI webhook server for receiving PagerDuty alerts"""

import asyncio
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse

from .models import PagerDutyWebhook, Incident, IncidentStatus
from .config import get_settings
from .agent import ShiftZeroAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ShiftZero Webhook Server",
    description="Autonomous on-call incident response agent",
    version="0.1.0"
)

# Initialize agent
agent = ShiftZeroAgent()
settings = get_settings()


def verify_pagerduty_signature(
    payload: bytes,
    signature: Optional[str],
    webhook_secret: str
) -> bool:
    """
    Verify PagerDuty webhook signature

    Args:
        payload: Raw request body
        signature: X-PagerDuty-Signature header
        webhook_secret: Configured webhook secret

    Returns:
        True if signature is valid
    """
    if not signature or not webhook_secret:
        logger.warning("Missing signature or webhook secret")
        return False

    # PagerDuty uses HMAC-SHA256
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures (constant-time comparison)
    return hmac.compare_digest(
        f"v1={expected_signature}",
        signature
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "shiftzero",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_status": "online"
    }


@app.post("/webhook/pagerduty")
async def receive_pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pagerduty_signature: Optional[str] = Header(None)
):
    """
    Receive PagerDuty webhook and trigger autonomous response

    PagerDuty sends webhooks for various incident events.
    We only process incident.triggered events.
    """
    try:
        # Get raw body for signature verification
        raw_body = await request.body()

        # Verify webhook signature (skip in dry-run mode for testing)
        if not settings.dry_run_mode:
            if not verify_pagerduty_signature(
                raw_body,
                x_pagerduty_signature,
                settings.pagerduty_webhook_secret
            ):
                logger.error("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse webhook payload
        webhook_data = await request.json()
        webhook = PagerDutyWebhook(**webhook_data)

        logger.info(f"Received webhook with {len(webhook.messages)} message(s)")

        # Only process triggered events
        if not webhook.is_triggered_event():
            logger.info("Webhook is not a trigger event, ignoring")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": "not_a_trigger_event"}
            )

        # Extract incident details
        pd_incident = webhook.get_first_incident()
        if not pd_incident:
            logger.warning("No incident found in webhook")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": "no_incident"}
            )

        # Create internal incident record
        incident = Incident(
            incident_id=pd_incident.id,
            timestamp=pd_incident.created_at,
            service=pd_incident.service.name,
            alert_type=extract_alert_type(pd_incident.title),
            severity=pd_incident.urgency,
            title=pd_incident.title,
            description=pd_incident.description,
            raw_payload=webhook_data
        )

        logger.info(
            f"Created incident {incident.incident_id} for service {incident.service}"
        )

        # Process incident asynchronously (don't block webhook response)
        background_tasks.add_task(process_incident, incident)

        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "incident_id": incident.incident_id,
                "message": "Incident received, processing in background"
            }
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def process_incident(incident: Incident):
    """
    Process incident asynchronously

    This is the main entry point for the ShiftZero agent.
    It runs in the background after webhook is acknowledged.
    """
    try:
        logger.info(f"Starting autonomous response for incident {incident.incident_id}")

        # Update status
        incident.status = IncidentStatus.INVESTIGATING

        # Invoke the agent
        await agent.handle_incident(incident)

        logger.info(
            f"Completed processing incident {incident.incident_id}. "
            f"Status: {incident.status}, "
            f"Resolution time: {incident.resolution_time_seconds}s"
        )

    except Exception as e:
        logger.error(
            f"Error processing incident {incident.incident_id}: {e}",
            exc_info=True
        )
        incident.status = IncidentStatus.FAILED


def extract_alert_type(title: str) -> str:
    """
    Extract alert type from incident title

    Examples:
      "Pod api-service-xyz is CrashLooping" -> "PodCrashLooping"
      "High CPU usage on node-123" -> "HighCPU"
      "Database connection pool exhausted" -> "DatabaseConnectionPool"
    """
    title_lower = title.lower()

    # Pattern matching for common alert types
    if "crashloop" in title_lower or "crash" in title_lower:
        return "PodCrashLooping"
    elif "oom" in title_lower or "memory" in title_lower:
        return "OutOfMemory"
    elif "cpu" in title_lower:
        return "HighCPU"
    elif "disk" in title_lower:
        return "DiskSpace"
    elif "connection" in title_lower and "pool" in title_lower:
        return "ConnectionPoolExhausted"
    elif "timeout" in title_lower:
        return "Timeout"
    elif "503" in title_lower or "unavailable" in title_lower:
        return "ServiceUnavailable"
    else:
        return "Unknown"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level=settings.log_level.lower()
    )
