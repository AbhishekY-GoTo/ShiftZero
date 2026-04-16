# ShiftZero - Autonomous On-Call Agent

ShiftZero is an AI-powered on-call agent that eliminates alert noise and autonomously handles incident response.

## Architecture

```
INCOMING PAGERDUTY ALERT
          │
          ▼
┌─────────────────────────┐
│   LAYER 1: NOISE FILTER  │
│                         │
│  Is this alert needed?  │
│  - Recurring false +ve? │
│  - No action ever taken?│
└──────┬──────────────────┘
       │
    NOISY ──────────────► Flag for PagerDuty rule removal
       │                  (agent gets quieter over time)
   NOT NOISY
       │
       ▼
┌──────────────────────────────┐
│   LAYER 2: AUTONOMOUS TRIAGE  │
│                              │
│  1. RUN TESTS                │
│     Validate: is issue real? │
│                              │
│  2. INVESTIGATE              │
│     Logs, metrics, traces    │
│     Pinpoint root cause      │
│                              │
│  3. REMEDIATE                │
│     Within approved scope:   │
│     • Restart service        │
│     • Scale pod              │
│     • Flush cache            │
│     • Re-trigger pipeline    │
│     • Rollback deployment    │
│                              │
│  4. VERIFY                   │
│     Run tests again          │
│     Confirm fix worked       │
│                              │
│  5. CLOSE PD INCIDENT        │
│     Log actions taken        │
│     Post summary to Slack    │
└──────┬───────────────────────┘
       │
  OUT OF SCOPE?
       │
       ▼
┌──────────────────────────────┐
│   ESCALATE TO HUMAN          │
│   But with FULL REPORT:      │
│   ✓ What was tested          │
│   ✓ Root cause hypothesis    │
│   ✓ What was tried           │
│   ✓ Recommended next steps   │
└──────────────────────────────┘
```

## Components

- **agent.py**: Core autonomous agent using Claude Agent SDK
- **webhook.py**: FastAPI server for receiving PagerDuty webhooks
- **layer1_noise.py**: Alert pattern analysis and noise elimination
- **layer2_remediation.py**: Investigation and remediation logic
- **tools/**: MCP tool definitions for infrastructure access
- **config/**: Safety rules and autonomy boundaries

## Quick Start

1. Install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the agent:
```bash
python main.py
```

4. Configure PagerDuty webhook:
   - Point to: `http://your-domain:8000/webhook/pagerduty`

## Configuration

See `config/safety_rules.json` for autonomy boundaries and approved actions.

## Development

- Built with Claude Opus 4.6 via Agent SDK
- Uses MCP servers for tool access (K8s, PagerDuty, Observability)
- FastAPI for webhook handling
- PostgreSQL for pattern learning and incident history

## License

MIT
