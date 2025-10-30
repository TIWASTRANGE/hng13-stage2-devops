
## Stage 3: Observability & Alerts

### Overview

Stage 3 adds operational visibility and Slack alerting to the Blue/Green deployment:

- **Enhanced Logging**: Nginx logs capture pool, release, status, and latency
- **Real-time Monitoring**: Python watcher tails logs and detects issues
- **Slack Alerts**: Automatic notifications for failovers and high error rates
- **Runbook**: Operator guide for responding to alerts

### Prerequisites

1. Complete Stage 2 setup
2. Create a Slack webhook (see below)

### Slack Webhook Setup

1. Go to https://api.slack.com/messaging/webhooks
2. Create a new app in your workspace
3. Enable "Incoming Webhooks"
4. Add webhook to a channel (e.g., #alerts)
5. Copy the webhook URL
6. Add to `.env`:
```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Quick Start
```bash
# Configure environment
cp .env.example .env
nano .env  # Add your Slack webhook URL

# Start all services
docker compose up -d

# Verify watcher is running
docker compose logs -f alert_watcher
```

### Testing Alerts

#### Test 1: Failover Alert
```bash
# 1. Trigger chaos on Blue
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 2. Generate traffic to trigger failover
for i in {1..10}; do
  curl http://localhost:8080/version
  sleep 0.5
done

# 3. Check Slack for failover alert
# 4. Verify in logs
docker compose logs alert_watcher
```

**Expected:** Slack message showing failover from Blue to Green

#### Test 2: High Error Rate Alert
```bash
# 1. Ensure Blue is active and trigger chaos
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# 2. Generate enough traffic to exceed 2% error threshold
# Need ~5+ errors in 200 requests
for i in {1..250}; do
  curl -s http://localhost:8080/version > /dev/null
  sleep 0.1
done

# 3. Check Slack for error rate alert
# 4. Verify in logs
docker compose logs alert_watcher | grep "ERROR"

# 5. Stop chaos
curl -X POST "http://localhost:8081/chaos/stop"
```

**Expected:** Slack message showing error rate exceeded threshold

### Viewing Logs

#### Nginx Access Logs (Structured)
```bash
# View recent logs
docker compose exec nginx tail -50 /var/log/nginx/access.log

# Filter by pool
docker compose exec nginx grep "pool=blue" /var/log/nginx/access.log | tail -10

# Check for errors
docker compose exec nginx grep "upstream_status=5" /var/log/nginx/access.log
```

**Sample log line:**
```
172.18.0.1 - - [25/Oct/2025:15:30:45 +0000] "GET /version HTTP/1.1" 200 57 
"-" "curl/7.81.0" pool=blue release=blue-v1.0.0 upstream_status=200 
upstream_addr=172.18.0.2:3000 request_time=0.045 upstream_response_time=0.042
```

#### Watcher Logs
```bash
# Follow watcher output
docker compose logs -f alert_watcher

# Check for alerts
docker compose logs alert