#!/usr/bin/env python3
"""
Nginx Log Watcher for Blue/Green Deployment
Monitors Nginx logs and sends Slack alerts for failovers and high error rates.
"""

import os
import re
import time
import json
import requests
import subprocess
from collections import deque
from datetime import datetime

# Configuration from environment variables
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '2'))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', '200'))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', '300'))
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
LOG_FILE = '/var/log/nginx/access.log'

# State tracking
last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_alert_times = {}


def parse_log_line(line):
    """Parse Nginx log line and extract relevant fields."""
    try:
        # Extract pool
        pool_match = re.search(r'pool=(\w+)', line)
        pool = pool_match.group(1) if pool_match else None

        # Extract release
        release_match = re.search(r'release=([\w\.-]+)', line)
        release = release_match.group(1) if release_match else None

        # Extract upstream status
        status_match = re.search(r'upstream_status=(\d+)', line)
        upstream_status = int(status_match.group(1)) if status_match else None

        # Extract upstream address
        addr_match = re.search(r'upstream_addr=([\d\.:]+)', line)
        upstream_addr = addr_match.group(1) if addr_match else None

        # Extract request time
        req_time_match = re.search(r'request_time=([\d\.]+)', line)
        request_time = float(req_time_match.group(1)) if req_time_match else None

        # Extract upstream response time
        up_time_match = re.search(r'upstream_response_time=([\d\.]+)', line)
        upstream_response_time = float(up_time_match.group(1)) if up_time_match else None

        # Debug output
        if pool:
            print(f"[DEBUG] Parsed: pool={pool}, status={upstream_status}")

        return {
            'pool': pool,
            'release': release,
            'upstream_status': upstream_status,
            'upstream_addr': upstream_addr,
            'request_time': request_time,
            'upstream_response_time': upstream_response_time,
            'timestamp': datetime.now()
        }
    except Exception as e:
        print(f"[ERROR] Error parsing log line: {e}")
        return None


def send_slack_alert(message, alert_type='info'):
    """Send alert to Slack."""
    print(f"[DEBUG] send_slack_alert called with type={alert_type}")

    if not SLACK_WEBHOOK_URL:
        print(f"[ALERT] No webhook configured. Message: {message}")
        return

    if MAINTENANCE_MODE:
        print(f"[MAINTENANCE MODE] Suppressed alert: {message}")
        return

    # Check cooldown
    if alert_type in last_alert_times:
        elapsed = (datetime.now() - last_alert_times[alert_type]).total_seconds()
        if elapsed < ALERT_COOLDOWN_SEC:
            print(f"[COOLDOWN] Alert suppressed (last sent {elapsed:.0f}s ago)")
            return

    # Determine color based on alert type
    colors = {
        'error_rate': '#FF0000',  # Red
        'recovery': '#00FF00',  # Green
        'info': '#0000FF'  # Blue
    }
    
    # Default color for failover alerts
    color = colors.get(alert_type, '#FFA500')  # Orange for failovers

    # Prepare Slack message
    payload = {
        "attachments": [{
            "color": color,
            "title": "Blue/Green Deployment Alert",
            "text": message,
            "footer": "Backend.im Monitoring",
            "ts": int(time.time())
        }]
    }

    print(f"[DEBUG] Sending to Slack: {SLACK_WEBHOOK_URL[:50]}...")

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            print(f"[SLACK] Alert sent successfully!")
            print(f"[SLACK] Message: {message}")
            last_alert_times[alert_type] = datetime.now()  # FIX: Properly indented
        else:
            print(f"[ERROR] Slack returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Failed to send Slack alert: {e}")
        import traceback
        traceback.print_exc()


def check_failover(current_pool):
    """Check if a failover has occurred."""
    global last_pool

    print(f"[DEBUG] check_failover: current_pool={current_pool}, last_pool={last_pool}")

    if current_pool is None:
        return

    if last_pool is None:
        last_pool = current_pool
        print(f"[INFO] Initial pool detected: {current_pool}")
        return

    if current_pool != last_pool:
        print(f"[ALERT] FAILOVER DETECTED: {last_pool} → {current_pool}")
        message = (
            f"*Failover Detected!*\n"
            f"• From: `{last_pool}`\n"
            f"• To: `{current_pool}`\n"
            f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"• Action: Check health of `{last_pool}` container"
        )
        # Use unique alert type for each failover direction to avoid cooldown conflicts
        alert_type = f'failover_{last_pool}_to_{current_pool}'
        send_slack_alert(message, alert_type=alert_type)
        last_pool = current_pool


def check_error_rate():
    """Check if error rate exceeds threshold."""
    if len(request_window) < WINDOW_SIZE:
        return  # Not enough data yet

    error_count = sum(1 for req in request_window
                      if req.get('upstream_status') and req['upstream_status'] >= 500)

    error_rate = (error_count / len(request_window)) * 100

    # Debug output every 50 requests
    if len(request_window) == WINDOW_SIZE:
        print(f"[DEBUG] Error rate: {error_rate:.2f}% ({error_count}/{WINDOW_SIZE})")

    if error_rate > ERROR_RATE_THRESHOLD:
        print(f"[ALERT] HIGH ERROR RATE: {error_rate:.2f}%")
        message = (
            f"*High Error Rate Detected!*\n"
            f"• Error Rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
            f"• Errors: {error_count}/{len(request_window)} requests\n"
            f"• Window: Last {WINDOW_SIZE} requests\n"
            f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"• Action: Inspect upstream logs and consider manual pool toggle"
        )
        send_slack_alert(message, alert_type='error_rate')


def tail_log_file():
    """Tail the Nginx log file and process new lines using tail command."""
    print(f"[WATCHER] Starting log watcher...")
    print(f"[CONFIG] Error threshold: {ERROR_RATE_THRESHOLD}%")
    print(f"[CONFIG] Window size: {WINDOW_SIZE}")
    print(f"[CONFIG] Cooldown: {ALERT_COOLDOWN_SEC}s")
    print(f"[CONFIG] Maintenance mode: {MAINTENANCE_MODE}")
    print(f"[CONFIG] Slack webhook: {'Configured' if SLACK_WEBHOOK_URL else 'NOT CONFIGURED'}")

    # Wait for log file to exist
    while not os.path.exists(LOG_FILE):
        print(f"[WATCHER] Waiting for log file: {LOG_FILE}")
        time.sleep(2)

    print(f"[WATCHER] Monitoring: {LOG_FILE}")

    # Use tail -f command which handles file rotation and Docker volumes better
    process = subprocess.Popen(
        ['tail', '-f', '-n', '0', LOG_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                continue

            line = line.strip()
            if not line:
                continue

            # Parse log line
            parsed = parse_log_line(line)
            if not parsed:
                continue

            # Track in window
            request_window.append(parsed)

            # Check for failover
            if parsed['pool']:
                check_failover(parsed['pool'])

            # Check error rate
            check_error_rate()

    except KeyboardInterrupt:
        print("\n[WATCHER] Shutting down...")
    finally:
        process.terminate()
        process.wait()


if __name__ == '__main__':
    try:
        tail_log_file()
    except KeyboardInterrupt:
        print("\n[WATCHER] Shutting down...")
    except Exception as e:
        print(f"[ERROR] Watcher crashed: {e}")
        import traceback
        traceback.print_exc()
        raise