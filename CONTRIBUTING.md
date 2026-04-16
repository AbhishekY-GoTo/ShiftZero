# Contributing to ShiftZero

This guide helps engineers understand the codebase and extend functionality to production-grade.

## Quick Start for Engineers

```bash
git clone https://github.com/AbhishekY-GoTo/ShiftZero.git
cd ShiftZero
./setup.sh
cp .env.example .env
# Edit .env with your credentials
python main.py
```

## Project Architecture

### Core Components

```
src/shiftzero/
├── agent.py           # Main autonomous agent (investigation → remediation loop)
├── webhook.py         # FastAPI server for PagerDuty webhooks
├── bedrock_client.py  # AWS Bedrock Claude API wrapper
├── config.py          # Configuration management (Pydantic)
├── models/            # Data models (Incident, PagerDuty)
├── services/          # Safety guard and rate limiting
└── tools/             # Kubernetes, PagerDuty, escalation tools
```

### How It Works

1. **Webhook receives PagerDuty alert** → `webhook.py`
2. **Agent investigates** → `agent.py` calls Claude via Bedrock
3. **Tools execute** → Kubernetes/PagerDuty operations
4. **Safety checks** → `services/safety.py` validates actions
5. **Remediate or escalate** → Based on confidence score

## Adding New Tools

### 1. Implement the Tool Function

Create in `src/shiftzero/tools/your_tool.py`:

```python
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def scale_deployment(namespace: str, deployment: str, replicas: int) -> Dict[str, Any]:
    """
    Scale a Kubernetes deployment.
    
    Args:
        namespace: K8s namespace
        deployment: Deployment name
        replicas: Target replica count
    
    Returns:
        Dict with 'success' and 'message' or 'error'
    """
    try:
        # Your implementation
        return {"success": True, "message": f"Scaled {deployment} to {replicas}"}
    except Exception as e:
        logger.error(f"Scale failed: {e}")
        return {"success": False, "error": str(e)}
```

### 2. Add Tool Definition

Add to `src/shiftzero/tools/definitions.py`:

```python
{
    "toolSpec": {
        "name": "scale_deployment",
        "description": "Scale a Kubernetes deployment to handle load changes",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "K8s namespace"},
                    "deployment": {"type": "string", "description": "Deployment name"},
                    "replicas": {"type": "integer", "description": "Target replicas"}
                },
                "required": ["namespace", "deployment", "replicas"]
            }
        }
    }
}
```

### 3. Register in Agent

Update `src/shiftzero/agent.py` in the tool execution section:

```python
from shiftzero.tools.your_tool import scale_deployment

# In handle_incident() tool execution:
elif tool_name == "scale_deployment":
    result = await scale_deployment(
        namespace=tool_input["namespace"],
        deployment=tool_input["deployment"],
        replicas=tool_input["replicas"]
    )
```

### 4. Add Safety Rules

Update `config/safety_rules.json`:

```json
{
  "approved_actions": ["scale_deployment"],
  "action_constraints": {
    "scale_deployment": {
      "requires_confidence": 0.85,
      "max_replicas": 10,
      "allowed_criticality_levels": ["low", "medium"]
    }
  }
}
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | ✅ | AWS region for Bedrock |
| `BEDROCK_MODEL_ID` | ✅ | Claude model ARN or ID |
| `PAGERDUTY_API_KEY` | ✅ | PagerDuty API key |
| `PAGERDUTY_WEBHOOK_SECRET` | ✅ | Webhook signature secret |
| `KUBECONFIG` | ❌ | Path to K8s config |
| `SLACK_BOT_TOKEN` | ❌ | Slack bot token |
| `DRY_RUN_MODE` | ❌ | `true` for testing |

### Safety Thresholds

- `MAX_AUTO_RESTARTS_PER_HOUR=3` - Rate limit
- `CONFIDENCE_THRESHOLD_AUTO_REMEDIATE=0.85` - Min confidence for auto-action
- `CONFIDENCE_THRESHOLD_ESCALATE=0.70` - Min confidence for escalation

## Testing

### Unit Tests

```bash
pytest tests/
pytest --cov=src/shiftzero tests/  # With coverage
```

### Integration Test

```bash
# Terminal 1: Start server
python main.py

# Terminal 2: Send test webhook
./tests/test_webhook.sh

# Watch logs
tail -f shiftzero.log
```

### Testing with Real PagerDuty

1. Set `DRY_RUN_MODE=false` in `.env`
2. Configure PagerDuty webhook to point to your server
3. Trigger test incident
4. Watch `server.log` for agent reasoning

## Security Best Practices

### Credential Management

- ✅ **DO**: Use `.env` for secrets (git-ignored)
- ✅ **DO**: Use IAM roles instead of access keys when possible
- ❌ **DON'T**: Hardcode credentials in code
- ❌ **DON'T**: Commit `.env` files

### Safe Tool Design

- **Idempotent**: Safe to retry (e.g., restart already-running pod)
- **Validated**: Check inputs before execution
- **Reversible**: Support rollback when possible
- **Audited**: Log all actions with context
- **Rate-limited**: Prevent runaway automation

### Example Safety Check

```python
def is_action_safe(action: str, service: str, confidence: float) -> bool:
    if service in HIGH_CRITICALITY_SERVICES and confidence < 0.95:
        return False
    if action == "restart_deployment" and get_recent_restart_count(service) >= 3:
        return False
    return True
```

## Common Extensions

### 1. Add Slack Notifications (20 min)

```python
# src/shiftzero/tools/slack.py
async def post_to_slack(channel: str, message: str):
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    # Use slack_sdk to post message
```

### 2. Add Metrics Dashboard (2 hours)

- Track MTTR, success rate, confidence scores
- Use Grafana or custom dashboard
- Store metrics in Prometheus

### 3. Layer 1: Noise Elimination (4-6 hours)

- Analyze alert patterns over time
- Detect false positives
- Recommend PagerDuty rule changes
- See `SPEC.md` for architecture

### 4. Database Persistence (2-3 hours)

- Add PostgreSQL for incident history
- Use SQLAlchemy models
- Enable pattern matching

## Code Style

- Follow PEP 8
- Use type hints: `def func(arg: str) -> Dict[str, Any]`
- Write docstrings (Google style)
- Use async/await for I/O operations
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)

## Pull Request Process

1. **Create branch**: `git checkout -b feature/my-feature`
2. **Make changes**: Implement + test
3. **Commit**: Clear message describing changes
4. **Push**: `git push origin feature/my-feature`
5. **Create PR**: On GitHub with description

### PR Checklist

- [ ] Tests pass locally
- [ ] No hardcoded credentials
- [ ] Documentation updated
- [ ] Safety rules considered
- [ ] Logging added

## Next Steps

See [ROADMAP.md](ROADMAP.md) for planned features and priorities.

## Getting Help

- Check `SPEC.md` for architecture details
- Check `IMPLEMENTATION_STATUS.md` for current status
- Check `server.log` for runtime debugging
- Open GitHub issue for bugs/questions

---

**Ready to build?** Start with QUICKSTART.md, then dive into the code! 🚀
