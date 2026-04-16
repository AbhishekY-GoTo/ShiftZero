# ShiftZero - Technical Specification

## 1. Overview

**Problem**: GoTo engineers trapped in 24/7 on-call responding to noisy alerts and repeatable incidents.

**Solution**: AI agent that eliminates noise and autonomously handles incidents.

**Tech Stack**: 
- AWS Bedrock (Claude Opus)
- FastAPI (webhook receiver)
- PostgreSQL (incident history)
- MCP Servers (tool integrations)

---

## 2. Release Phases

### Phase 1: MVP - Basic Autonomous Remediation (Hackathon Demo)
**Goal**: Demonstrate one end-to-end autonomous incident resolution

**Scope**:
- ✅ Receive PagerDuty webhook
- ✅ Simple classification (noisy vs. actionable)
- ✅ ONE remediation action: Restart unhealthy Kubernetes pod
- ✅ Verify fix worked
- ✅ Close PagerDuty incident
- ✅ Escalate if unsure (with diagnostic report)

**Demo Flow**:
```
PagerDuty Alert: "Pod api-service-xyz is CrashLooping"
    ↓
Agent investigates: Check pod logs, check recent deployments
    ↓
Agent decides: "Likely OOM issue, safe to restart"
    ↓
Agent acts: kubectl rollout restart deployment api-service
    ↓
Agent verifies: Pod is now healthy
    ↓
Agent closes: Update PagerDuty with resolution notes
```

**Success Metrics**:
- Alert → Resolution in <60 seconds
- No human intervention needed
- Incident properly documented

---

### Phase 2: Noise Elimination Layer
**Goal**: Reduce alert surface over time

**Scope**:
- Pattern detection for recurring false positives
- Alert frequency analysis
- Recommendation engine for alert removal
- Dashboard showing noise reduction over time

---

### Phase 3: Expanded Remediation Playbook
**Goal**: Handle more incident types autonomously

**Scope**:
- Scale pods (handle load spikes)
- Flush cache (handle stale data)
- Re-trigger failed pipelines
- Rollback bad deployments
- Database connection pool adjustments

---

### Phase 4: Continuous Learning
**Goal**: Agent gets smarter over time

**Scope**:
- Learn from successful remediations
- Build incident similarity matching
- Auto-suggest new playbook entries
- Confidence scoring improvements

---

## 3. Architecture Specification

### 3.1 System Components

```
┌─────────────────────────────────────────────────────────┐
│                     PagerDuty                           │
│                 (Alert Source)                          │
└────────────────────┬────────────────────────────────────┘
                     │ webhook POST
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Webhook Server                      │
│              (webhook.py)                                │
│  - Receive alerts                                        │
│  - Authenticate webhook                                  │
│  - Queue for processing                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              ShiftZero Agent                             │
│              (agent.py)                                  │
│  - AWS Bedrock Claude Opus                               │
│  - Autonomous decision-making                            │
│  - Tool orchestration                                    │
└────────┬────────────────────────────┬───────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐        ┌──────────────────┐
│  Layer 1 Module  │        │  Layer 2 Module  │
│  (noise.py)      │        │ (remediation.py) │
│                  │        │                  │
│  - Pattern match │        │  - Investigate   │
│  - False +ve     │        │  - Remediate     │
│  - Recommend     │        │  - Verify        │
│    removal       │        │  - Escalate      │
└──────────────────┘        └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │   MCP Tools      │
                            │                  │
                            │  - Kubernetes    │
                            │  - PagerDuty     │
                            │  - Observability │
                            │  - Database      │
                            └──────────────────┘
```

### 3.2 Data Models

#### Incident Record
```python
{
    "incident_id": "PD123456",
    "timestamp": "2026-04-16T08:00:00Z",
    "service": "api-service",
    "alert_type": "PodCrashLooping",
    "severity": "high",
    "raw_payload": {...},
    
    # Layer 1 Analysis
    "is_noise": false,
    "noise_confidence": 0.15,
    "similar_incidents_count": 3,
    
    # Layer 2 Analysis
    "investigation_summary": "Pod restarting due to OOM...",
    "root_cause": "memory_limit_exceeded",
    "remediation_action": "restart_deployment",
    "action_confidence": 0.92,
    
    # Outcome
    "resolution_status": "auto_resolved",
    "resolution_time_seconds": 45,
    "verification_passed": true,
    "escalated_to_human": false
}
```

