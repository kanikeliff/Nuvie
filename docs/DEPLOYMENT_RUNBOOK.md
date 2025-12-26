# Nuvie Deployment Runbook

This runbook provides step-by-step procedures for deploying Nuvie to production environments.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Backend Deployment](#backend-deployment)
4. [AI Service Deployment](#ai-service-deployment)
5. [iOS App Deployment](#ios-app-deployment)
6. [Database Migrations](#database-migrations)
7. [Rollback Procedures](#rollback-procedures)
8. [Health Checks](#health-checks)
9. [Monitoring & Alerts](#monitoring--alerts)
10. [Incident Response](#incident-response)

---

## Deployment Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                    (AWS ALB / CloudFlare)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│    Backend API (K8s)    │   │    AI Service (K8s)     │
│    - 3 replicas min     │   │    - 2 replicas min     │
│    - HPA enabled        │   │    - GPU optional       │
└───────────┬─────────────┘   └───────────┬─────────────┘
            │                             │
            └─────────────┬───────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌───────────┐ ┌─────────────────┐
│   PostgreSQL    │ │   Redis   │ │   Object Store  │
│   (RDS/Aurora)  │ │(ElastiCache│ │    (S3)        │
└─────────────────┘ └───────────┘ └─────────────────┘
```

### Deployment Environments

| Environment | Purpose | Update Frequency |
|-------------|---------|------------------|
| Development | Feature testing | On commit |
| Staging | Pre-production validation | Daily |
| Production | Live users | Weekly (scheduled) |

---

## Pre-Deployment Checklist

### Code Quality Gates

- [ ] All CI checks passing (lint, typecheck, security, tests)
- [ ] Code review approved (2+ reviewers)
- [ ] No critical or high severity security issues
- [ ] Test coverage meets threshold (>80%)
- [ ] API documentation updated

### Infrastructure Readiness

- [ ] Database migrations tested in staging
- [ ] Redis cache cleared if schema changes
- [ ] Environment variables verified
- [ ] SSL certificates valid (>30 days)
- [ ] DNS records configured

### Communication

- [ ] Deployment window scheduled
- [ ] Team notified in #deployments channel
- [ ] Status page updated (if applicable)
- [ ] Customer support briefed on changes

---

## Backend Deployment

### Step 1: Build and Push Docker Image

```bash
# Set version tag
export VERSION=$(git describe --tags --always)
export REGISTRY=your-registry.azurecr.io

# Build image
docker build \
  -t $REGISTRY/nuvie-backend:$VERSION \
  -t $REGISTRY/nuvie-backend:latest \
  backend/

# Push to registry
docker push $REGISTRY/nuvie-backend:$VERSION
docker push $REGISTRY/nuvie-backend:latest
```

### Step 2: Update Kubernetes Deployment

```bash
# Update image in deployment
kubectl set image deployment/nuvie-backend \
  backend=$REGISTRY/nuvie-backend:$VERSION \
  -n nuvie-production

# Watch rollout status
kubectl rollout status deployment/nuvie-backend -n nuvie-production
```

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -n nuvie-production -l app=nuvie-backend

# Check logs for errors
kubectl logs -n nuvie-production -l app=nuvie-backend --tail=100

# Test health endpoint
curl https://api.nuvie.app/health
```

### Step 4: Run Smoke Tests

```bash
# Run automated smoke tests
./scripts/smoke-test-backend.sh production

# Expected output:
# ✓ Health check passed
# ✓ Authentication working
# ✓ Feed endpoint responding
# ✓ Rate limiting active
```

---

## AI Service Deployment

### Step 1: Build and Push

```bash
export VERSION=$(git describe --tags --always)

docker build \
  -t $REGISTRY/nuvie-ai:$VERSION \
  aii/

docker push $REGISTRY/nuvie-ai:$VERSION
```

### Step 2: Deploy with Model

```bash
# Ensure model artifact is available
aws s3 cp s3://nuvie-models/ibcf-v2.pkl ./models/

# Update deployment
kubectl set image deployment/nuvie-ai \
  ai=$REGISTRY/nuvie-ai:$VERSION \
  -n nuvie-production

# Wait for model to load (check logs)
kubectl logs -f deployment/nuvie-ai -n nuvie-production
```

### Step 3: Verify Model Health

```bash
# Check model is loaded
curl https://ai.nuvie.app/health

# Expected response:
# {"status":"healthy","model_loaded":true,"version":"..."}

# Test recommendation
curl -X POST https://ai.nuvie.app/ai/recommend \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $AI_TOKEN" \
  -d '{"user_id": 1, "limit": 5}'
```

---

## iOS App Deployment

### Step 1: Prepare Release Build

```bash
# Increment version in Xcode
# Project → General → Version

# Create archive
xcodebuild archive \
  -project Nuvie.xcodeproj \
  -scheme Nuvie \
  -configuration Release \
  -archivePath build/Nuvie.xcarchive
```

### Step 2: Export IPA

```bash
# Export for App Store
xcodebuild -exportArchive \
  -archivePath build/Nuvie.xcarchive \
  -exportPath build/ \
  -exportOptionsPlist ExportOptions.plist
```

### Step 3: Upload to App Store Connect

```bash
# Using altool
xcrun altool --upload-app \
  -f build/Nuvie.ipa \
  -t ios \
  -u $APPLE_ID \
  -p $APP_SPECIFIC_PASSWORD
```

### Step 4: Submit for Review

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Select Nuvie app
3. Add build to new version
4. Complete metadata and screenshots
5. Submit for review

---

## Database Migrations

### Running Migrations

```bash
# Backup database first
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d-%H%M%S).sql

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

### Migration Safety Rules

1. **Always backup first** - No exceptions
2. **Test in staging** - Run migrations on staging before production
3. **Avoid locks** - Use `CONCURRENTLY` for index creation
4. **Rollback plan** - Have downgrade script ready

### Example Safe Migration

```python
# migrations/versions/20231226_add_index.py
def upgrade():
    # Use CONCURRENTLY to avoid locking
    op.execute("""
        CREATE INDEX CONCURRENTLY ix_users_email_active
        ON users (email, is_active)
    """)

def downgrade():
    op.drop_index("ix_users_email_active")
```

---

## Rollback Procedures

### Backend Rollback

```bash
# Quick rollback to previous version
kubectl rollout undo deployment/nuvie-backend -n nuvie-production

# Rollback to specific revision
kubectl rollout undo deployment/nuvie-backend \
  --to-revision=5 \
  -n nuvie-production

# Verify rollback
kubectl rollout status deployment/nuvie-backend -n nuvie-production
```

### Database Rollback

```bash
# Restore from backup
psql $DATABASE_URL < backup-20231226-143000.sql

# Or downgrade migration
alembic downgrade -1
```

### Emergency Procedures

```bash
# Scale down to 0 if critical issue
kubectl scale deployment/nuvie-backend --replicas=0 -n nuvie-production

# Enable maintenance mode (if configured)
kubectl set env deployment/nuvie-backend MAINTENANCE_MODE=true
```

---

## Health Checks

### Endpoint Definitions

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Liveness probe | `{"status":"healthy"}` |
| `/ready` | Readiness probe | `{"status":"ready","checks":{...}}` |
| `/metrics` | Prometheus metrics | Prometheus format |

### Automated Health Monitoring

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error rate (5xx) | >1% | >5% | Check logs, consider rollback |
| Response time (p95) | >500ms | >2000ms | Scale up, optimize queries |
| CPU utilization | >70% | >90% | Scale horizontally |
| Memory utilization | >80% | >95% | Investigate leaks, scale up |
| Circuit breaker open | Any | >5min | Check AI service |
| Redis connection | Any failure | >1min | Check Redis health |

### Alert Configuration

```yaml
# Prometheus alerting rules
groups:
  - name: nuvie-backend
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times detected"
```

---

## Incident Response

### Severity Levels

| Level | Impact | Response Time | Examples |
|-------|--------|---------------|----------|
| P1 - Critical | Complete outage | 15 min | API down, auth broken |
| P2 - Major | Significant degradation | 1 hour | Slow responses, partial failures |
| P3 - Minor | Limited impact | 4 hours | Single feature broken |
| P4 - Low | Minimal impact | 24 hours | UI glitch, non-critical bugs |

### Incident Workflow

1. **Detect** - Alert triggered or user report
2. **Acknowledge** - Assign incident commander
3. **Diagnose** - Check dashboards, logs, traces
4. **Mitigate** - Rollback, scale, hotfix
5. **Resolve** - Confirm fix, update status
6. **Post-mortem** - Document lessons learned

### Useful Commands During Incidents

```bash
# Get recent error logs
kubectl logs -n nuvie-production -l app=nuvie-backend \
  --since=5m | grep -i error

# Check resource usage
kubectl top pods -n nuvie-production

# Describe pod for events
kubectl describe pod <pod-name> -n nuvie-production

# Check circuit breaker status
curl https://api.nuvie.app/metrics | grep circuit

# Force cache clear
redis-cli -h $REDIS_HOST FLUSHDB
```

---

## Appendix

### Deployment Schedule

| Day | Time (UTC) | Type |
|-----|------------|------|
| Tuesday | 14:00-16:00 | Routine releases |
| Thursday | 14:00-16:00 | Routine releases |
| Any | As needed | Emergency hotfixes |

### Contact List

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | PagerDuty | Auto-escalate 15min |
| Engineering Manager | Slack @eng-manager | Manual |
| Infrastructure | Slack #infra | Manual |

### Related Documents

- [Architecture Documentation](../Architecture.md)
- [Development Setup](./DEVELOPMENT_SETUP.md)
- [API Documentation](https://api.nuvie.app/docs)
- [Security Guidelines](./SECURITY.md)
