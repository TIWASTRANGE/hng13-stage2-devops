cat > DECISION.md << 'EOF'
# Implementation Decisions

## Why I Built It This Way

### 1. Using Nginx's backup Feature

I configured one server as primary and the other as backup using Nginx's `backup` parameter. This means traffic only goes to the backup server when the primary fails - which is exactly what Blue/Green deployment should do. Without this, Nginx would split traffic between both servers like a load balancer, which isn't what we want.
```nginx
server app_blue:3000 max_fails=1 fail_timeout=10s;
server app_green:3000 backup;
```

### 2. Fast Timeouts (2 seconds)

I set all timeouts to 2 seconds because the task requires zero failed requests during failover. If a server is failing, we need to detect it fast and switch to the backup within the same request. Longer timeouts would make clients wait too long and potentially see errors.

This is aggressive, but it works for the task requirements. In a real production system, I'd probably use 5-10 seconds to avoid false alarms.

### 3. Fail After Just One Error

I used `max_fails=1` so Nginx marks the server as down immediately after a single failure. This ensures instant failover when chaos is triggered. The `fail_timeout=10s` means the server stays marked as down for 10 seconds before Nginx tries it again.

This feels risky but it matches what the task needs - immediate failover with no failed requests.

### 4. Retry on Multiple Error Types
```nginx
proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
```

I told Nginx to retry requests for connection errors, timeouts, and all 5xx errors. This covers all the ways the chaos endpoint can fail. Without this, clients would see errors instead of Nginx switching to the backup.

### 5. Environment Variable Templating

I used a simple shell script with `envsubst` to generate the Nginx config from a template. This lets us switch between Blue and Green just by changing the `.env` file and restarting Nginx - no need to rebuild anything.

The script is straightforward:
- Read `ACTIVE_POOL` from environment
- Figure out which one is backup (if Blue is active, Green is backup)
- Generate the config file
- Start Nginx

### 6. Why I Exposed Ports 8081 and 8082

The task requires direct access to Blue and Green containers to trigger chaos. In a real production setup, these wouldn't be exposed - only the Nginx port would be public. But for testing and grading, we need to hit the `/chaos/*` endpoints directly.

### 7. How Headers Get Through

I kept `proxy_pass_request_headers on` so that the application's custom headers (`X-App-Pool` and `X-Release-Id`) reach the client. These headers prove which server handled the request, which is how we verify failover worked.


### Testing Was Key

I couldn't just assume it worked. I had to run 10+ consecutive requests via a bash *failed_over.sh* script during chaos to prove there were no failures.

### Simple Is Better

I initially considered more complex solutions like health check scripts or custom monitoring. But the simple approach - Nginx's built-in upstream features - works perfectly for this use case. Sometimes the straightforward solution is the right one.

## Future works thoughts

For a production-ready system, I'd add:

1. **Better monitoring** - metrics on failover events and response times
2. **Active health checks** - ping the health endpoint regularly instead of waiting for failures
3. **Logging** - detailed logs of when and why failovers happen

But for this task, the current setup meets all requirements and works reliably.

## Why This Approach Works

The combination of:
- Fast failure detection (2s timeouts)
- Immediate failover (max_fails=1)
- Comprehensive retry logic
- Backup server configuration

Hence, when chaos hits, Nginx detects it in under 2 seconds and retries to the backup server within the same client request. The client never sees an error. That's exactly what the task asked for.