#### Alert Pattern
```python
{
    "pattern_id": "PAT001",
    "alert_signature": "DiskSpace > 80%",
    "service": "monitoring-agent",
    "occurrences": 47,
    "false_positive_rate": 0.98,
    "actions_taken_count": 0,
    "recommendation": "remove_alert",
    "confidence": 0.95,
    "created_at": "2026-03-01",
    "last_seen": "2026-04-16"
}
```

### 3.3 Tool Definitions (Phase 1 MVP)

#### Tool 1: get_pod_status
```python
{
    "name": "get_pod_status",
    "description": "Get Kubernetes pod status, health, and recent events",
    "input_schema": {
        "namespace": "string",
        "pod_name": "string"
    },
    "output": {
        "status": "CrashLoopBackOff|Running|Pending",
        "restart_count": 15,
        "last_restart": "2026-04-16T07:58:00Z",
        "events": ["OOMKilled", "Back-off restarting"],
        "resource_usage": {"memory": "512Mi/500Mi", "cpu": "200m/500m"}
    }
}
```

#### Tool 2: get_pod_logs
```python
{
    "name": "get_pod_logs",
    "description": "Retrieve recent logs from a pod",
    "input_schema": {
        "namespace": "string",
        "pod_name": "string",
        "lines": "int (default: 100)"
    },
    "output": "string (log content)"
}
```

#### Tool 3: restart_deployment
```python
{
    "name": "restart_deployment",
    "description": "Perform rolling restart of a deployment",
    "input_schema": {
        "namespace": "string",
        "deployment_name": "string",
        "reason": "string"
    },
    "requires_approval": false,  # Phase 1: auto-approved
    "safety_checks": [
        "max_3_restarts_per_hour",
        "not_in_deployment_window"
    ]
}
```

#### Tool 4: update_pagerduty_incident
```python
{
    "name": "update_pagerduty_incident",
    "description": "Update or resolve PagerDuty incident",
    "input_schema": {
        "incident_id": "string",
        "status": "acknowledged|resolved",
        "resolution_note": "string"
    }
}
```

#### Tool 5: escalate_to_oncall
```python
{
    "name": "escalate_to_oncall",
    "description": "Escalate to human with diagnostic report",
    "input_schema": {
        "incident_id": "string",
        "diagnostic_summary": "string",
        "root_cause_hypothesis": "string",
        "actions_attempted": ["string"],
        "recommended_next_steps": "string"
    }
}
```

### 3.4 Safety Rules (Phase 1)

```json
{
    "approved_autonomous_actions": [
        "restart_deployment",
        "get_pod_status",
        "get_pod_logs",
        "check_deployment_history"
    ],
    
    "require_human_approval": [
        "scale_deployment",
        "rollback_deployment",
        "delete_resources"
    ],
    
    "rate_limits": {
        "restart_deployment": {
            "max_per_hour": 3,
            "max_per_service": 1
        }
    },
    
    "confidence_thresholds": {
        "auto_remediate": 0.85,
        "recommend_with_approval": 0.70,
        "escalate_immediately": 0.70
    },
    
    "always_escalate": [
        "security_incidents",
        "data_loss_alerts",
        "production_database_alerts"
    ]
}
```

### 3.5 Agent Prompt Template

