# ShiftZero - Quick Start Guide

## What We've Built (Phase 1 Foundation)

✅ **Project Structure** - Complete with spec-driven development approach
✅ **AWS Bedrock Integration** - Claude client configured for your AWS setup
✅ **Configuration Management** - Environment-based settings with Pydantic
✅ **Safety Rules** - JSON-based autonomy boundaries and guardrails
✅ **System Prompts** - Comprehensive agent instructions with decision framework
✅ **Docker Setup** - Local development with PostgreSQL
✅ **Documentation** - Full technical specification (SPEC.md)

## Project Structure

```
shiftzero/
├── SPEC.md                    # Technical specification (READ THIS FIRST!)
├── README.md                  # Project overview
├── QUICKSTART.md              # This file
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image
├── docker-compose.yml         # Local dev environment
├── .env.example               # Environment template
├── config/
│   ├── safety_rules.json      # Autonomy boundaries & rate limits
│   └── prompts.py             # Agent system prompts
├── src/shiftzero/
│   ├── __init__.py
│   ├── config.py              # Settings management
│   ├── bedrock_client.py      # AWS Bedrock Claude wrapper
│   ├── models/                # (Next: Data models)
│   ├── services/              # (Next: Business logic)
│   └── tools/                 # (Next: K8s, PagerDuty tools)
└── tests/                     # (Next: Test suite)
```

## Next Steps (In Order)

### 1. Set Up Local Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials
```

### 2. Start PostgreSQL

```bash
# Start database
docker-compose up -d postgres

# Verify it's running
docker-compose ps
```

### 3. Implement Remaining Components

Refer to **SPEC.md Section 4 (Implementation Plan)** for the step-by-step checklist.

**Priority Order for Hackathon**:
1. ✅ Project Setup (DONE)
2. **Webhook Handler** (Task #3) - PagerDuty webhook receiver
3. **Tool Definitions** (Task #5) - K8s & PagerDuty integrations
4. **Agent Core** (Task #6) - Main autonomous loop
5. **Safety Rails** (Task #4) - Enforcement logic
6. **Layer 1 Noise** (Task #2) - (Optional for Phase 1)

### 4. Test Locally

```bash
# Run webhook server
python -m uvicorn shiftzero.webhook:app --reload

# In another terminal, send test webhook:
curl -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_pagerduty_alert.json
```

### 5. Demo Preparation

See **SPEC.md Section 6 (Demo Script)** for the 2-3 minute demo flow.

## Key Files to Read

1. **SPEC.md** - Complete technical specification
   - Architecture diagrams
   - Data models
   - Tool definitions
   - Safety rules
   - Implementation checklist

2. **config/prompts.py** - Agent system prompt
   - Shows exactly how the agent thinks
   - Decision framework
   - Example scenarios

3. **config/safety_rules.json** - Autonomy boundaries
   - What actions are auto-approved
   - What requires human approval
   - Rate limits and thresholds

## AWS Bedrock Notes

- Using `boto3` client (not Anthropic SDK)
- Model: `anthropic.claude-opus-4-6`
- Region: `us-east-1` (configurable in .env)
- Authentication: IAM credentials or AWS profile

The `bedrock_client.py` already handles:
- Session management
- Converse API calls
- Tool use support
- Response parsing

## Development Workflow

1. **Read SPEC.md** - Understand the full design
2. **Pick a task** - Follow the implementation plan
3. **Write tests first** - TDD approach recommended
4. **Implement** - Keep Phase 1 scope (one remediation action)
5. **Test locally** - Use docker-compose for dependencies
6. **Document** - Update SPEC.md if design changes

## Hackathon Tips

**Focus on the Demo**:
- Build ONE complete flow: Alert → Investigate → Restart Pod → Verify → Close
- Polish the happy path, handle errors gracefully
- Show the diagnostic report quality (this is your differentiator)

**Don't Overbuild**:
- Phase 1 is ONE remediation type (pod restart)
- Skip the noise detection layer initially (save for Phase 2)
- Use simple in-memory state instead of complex DB queries

**Wow Factors**:
- Real-time streaming of agent thinking
- Clear confidence scores with reasoning
- Beautiful diagnostic reports on escalation
- MTTR metrics (<60 seconds)

## Questions?

- Check SPEC.md first
- Review the system prompt in config/prompts.py
- Look at tool definitions in SPEC.md Section 3.3

## Current Tasks

Use these task IDs to track progress:
- #3: Implement PagerDuty webhook handler
- #5: Create MCP tool definitions and integrations
- #6: Build Layer 2 - Autonomous Investigation & Remediation
- #4: Add safety rails and autonomy boundaries
- #2: Build Layer 1 - Noise Elimination system (Phase 2)

---

**Ready to build?** Start with Task #3 (webhook handler) next!