```python
SYSTEM_PROMPT = """You are ShiftZero, an autonomous on-call incident response agent for GoTo's infrastructure.

Your mission: Reduce MTTR and eliminate alert noise so engineers can sleep through the night.

## Your Capabilities

1. **INVESTIGATE**: Analyze alerts, check pod status, review logs, examine metrics
2. **REMEDIATE**: Execute approved fixes (restart pods, scale resources)
3. **VERIFY**: Confirm fixes worked before closing incidents
4. **ESCALATE**: Alert humans with full diagnostic reports when needed

## Decision Framework

**When to AUTO-REMEDIATE** (confidence ≥ 0.85):
- Pod CrashLooping with OOM errors → Restart
- Known transient failures → Standard fix
- Low-impact, well-understood issues → Execute playbook

**When to ESCALATE** (confidence < 0.85):
- Unfamiliar error patterns
- High-impact services
- Multiple failed remediation attempts
- Outside approved action scope

## Safety Rules (CRITICAL)
- MAX 3 pod restarts per hour per service
- NEVER delete resources without approval
- ALWAYS verify fixes worked before closing incidents
- ESCALATE security incidents immediately

## Your Response Format

1. **Investigation Summary**: What you found
2. **Root Cause**: Your hypothesis (with confidence %)
3. **Action Plan**: What you'll do or why you're escalating
4. **Verification**: How you'll confirm it worked

Be thorough but fast. MTTR matters.
"""
```

---

## 4. Implementation Plan (Phase 1)

### Step 1: Project Setup
- [ ] Initialize project structure
- [ ] Configure AWS Bedrock credentials
- [ ] Set up PostgreSQL database
- [ ] Create Docker Compose for local dev

### Step 2: Webhook Handler
- [ ] FastAPI endpoint for PagerDuty webhooks
- [ ] Webhook signature verification
- [ ] Parse alert payload
- [ ] Store incident in database

### Step 3: Agent Core
- [ ] AWS Bedrock client setup
- [ ] Agent conversation loop
- [ ] Tool execution framework
- [ ] State management

### Step 4: Tool Integrations
- [ ] Kubernetes MCP server (or direct kubectl)
- [ ] PagerDuty API integration
- [ ] Database query tools

### Step 5: Remediation Logic
- [ ] Implement restart_deployment action
- [ ] Add safety checks
- [ ] Verification logic
- [ ] Incident closure

### Step 6: Testing
- [ ] Unit tests for tools
- [ ] Integration test with mock PagerDuty
- [ ] End-to-end test with real K8s cluster
- [ ] Load testing

### Step 7: Demo Prep
- [ ] Create demo incident scenario
- [ ] Build simple monitoring dashboard
- [ ] Prepare metrics/charts
- [ ] Script the demo flow

---

## 5. Success Criteria (Phase 1)

**Functional**:
- ✅ Agent successfully handles 1 incident end-to-end
- ✅ Incident resolved in <60 seconds
- ✅ Proper escalation when confidence is low
- ✅ All actions logged and auditable

**Non-Functional**:
- ✅ No false positive remediations
- ✅ Agent never violates safety rules
- ✅ Clear audit trail in database
- ✅ Graceful failure handling

---

## 6. Demo Script

**Setup**: Pre-deployed unhealthy pod in test K8s cluster

**Flow**:
1. Trigger PagerDuty alert manually
2. Show webhook received in logs
3. Show agent investigation in real-time
4. Show agent decision + confidence score
5. Show remediation execution
6. Show verification passing
7. Show PagerDuty incident auto-closed
8. Show database record with full audit trail

**Time**: 2-3 minutes total

---

## 7. Future Considerations

### Observability
- Prometheus metrics for agent performance
- Grafana dashboard for MTTR tracking
- Alert noise reduction over time chart

### Multi-tenancy
- Support multiple teams/services
- Per-team autonomy boundaries
- Custom playbooks per service

### Learning
- Vector embeddings for incident similarity
- Confidence score improvements from feedback
- Auto-discovery of new playbook patterns

---

## Appendix A: AWS Bedrock Setup

```python
import boto3

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

def invoke_claude(messages, tools):
    response = bedrock_runtime.converse(
        modelId='anthropic.claude-opus-4-6',
        messages=messages,
        inferenceConfig={
            'maxTokens': 4096,
            'temperature': 0.0
        },
        toolConfig={'tools': tools}
    )
    return response
```

---

**Last Updated**: 2026-04-16
**Version**: 1.0 (Phase 1 Spec)
